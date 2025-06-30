#!/bin/bash

# Read the InfluxDB token from the secret file
export INFLUX_TOKEN=$(cat /run/secrets/influxdb2-admin-token)

# Execute the original Telegraf command
exec telegraf --config /etc/telegraf/telegraf.conf 