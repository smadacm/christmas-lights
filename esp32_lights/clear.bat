@echo off

@rem cd to esp32 directory
@cd /d "%~dp0"

@rem remove all files from the esp32 device
@mpremote rm -rv :/.

@rem clear the `dist` dir
if exist "dist" (
    @del /f /s /q dist\*.*
)

@rem clear hashes so build script will rebuild everything
if exist "hashes.json" (
    @del hashes.json
)