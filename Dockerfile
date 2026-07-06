# ================================================================================
# Filename: Dockerfile
# Description: Docker configuration for building the Clan Manager Dashboard image.
# Author: Raphael Smilet
# Date Created: 2026-06-06
# Last Modified: 2026-07-03
# Version: 0.5.0
# Dependencies: Docker
# ================================================================================


# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include /app
ENV PYTHONPATH=/app

# Copy project files
COPY . .

# Expose ports
##FastAPI
EXPOSE 8000 
##Streamlit
EXPOSE 8501

# Create a script to sync data and start Streamlit
RUN echo '#!/bin/bash' > start.sh && \
    echo 'echo "Starting tests..."' >> start.sh && \
    echo "pytest" >> start.sh && \
    echo 'echo "Collecting data from Clash Royale API..."' >> start.sh && \
    echo 'python scripts/collect_data.py' >> start.sh && \
    echo 'streamlit run dashboard/home.py --server.port=8501 --server.address=0.0.0.0' >> start.sh && \
    chmod +x start.sh

# Command to run the script
CMD ["./start.sh"]