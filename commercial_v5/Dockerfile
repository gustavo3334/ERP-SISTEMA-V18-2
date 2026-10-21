FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ENVIRONMENT=production AUTO_CREATE_TABLES=false
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 10000
CMD ["sh", "-c", "alembic -c alembic_gateway.ini upgrade head && uvicorn gateway.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers"]
