"""Microservicio Notificaciones de TiendaIA (Laboratorio 3).
Escucha eventos de ventas de RabbitMQ y guarda un historial de los 100 más recientes en Redis.
"""
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
import pika
import redis
from fastapi import FastAPI, Query

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
PARAMS = (pika.URLParameters(RABBIT) if "://" in RABBIT else pika.ConnectionParameters(RABBIT))
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)

def al_recibir(canal, metodo, props, cuerpo):
    """Callback de pika: se ejecuta una vez por cada evento recibido."""
    try:
        venta = json.loads(cuerpo)
        # Validación básica para lanzar KeyError si falta el ID
        _ = venta["id"] 
        
        texto = f"Venta {venta['id']}: cliente {venta['cliente_id']} compró {venta['cantidad']} x producto {venta['producto_id']} (${venta['total']})"
        mensaje_redis = {"evento": metodo.routing_key, "mensaje": texto}
        
        r.lpush("notificaciones", json.dumps(mensaje_redis))
        r.ltrim("notificaciones", 0, 99)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
        
    except (ValueError, KeyError) as e:
        logging.warning("Mensaje venenoso o incompleto descartado: %s", e)
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)

def consumir():
    """Conecta, declara exchange/cola/binding y consume para siempre."""
    while True:
        try:
            con = pika.BlockingConnection(PARAMS)
            canal = con.channel()
            canal.exchange_declare("tienda.eventos", exchange_type="topic", durable=True)
            canal.queue_declare("notificaciones", durable=True)
            canal.queue_bind("notificaciones", "tienda.eventos", routing_key="venta.*")
            canal.basic_consume("notificaciones", al_recibir)
            canal.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            time.sleep(3)

@asynccontextmanager
async def ciclo_de_vida(app):
    hilo = threading.Thread(target=consumir, daemon=True)
    hilo.start()
    yield

app = FastAPI(title="TiendaIA Notificaciones", lifespan=ciclo_de_vida)

@app.get("/health")
def health():
    return {"servicio": "notificaciones", "status": "ok"}

@app.get("/notificaciones")
def obtener_notificaciones(limite: int = Query(20, ge=1, le=100)):
    items = r.lrange("notificaciones", 0, limite - 1)
    return [json.loads(item) for item in items]