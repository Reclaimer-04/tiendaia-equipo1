"""Suscriptor IA-Listener (Laboratorio 3, Parte G).
Cuenta las ventas y dispara el reentrenamiento del modelo cada 50 ventas.
"""
import json
import os
import time
import pika
import redis
import requests

# Configuración
RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
PARAMS = (pika.URLParameters(RABBIT) if "://" in RABBIT 
          else pika.ConnectionParameters(RABBIT))
IA_URL = os.getenv("IA_URL", "http://ia:8000")

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)

def procesar(canal, metodo, props, cuerpo):
    """Callback que procesa cada evento de venta."""
    try:
        # Validar que sea un JSON (si no, lanza ValueError y se descarta)
        venta = json.loads(cuerpo)
        
        # Incrementar contador en Redis
        n = r.incr("ia_listener:ventas")
        print(f"Venta procesada. Total actual: {n}", flush=True)

        # Solicitar reentrenamiento cada 50 ventas
        if n % 50 == 0:
            print(f"Límite de {n} alcanzado. Iniciando reentrenamiento...", flush=True)
            res = requests.post(f"{IA_URL}/ia/train", timeout=120)
            print(f"Reentrenamiento finalizado. Código HTTP: {res.status_code}", flush=True)

        # Confirmar el mensaje al final
        canal.basic_ack(delivery_tag=metodo.delivery_tag)

    except ValueError:
        print("Mensaje venenoso detectado (no es JSON). Descartando...", flush=True)
        # Nack sin reencolar para evitar bucles infinitos
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
    except Exception as e:
        print(f"Error inesperado: {e}", flush=True)
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)

# Ciclo principal con reconexión
while True:
    try:
        con = pika.BlockingConnection(PARAMS)
        canal = con.channel()
        
        # Topología: Exchange, cola propia y binding
        canal.exchange_declare("tienda.eventos", exchange_type="topic", durable=True)
        canal.queue_declare("ia_listener", durable=True)
        canal.queue_bind("ia_listener", "tienda.eventos", routing_key="venta.*")
        
        canal.basic_consume("ia_listener", procesar)
        print("IA-Listener conectado y esperando eventos...", flush=True)
        
        canal.start_consuming()
    except pika.exceptions.AMQPConnectionError:
        print("Conexión perdida o RabbitMQ no disponible. Reintentando en 3s...", flush=True)
        time.sleep(3)