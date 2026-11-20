
"""Publicación de eventos de dominio en RabbitMQ (Laboratorio 3)."""

import json
import logging
import os
import pika

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
EXCHANGE = "tienda.eventos"


def publicar(clave: str, datos: dict) -> bool:
    """Publica un evento de dominio en RabbitMQ."""

    con = None

    try:
        if "://" in RABBIT:
            params = pika.URLParameters(RABBIT)
        else:
            params = pika.ConnectionParameters(
                host=RABBIT,
                connection_attempts=3,
                retry_delay=2,
                socket_timeout=5,
                heartbeat=30
            )

        con = pika.BlockingConnection(params)
        canal = con.channel()

        canal.exchange_declare(
            exchange=EXCHANGE,
            exchange_type="topic",
            durable=True
        )

        # Confirma que RabbitMQ acepta los mensajes.
        canal.confirm_delivery()

        canal.basic_publish(
            exchange=EXCHANGE,
            routing_key=clave,
            body=json.dumps(datos, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            ),
            mandatory=True
        )

        return True

    except Exception as e:
        logging.exception(
            "No se pudo publicar el evento %s: %s",
            clave,
            e
        )
        return False

    finally:
        if con is not None and con.is_open:
            try:
                con.close()
            except Exception:
                logging.warning("No se pudo cerrar la conexión RabbitMQ")