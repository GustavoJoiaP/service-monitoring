#!/bin/bash

echo "Removing Service Monitoring Host..."

sudo systemctl stop service-monitoring

sudo systemctl disable service-monitoring

sudo rm -f /etc/systemd/system/service-monitoring.service

sudo systemctl daemon-reload

echo "Done."