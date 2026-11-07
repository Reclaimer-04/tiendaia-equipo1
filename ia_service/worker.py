"""Worker de inferencia de TiendaIA (Laboratorio 3): consume la cola 'inferencias'."""
import json
import os
import socket
import time
import joblib
import pandas as pd
import pika
import redis

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
PARAMS = (pika.URLParameters(RABBIT) if "://" in RABBIT else pika.ConnectionParameters(RABBIT))
MODELO = os.getenv("MODELO_PATH", "/modelos/modelo.joblib")
RETARDO = float(os.getenv("RETARDO_MS", "200")) / 1000

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)
modelo = None

def procesar(canal, metodo, props, cuerpo):
    global modelo
    try:
        s = json.loads(cuerpo)
        if modelo is None:
            modelo = joblib.load(MODELO)
        
        x = pd.DataFrame([[s["producto_id"], s["mes"], s["precio"]]],
                         columns=["producto_id", "mes", "precio"])
        time.sleep(RETARDO)
        
        resultado = {
            "estado": "listo",
            "worker": f"{socket.gethostname()}:{os.getpid()}",
            "cantidad_estimada": round(float(modelo.predict(x)[0]), 1)
        }
        r.set(f"solicitud:{s['id']}", json.dumps(resultado), ex=3600)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
        
    except Exception as e:
        print("error al procesar:", e, flush=True)
        if isinstance(locals().get("s"), dict) and "id" in s:
            r.set(f"solicitud:{s['id']}", json.dumps({"estado": "error", "detalle": str(e)}), ex=3600)
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)

while True:
    try:
        con = pika.BlockingConnection(PARAMS)
        canal = con.channel()
        canal.queue_declare("inferencias", durable=True)
        canal.basic_qos(prefetch_count=1)
        canal.basic_consume("inferencias", procesar)
        print("worker listo", flush=True)
        canal.start_consuming()
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)