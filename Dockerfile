# ================================================================================
# Filename: Dockerfile
# Description: Docker configuration for building the Clan Manager Dashboard image.
# Author: Raphael Smilet
# Date Created: 2026-06-06
# Last Modified: 2026-10-06
# Version: 0.5.2
# Dependencies: Docker
# ================================================================================


FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Numeric container users may have no writable home for Streamlit telemetry.
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
COPY . .
RUN pip install --no-cache-dir . && mkdir -p /app/data/cache /app/data/locks /app/logs /app/backups && chown -R 1000:1000 /app
USER 1000:1000
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "scripts.run_app"]
