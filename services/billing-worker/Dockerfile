FROM python:3.11-slim
WORKDIR /app
COPY requirements-base.txt .
COPY services/billing-worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements.txt
COPY services/billing-worker/ .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
