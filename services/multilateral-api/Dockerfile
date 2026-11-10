FROM python:3.11-slim
WORKDIR /app
COPY requirements-base.txt .
COPY services/multilateral-api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements.txt
COPY services/multilateral-api/ .
EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
