# ================================================================================
# Filename: Dockerfile
# Description: Docker configuration for building the Clan Manager Dashboard image.
# Author: Raphael Smilet
# Date Created: 2026-06-06
# Last Modified: 2026-06-06
# Version: 0.1.0
# Dependencies: Docker
# ================================================================================


# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose ports
##FastAPI
EXPOSE 8000 
##Streamlit
EXPOSE 8501

# Command to run the app (override in docker-compose)
CMD ["tail", "-f", "/dev/null"]