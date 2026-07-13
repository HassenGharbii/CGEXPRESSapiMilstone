FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV API_USERNAME=axone
ENV API_PASSWORD=Ax0nesys!
ENV SERVER_URL=http://192.168.20.1
ENV VERIFY_CERTIFICATES=True
ENV ENABLE_WEBSOCKET=true
ENV SYNC_INTERVAL_SECONDS=300
ENV ALARM_SYNC_INTERVAL_SECONDS=15
ENV DATABASE_URL=postgresql+psycopg2://milestone:milestone@db:6623/milestone

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
