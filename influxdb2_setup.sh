#!/bin/bash
# reading variables from file
DOCKER_INFLUXDB_INIT_USERNAME=$(cat $DOCKER_INFLUXDB_INIT_USERNAME_FILE)
DOCKER_INFLUXDB_INIT_PASSWORD=$(cat $DOCKER_INFLUXDB_INIT_PASSWORD_FILE)
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=$(cat $DOCKER_INFLUXDB_INIT_ADMIN_TOKEN_FILE)

# Create buckets defined in SETUP_BUCKETS array.
echo "##### Setting up : ${SETUP_BUCKETS}"
for bucket_name in ${SETUP_BUCKETS};
    do
        echo "---> ${bucket_name}"
        if influx bucket list \
            --host http://${DOCKER_INFLUXDB_INIT_HOST}:${DOCKER_INFLUXDB_INIT_PORT} \
            -t ${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN} \
            -o ${DOCKER_INFLUXDB_INIT_ORG} --name ${bucket_name} &> /dev/null
            
            then
                echo "Bucket ${bucket_name} already exists. Skipping"
            else
                influx bucket create -n ${bucket_name} \
                    -o ${DOCKER_INFLUXDB_INIT_ORG} \
                    -r ${DOCKER_INFLUXDB_INIT_RETENTION} \
                    --host http://${DOCKER_INFLUXDB_INIT_HOST}:${DOCKER_INFLUXDB_INIT_PORT} \
                    -t ${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
                echo "Bucket ${bucket_name} created."
        fi
    done
echo "##### Setting up completed"

exit 0
