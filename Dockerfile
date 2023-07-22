# Use an official Python base image from the Docker Hub
FROM python:3.10-slim AS threader-base

# Install utilities
RUN apt-get update && apt-get install -y \
    curl jq wget git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install Poetry
RUN pip install poetry

# Set the working directory
WORKDIR /app

# Copy the project files into the Docker image
COPY . /app

# Install the required python packages using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# dev build -> include everything
FROM threader-base as threader-dev
WORKDIR /app
ONBUILD COPY . ./

# release build -> include bare minimum
FROM threader-base as threader-release
WORKDIR /app
ONBUILD COPY github_threader/ ./github_threader
ONBUILD COPY pyproject.toml ./pyproject.toml
ONBUILD RUN mkdir ./data

FROM threader-${BUILD_TYPE} AS threader

# Set the entrypoint
CMD ["python", "main.py"]
