# Use the official Python image from the Docker Hub
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the necessary ports
EXPOSE 5001 8001

# Set the default command to run the application
CMD ["sh", "-c", "if [ ${FLASK_ENV} = 'development' ]; then flask run --host=0.0.0.0 --port=5001; else gunicorn -c gunicorn_config.py 'app:create_app(\"frontend\")'; fi"]