FROM python:3.11-slim
WORKDIR /app
COPY requirements-base.txt .
COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements.txt
COPY services/api/ .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
