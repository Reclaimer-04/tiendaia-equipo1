"""Publicación de eventos de dominio en RabbitMQ (Laboratorio 3)."""
import json
import logging
import os
import pika

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
PARAMS = (pika.URLParameters(RABBIT) if "://" in RABBIT else pika.ConnectionParameters(RABBIT))
EXCHANGE = "tienda.eventos"

def publicar(clave: str, datos: dict) -> bool:
    """Publica un evento; si el broker no responde, la venta NO se pierde."""
    try:
        con = pika.BlockingConnection(PARAMS)
        canal = con.channel()
        canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
        canal.basic_publish(exchange=EXCHANGE, routing_key=clave,
                            body=json.dumps(datos),
                            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"))
        con.close()
        return True
    except pika.exceptions.AMQPError as e:
        logging.warning("No se publicó %s: %s", clave, e)
        return False