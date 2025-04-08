import json
import logging
import os
import io
import time
from kafka import KafkaConsumer, KafkaProducer
from minio import Minio

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configurazione Kafka (modifica se necessario)
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka-broker-1:9092")
INPUT_TOPIC = "nbs_request"
OUTPUT_TOPIC = "analytcs_result"

# Configurazione MinIO (usa variabili d'ambiente oppure imposta i valori direttamente)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioaccess")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "miniosecret")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "messages")


def save_to_minio(client, bucket, data, object_name):
    """
    Salva il messaggio (formattato in JSON) in MinIO con il nome specificato.
    """
    json_data = json.dumps(data).encode("utf-8")
    data_length = len(json_data)
    client.put_object(
        bucket, object_name, io.BytesIO(json_data), data_length,
        content_type="application/json"
    )
    logger.info("Salvato il messaggio su MinIO come '%s'", object_name)


def main():
    # Connessione a MinIO
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    # Verifica se il bucket esiste, altrimenti lo crea
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
        logger.info("Creato bucket '%s'", MINIO_BUCKET)

    # Crea il consumer Kafka per leggere dal topic 'nbs_request'
    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="analytics_processor_group",
    )

    # Crea il producer Kafka per inviare messaggi a 'analytcs_result'
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    logger.info("Avvio dell'analytics processor. In ascolto sul topic: '%s'", INPUT_TOPIC)

    try:
        for message in consumer:
            logger.info("Messaggio ricevuto: %s", message.value)

            # Genera un nome oggetto unico usando il timestamp
            object_name = f"message_{int(time.time() * 1000)}.json"

            try:
                # Salva il messaggio su MinIO
                save_to_minio(minio_client, MINIO_BUCKET, message.value, object_name)

                # Prepara il messaggio di output per 'analytcs_result'
                output_message = {
                    "status": "saved",
                    "bucket": MINIO_BUCKET,
                    "object_name": object_name,
                    "original_message": message.value
                }

                # Invia il messaggio al topic 'analytcs_result'
                producer.send(OUTPUT_TOPIC, output_message)
                producer.flush()
                logger.info("Inviato messaggio su '%s'", OUTPUT_TOPIC)

            except Exception as ex:
                logger.error("Errore durante il salvataggio del messaggio: %s", ex)

    except KeyboardInterrupt:
        logger.info("Interruzione dell'elaborazione. Uscita in corso...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
