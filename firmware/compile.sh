#!/usr/bin/env bash

echo "Running firmware compile script"

export BOARD_ID=$1
export BOARD_TYPE=$2

if [ -z "$BOARD_ID" ]
then
      echo "BOARD_ID is not set. Not compiling."
      exit 1
fi

if [ -z "$BOARD_TYPE" ]
then
      echo "BOARD_TYPE is not set. Not compiling."
      exit 1
fi

export PLATFORMIO_BUILD_FLAGS="
${PLATFORMIO_BUILD_FLAGS}
'-DBOARD_ID=${BOARD_ID}'
'-DBOARD_TYPE=${BOARD_TYPE}'
"

platformio run
