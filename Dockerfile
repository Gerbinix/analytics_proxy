# Download Base-image
FROM python:3.12-slim-bullseye

WORKDIR /app

COPY . /app

# INSTALL DEPENDECIES: aggiorna il sistema ed installa gcc
RUN apt-get update && \
    apt-get install --assume-yes gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# INSTALL TOOLS: installa le librerie Python necessarie inclusa quella per MinIO
RUN pip install --no-cache-dir Flask pydantic Flask-Pydantic kafka-python minio

# Espone la porta dell'applicazione
EXPOSE 9090

# Comando di avvio: esegue lo script app.py
ENTRYPOINT [ "python" ]
CMD ["app.py"]
