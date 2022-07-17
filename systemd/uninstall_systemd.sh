#!/usr/bin/env bash

echo "Running novacancy-host systemd service uninstall script"

BASE_DIR=$(realpath "$(dirname $0)")

if [ "${BASE_INSTALL_DIR}" = "" ]; then
  BASE_INSTALL_DIR=/usr/local
fi


SCRIPT_NAME=novacancy-host
SERVICE_NAME=novacancy-host.service

SERVICE_ROOT_DIR=/etc/systemd/system

rm ${BASE_INSTALL_DIR}/bin/${SCRIPT_NAME}
rm ${SERVICE_ROOT_DIR}/${SERVICE_NAME}

echo "Disabling systemd services"
systemctl daemon-reload
systemctl stop ${SERVICE_NAME}
systemctl disable ${SERVICE_NAME}
echo "novacancy-host systemd service uninstallation complete"
