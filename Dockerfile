# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for mysqlclient
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    libcairo2 \
    libpango-1.0-0 \
    libglib2.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libgirepository-1.0-1 \
    gir1.2-pango-1.0 \
    shared-mime-info \
    fonts-liberation \
    default-libmysqlclient-dev \
    build-essential \
    postgresql-server-dev-all \
 && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8085


# Run gunicorn when the container launches
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]