import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from mpremote.commands import do_filesystem_cp, do_connect
from mpremote.main import State


here = Path(__file__).parent.resolve()

hash_file = here / 'hashes.json'
src_dir = here / 'src'
dist_dir = here / 'dist'


def mkdir_p(dir_name):
    os.makedirs(dir_name, exist_ok=True)


class FileHashCache:
    def __init__(self, dir_path: Path=None, hash_file_path: Path=None):
        self.dir_path = dir_path
        self.hash_file_path = hash_file_path
        self.cache = {}

    def load_hash_file(self):
        if self.hash_file_path.exists():
            try:
                with open(self.hash_file_path) as fd:
                    self.cache = json.load(fd)
            except:
                pass

    def save(self):
        with self.hash_file_path.open('w') as fd:
            json.dump(self.cache, fd, indent=2)

    def build_hashes(self):
        for path, dirs, files in self.dir_path.walk():
            for f in files:
                filename = path / f
                with open(filename, "rb") as f:
                    md5_hash = hashlib.file_digest(f, "md5").hexdigest()
                self.cache[str(filename)] = md5_hash

    def diff(self, other_file_hash: 'FileHashCache'):
        differing_hashes = []
        for filename, hash in self.cache.items():
            if other_file_hash.cache.get(filename) != hash:
                differing_hashes.append(filename)
        return differing_hashes

KEEP_AS_PY = {'boot.py', 'main.py'}


def get_mpy_cross_bin():
    exe_name = 'mpy-cross.exe' if os.name == 'nt' else 'mpy-cross'
    candidate = Path(sys.executable).parent / exe_name
    if candidate.exists():
        return str(candidate)
    return 'mpy-cross'


def compile_mpy(src_path: Path, dst_path: Path):
    mpy_cross_bin = get_mpy_cross_bin()
    subprocess.run(
        [mpy_cross_bin, '-o', str(dst_path), str(src_path)],
        check=True,
    )


def build_dist():
    for path, dirs, files in src_dir.walk():
        if '__pycache__' in str(path).lower(): continue

        rel_dir = Path(path).relative_to(src_dir)
        target_dir = dist_dir / rel_dir
        if files:
            mkdir_p(target_dir)
        for f in files:
            src_file = path / f
            if f.endswith('.py') and not (rel_dir == Path('.') and f in KEEP_AS_PY):
                mpy_name = Path(f).with_suffix('.mpy').name
                compile_mpy(src_file, target_dir / mpy_name)
            else:
                shutil.copyfile(src_file, target_dir / f)

def get_board_conn():
    state = State()
    do_connect(state)
    state.ensure_raw_repl()
    state.did_action()
    return state

def build_relative_d(files):
    paths = {}
    dirs = {}
    for path in files:
        path_p = Path(path)
        device_dir = './' + str(path_p.parent.relative_to(dist_dir)).replace('//', '/').replace('\\', '/').strip('./') + '/'
        device_path = path_p.relative_to(dist_dir)

        dirs.setdefault(device_dir, []).append(path)
    return dirs

def device_mkdirs(to_push, state):
    for d in to_push.keys():
        dns = '/' + d.rstrip('/').lstrip('./')
        dest_exists = state.transport.fs_exists(dns) and state.transport.fs_isdir(dns)

        try:
            state.transport.fs_mkdir(dns)
        except FileExistsError:
            pass

def push_differing_hashes(to_push, state):
    for target_dir, files in to_push.items():
        for f in files:
            print(f'Copying {f} to :{target_dir}')
            do_filesystem_cp(state, f, f':{target_dir}', False)

def go():
    # get previous run's hashes
    old_cache = FileHashCache(hash_file_path=hash_file)
    old_cache.load_hash_file()

    # clean dist so stale .py files don't remain alongside .mpy
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    # copy/compile files to dist
    build_dist()

    # build hashes of all files
    new_cache = FileHashCache(dir_path=dist_dir, hash_file_path=hash_file)
    new_cache.build_hashes()

    # get differing hashes
    files_to_push = build_relative_d(new_cache.diff(old_cache))

    # connect to board
    state = get_board_conn()

    # make missing directories
    device_mkdirs(files_to_push, state)

    # push differing hashes
    push_differing_hashes(files_to_push, state)

    # write new hash file
    new_cache.save()


if __name__ == '__main__':
    go()