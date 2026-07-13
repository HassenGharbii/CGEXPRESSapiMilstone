FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN mkdir -p /app/data

ENV API_USERNAME=axone
ENV API_PASSWORD=Ax0nesys!
ENV SERVER_URL=http://192.168.20.1
ENV VERIFY_CERTIFICATES=True
ENV RECORDING_SERVER_ID=27ed6e15-babf-4c4f-a86e-cf3d2a188ec1
ENV DATA_DIR=/app/data
ENV ENABLE_WEBSOCKET=false

CMD ["python", "main.py"]
