#!/usr/bin/env python3
"""Daily URL rotation scheduler ("pseudo-cron").

Starts at a configured daily start time, rotates through an ordered list of
URL paths one per interval, calls a configured stop URL at the daily stop time,
and stays running to repeat the schedule every day.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import re
import signal
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path

import requests
from dotenv import load_dotenv

# =============================================================================
# User Configuration
# =============================================================================

# Ordered list of URL paths to rotate through (1 URL called per interval).
# Relative paths are combined with the domain/IP loaded from .env.
# Full http(s):// URLs are also allowed and used as-is.
URL_PATHS: list[str] = [
    "/candy_cane",
    "/christmas_chase",
    "/red_green_wipe",
    "/red_green_shooting",
    "/rainbow",
    "/twinkle",
    "/super_twinkle",
]

# URL path called once when STOP_TIME is reached.
STOP_URL_PATH: str = "/off"

# Daily active window in 24-hour local time ("HH:MM" or "HH:MM:SS").
# Overnight windows (e.g. START_TIME="17:00", STOP_TIME="01:00") are supported.
START_TIME: str = "16:30"
STOP_TIME: str = "00:00"

# Minutes between rotated URL calls.
INTERVAL_MINUTES: float = 10

# Path to .env file and variable name holding the target domain, IP, or base URL.
ENV_FILE: Path = Path(__file__).resolve().parent / ".env"
ENV_HOST_KEY: str = "TARGET_HOST"
FALLBACK_ENV_HOST_KEYS: tuple[str, ...] = ("BASE_URL", "DOMAIN", "HOST", "IP")

# HTTP settings
DEFAULT_SCHEME: str = "http"
HTTP_METHOD: str = "GET"
REQUEST_TIMEOUT_SECONDS: float = 10.0

# Retry behavior when calling STOP_URL_PATH at the end of a window.
STOP_URL_RETRIES: int = 3
STOP_URL_RETRY_DELAY_SECONDS: float = 5.0

# If True, also call STOP_URL_PATH when interrupted (Ctrl+C / SIGTERM) mid-window.
CALL_STOP_ON_EXIT: bool = False

# =============================================================================

logger = logging.getLogger("pseudo-cron")

_TIME_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
_SCHEME_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def parse_time_of_day(value: str) -> dt.time:
    """Parse a 24-hour time string ('HH:MM' or 'HH:MM:SS') into a datetime.time."""
    cleaned = value.strip()
    match = _TIME_PATTERN.match(cleaned)
    if not match:
        raise ValueError(
            f"Invalid time '{value}'. Expected 24-hour 'HH:MM' or 'HH:MM:SS'."
        )

    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3)) if match.group(3) is not None else 0

    try:
        return dt.time(hour=hour, minute=minute, second=second)
    except ValueError as exc:
        raise ValueError(
            f"Invalid time '{value}' (hour={hour}, minute={minute}, second={second})."
        ) from exc


def normalize_base_url(raw_host: str, default_scheme: str = DEFAULT_SCHEME) -> str:
    """Normalize a domain, IP, or URL from .env into a scheme + host base URL."""
    cleaned = raw_host.strip()
    if (
        not cleaned
        or not cleaned.strip("/")
        or re.fullmatch(r"https?:/{0,2}", cleaned, re.IGNORECASE)
    ):
        raise ValueError(f"Invalid or empty host/URL value '{raw_host}'.")

    if not _SCHEME_PATTERN.match(cleaned):
        scheme = default_scheme.strip().rstrip(":/") or "http"
        cleaned = f"{scheme}://{cleaned}"

    cleaned = cleaned.rstrip("/")
    if not _SCHEME_PATTERN.sub("", cleaned).strip("/"):
        raise ValueError(f"Invalid host/URL value '{raw_host}'.")

    return cleaned


def load_base_url(
    env_file: Path,
    host_key: str = ENV_HOST_KEY,
    default_scheme: str = DEFAULT_SCHEME,
) -> str:
    """Load the target domain/IP/base URL from the .env file or environment."""
    load_dotenv(dotenv_path=env_file, override=False)

    candidate_keys = (host_key, *FALLBACK_ENV_HOST_KEYS)
    seen: set[str] = set()
    for key in candidate_keys:
        if not key or key in seen:
            continue
        seen.add(key)
        raw_value = os.getenv(key)
        if raw_value is not None and raw_value.strip():
            return normalize_base_url(raw_value, default_scheme=default_scheme)

    raise ValueError(
        f"Target host is not configured. Set {host_key} in '{env_file}' "
        f"(for example: {host_key}=192.168.1.100)."
    )


def build_url(base_url: str, path: str) -> str:
    """Combine base_url and a path unless the path is already a full HTTP(S) URL."""
    cleaned_path = path.strip()
    if _SCHEME_PATTERN.match(cleaned_path):
        return cleaned_path

    normalized_base = base_url.strip().rstrip("/")
    relative = cleaned_path.lstrip("/")
    return f"{normalized_base}/{relative}"


def compute_window(
    now: dt.datetime,
    start_tod: dt.time,
    stop_tod: dt.time,
    min_end_after: dt.datetime | None = None,
) -> tuple[dt.datetime, dt.datetime]:
    """Compute the current or next active [window_start, window_end) interval.

    Supports both same-day windows (start_tod < stop_tod) and overnight windows
    crossing midnight (start_tod > stop_tod).
    """
    if start_tod == stop_tod:
        raise ValueError("START_TIME and STOP_TIME cannot be identical.")

    today = now.date()
    one_day = dt.timedelta(days=1)

    if start_tod < stop_tod:
        today_start = dt.datetime.combine(today, start_tod)
        today_end = dt.datetime.combine(today, stop_tod)
        if now < today_end:
            window_start, window_end = today_start, today_end
        else:
            tomorrow = today + one_day
            window_start = dt.datetime.combine(tomorrow, start_tod)
            window_end = dt.datetime.combine(tomorrow, stop_tod)
    else:
        prev_start = dt.datetime.combine(today - one_day, start_tod)
        prev_end = dt.datetime.combine(today, stop_tod)
        if now < prev_end:
            window_start, window_end = prev_start, prev_end
        else:
            window_start = dt.datetime.combine(today, start_tod)
            window_end = dt.datetime.combine(today + one_day, stop_tod)

    while min_end_after is not None and window_end <= min_end_after:
        window_start = dt.datetime.combine(window_start.date() + one_day, start_tod)
        window_end = dt.datetime.combine(window_end.date() + one_day, stop_tod)

    return window_start, window_end


def sleep_until(
    target: dt.datetime,
    stop_event: threading.Event,
    max_chunk_seconds: float = 1.0,
) -> bool:
    """Sleep in short chunks until target local datetime or stop_event is set.

    Returns True when target is reached, False if interrupted by stop_event.
    """
    chunk = max(0.05, max_chunk_seconds)
    while not stop_event.is_set():
        remaining = (target - dt.datetime.now()).total_seconds()
        if remaining <= 0:
            return True
        stop_event.wait(timeout=min(remaining, chunk))
    return False


def _wait_retry_delay(delay_seconds: float, stop_event: threading.Event | None) -> bool:
    """Sleep for retry delay, returning False if interrupted by stop_event."""
    if delay_seconds <= 0:
        return stop_event is None or not stop_event.is_set()
    if stop_event is not None:
        return not stop_event.wait(timeout=delay_seconds)
    time.sleep(delay_seconds)
    return True


def call_url(
    session: requests.Session,
    url: str,
    *,
    method: str,
    timeout: float,
    retries: int = 1,
    retry_delay: float = 0.0,
    dry_run: bool = False,
    stop_event: threading.Event | None = None,
) -> bool:
    """Send an HTTP request to url, logging status and retrying on transient errors."""
    http_method = method.strip().upper()
    if dry_run:
        logger.info("[DRY-RUN] %s %s", http_method, url)
        return True

    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            response = session.request(method=http_method, url=url, timeout=timeout)
            if response.ok:
                logger.info(
                    "Called %s %s -> HTTP %d", http_method, url, response.status_code
                )
                return True

            logger.warning(
                "Called %s %s -> HTTP %d (attempt %d/%d)",
                http_method,
                url,
                response.status_code,
                attempt,
                attempts,
            )
            if response.status_code < 500:
                return False
        except requests.RequestException as exc:
            logger.warning(
                "Request failed for %s %s (attempt %d/%d): %s",
                http_method,
                url,
                attempt,
                attempts,
                exc,
            )

        if attempt < attempts:
            if not _wait_retry_delay(retry_delay, stop_event):
                logger.info("Retry wait interrupted for %s", url)
                return False

    logger.error("All %d attempt(s) failed for %s %s", attempts, http_method, url)
    return False


def _format_duration(delta: dt.timedelta) -> str:
    """Format a positive timedelta as Hh Mm Ss for log messages."""
    total_seconds = max(0, int(delta.total_seconds()))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}h {minutes:02d}m {seconds:02d}s"


def _install_signal_handlers(
    stop_event: threading.Event,
) -> list[tuple[int, object]]:
    """Install SIGINT/SIGTERM handlers in the main thread and return prior handlers."""
    if threading.current_thread() is not threading.main_thread():
        return []

    previous: list[tuple[int, object]] = []

    def _handle_signal(signum: int, _frame: object) -> None:
        try:
            sig_name = signal.Signals(signum).name
        except ValueError:
            sig_name = str(signum)
        logger.info("Received %s; shutting down...", sig_name)
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        previous.append((sig, signal.getsignal(sig)))
        signal.signal(sig, _handle_signal)

    return previous


def _restore_signal_handlers(previous: list[tuple[int, object]]) -> None:
    """Restore signal handlers saved by _install_signal_handlers."""
    for sig, handler in previous:
        signal.signal(sig, handler)  # type: ignore[arg-type]


def run_scheduler(
    *,
    base_url: str,
    url_paths: Sequence[str] = URL_PATHS,
    stop_url_path: str = STOP_URL_PATH,
    start_time: str = START_TIME,
    stop_time: str = STOP_TIME,
    interval_minutes: float = INTERVAL_MINUTES,
    http_method: str = HTTP_METHOD,
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    stop_url_retries: int = STOP_URL_RETRIES,
    stop_url_retry_delay: float = STOP_URL_RETRY_DELAY_SECONDS,
    call_stop_on_exit: bool = CALL_STOP_ON_EXIT,
    dry_run: bool = False,
    run_once: bool = False,
    stop_event: threading.Event | None = None,
) -> None:
    """Run the daily URL rotation loop until interrupted (or 1 window if run_once)."""
    if not url_paths:
        raise ValueError("URL_PATHS must contain at least one URL path.")
    if not stop_url_path.strip():
        raise ValueError("STOP_URL_PATH must not be empty.")
    if interval_minutes <= 0:
        raise ValueError("INTERVAL_MINUTES must be greater than 0.")

    start_tod = parse_time_of_day(start_time)
    stop_tod = parse_time_of_day(stop_time)
    if start_tod == stop_tod:
        raise ValueError("START_TIME and STOP_TIME cannot be identical.")

    event = stop_event if stop_event is not None else threading.Event()
    previous_handlers = _install_signal_handlers(event)
    interval_delta = dt.timedelta(minutes=interval_minutes)
    last_window_end: dt.datetime | None = None

    logger.info(
        "Scheduler initialized: base_url=%s, urls=%d, interval=%.4gm, window=%s->%s%s",
        base_url,
        len(url_paths),
        interval_minutes,
        start_tod.isoformat(timespec="seconds"),
        stop_tod.isoformat(timespec="seconds"),
        " [DRY-RUN]" if dry_run else "",
    )

    try:
        with requests.Session() as session:
            while not event.is_set():
                now = dt.datetime.now()
                window_start, window_end = compute_window(
                    now,
                    start_tod,
                    stop_tod,
                    min_end_after=last_window_end,
                )

                if now < window_start:
                    wait_duration = window_start - now
                    logger.info(
                        "Waiting until next start at %s (in %s).",
                        window_start.strftime("%Y-%m-%d %H:%M:%S"),
                        _format_duration(wait_duration),
                    )
                    if not sleep_until(window_start, event):
                        break

                logger.info(
                    "Active window started (%s -> %s).",
                    window_start.strftime("%Y-%m-%d %H:%M:%S"),
                    window_end.strftime("%Y-%m-%d %H:%M:%S"),
                )

                url_index = 0
                next_call_at = dt.datetime.now()

                while not event.is_set():
                    current = dt.datetime.now()
                    if current >= window_end:
                        break

                    path = url_paths[url_index % len(url_paths)]
                    target_url = build_url(base_url, path)
                    logger.info(
                        "Rotation %d/%d -> %s",
                        (url_index % len(url_paths)) + 1,
                        len(url_paths),
                        target_url,
                    )
                    call_url(
                        session,
                        target_url,
                        method=http_method,
                        timeout=timeout_seconds,
                        retries=1,
                        dry_run=dry_run,
                        stop_event=event,
                    )
                    url_index += 1

                    next_call_at += interval_delta
                    after_call = dt.datetime.now()
                    if next_call_at <= after_call:
                        next_call_at = after_call + interval_delta

                    wake_target = min(next_call_at, window_end)
                    sleep_until(wake_target, event)

                if event.is_set():
                    if call_stop_on_exit:
                        stop_url = build_url(base_url, stop_url_path)
                        logger.info(
                            "Interrupted during active window; calling stop URL: %s",
                            stop_url,
                        )
                        call_url(
                            session,
                            stop_url,
                            method=http_method,
                            timeout=timeout_seconds,
                            retries=stop_url_retries,
                            retry_delay=stop_url_retry_delay,
                            dry_run=dry_run,
                            stop_event=None,
                        )
                    break

                stop_url = build_url(base_url, stop_url_path)
                logger.info(
                    "Stop time %s reached; calling stop URL: %s",
                    window_end.strftime("%Y-%m-%d %H:%M:%S"),
                    stop_url,
                )
                call_url(
                    session,
                    stop_url,
                    method=http_method,
                    timeout=timeout_seconds,
                    retries=stop_url_retries,
                    retry_delay=stop_url_retry_delay,
                    dry_run=dry_run,
                    stop_event=event,
                )
                last_window_end = window_end

                if run_once:
                    logger.info("--once flag set; exiting after completing window.")
                    break
    finally:
        _restore_signal_handlers(previous_handlers)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse optional CLI overrides for pseudo-cron.py."""
    parser = argparse.ArgumentParser(
        description=(
            "Rotate through configured URLs at a fixed interval between daily "
            "START_TIME and STOP_TIME, calling STOP_URL_PATH when stopped."
        )
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ENV_FILE,
        help=f"Path to .env file containing {ENV_HOST_KEY} (default: {ENV_FILE})",
    )
    parser.add_argument(
        "--start",
        default=START_TIME,
        help=f"Daily start time in 24h HH:MM or HH:MM:SS (default: {START_TIME})",
    )
    parser.add_argument(
        "--stop",
        default=STOP_TIME,
        help=f"Daily stop time in 24h HH:MM or HH:MM:SS (default: {STOP_TIME})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=INTERVAL_MINUTES,
        help=f"Minutes between rotated URL calls (default: {INTERVAL_MINUTES})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log URLs that would be called without sending HTTP requests.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single active window and exit instead of repeating daily.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for CLI execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    args = parse_args(argv)
    try:
        base_url = load_base_url(
            env_file=args.env_file,
            host_key=ENV_HOST_KEY,
            default_scheme=DEFAULT_SCHEME,
        )
        run_scheduler(
            base_url=base_url,
            url_paths=URL_PATHS,
            stop_url_path=STOP_URL_PATH,
            start_time=args.start,
            stop_time=args.stop,
            interval_minutes=args.interval,
            http_method=HTTP_METHOD,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            stop_url_retries=STOP_URL_RETRIES,
            stop_url_retry_delay=STOP_URL_RETRY_DELAY_SECONDS,
            call_stop_on_exit=CALL_STOP_ON_EXIT,
            dry_run=args.dry_run,
            run_once=args.once,
        )
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
