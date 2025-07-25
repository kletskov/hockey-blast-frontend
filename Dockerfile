# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Install PostgreSQL development packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip show hockey_blast_common_lib

# Copy the rest of the application code into the container
COPY . .

# Copy the patch script into the container
COPY patch_flask_table.sh .

# Run the patch script
RUN chmod +x patch_flask_table.sh && ./patch_flask_table.sh

# Expose the necessary ports
EXPOSE 5001 8001

# Set the default command to run the application
CMD ["sh", "-c", "if [ ${FLASK_ENV} = 'development' ]; then FLASK_APP='app:create_sample_app()' FLASK_RUN_PORT=5001 flask run --host=0.0.0.0; else gunicorn -c gunicorn_config_docker.py 'app:create_prod_app()'; fi"]