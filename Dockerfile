FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the backend requirements and install them
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the rest of the application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY signallens.db ./

# Expose port (Render/Railway use the PORT env var)
ENV PORT=8000
EXPOSE 8000

# Set Python Path and start the Uvicorn server serving main:app
WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
