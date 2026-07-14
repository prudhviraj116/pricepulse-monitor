#!/usr/bin/env bash
# Start the Celery worker process in the background
celery -A app.worker worker --loglevel=info &

# Start the Celery Beat scheduler in the background
celery -A app.worker beat --loglevel=info &

# Start the FastAPI web application in the foreground
uvicorn app.main:app --host 0.0.0.0 --port $PORT
