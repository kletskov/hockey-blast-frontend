
#!/bin/bash
set -e

# Start the app container
docker-compose up -d app

# Wait for the app container to be ready
until docker exec hockey_blast_app ls /usr/local/lib/python3.9/site-packages/hockey_blast_common_lib; do
  echo "Waiting for the app container to be ready..."
  sleep 2
done

# Copy files from the app container to the host directory for sharing with the db container
# This is for sample DB restore
docker cp hockey_blast_app:/usr/local/lib/python3.9/site-packages/hockey_blast_common_lib ./.common_lib_for_docker_db_restore

# Start the db container
docker-compose up -d db