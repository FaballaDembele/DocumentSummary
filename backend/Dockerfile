# Dockerfile
FROM python:3.10-slim

# Install system deps (tesseract + fonts)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Upgrade pip and install python deps
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Command (uvicorn)
CMD ["uvicorn", "main1:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
