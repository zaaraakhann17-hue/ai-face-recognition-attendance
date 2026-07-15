FROM python:3.10-slim

# Install compilation dependencies required for dlib and face_recognition
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt
RUN pip install --no-cache-dir --default-timeout=1000 requests

# Copy strictly the AI service folder contents into the workspace
COPY ./ai_service .

EXPOSE 5001

CMD ["python", "ai_app.py"]