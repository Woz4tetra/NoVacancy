#!/usr/bin/env bash

echo "Running firmware upload script"

platformio run --target upload #  --upload-port=/dev/tty.usbserial-0246DD75
