FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements-base.txt .
COPY services/voice-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements.txt
COPY services/voice-service/ .
EXPOSE 8004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
