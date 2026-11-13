FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Código Python, incluindo os *_pb2.py gerados (versionados no repositório)
COPY python/ .
ENV PYTHONUNBUFFERED=1
CMD ["python", "SimpleNamingService.py"]
