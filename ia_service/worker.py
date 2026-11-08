
"""Worker de inferencia de TiendaIA (Laboratorio 3): consume la cola 'inferencias'.

Proceso independiente (no es una API): toma solicitudes de RabbitMQ, calcula la
predicción con el modelo entrenado por el servicio de IA y escribe el resultado
en Redis, donde lo lee GET /ia/solicitudes/{id}. Puede haber N copias en
paralelo: RabbitMQ reparte los mensajes entre ellas (cola de trabajo).
"""

import json
import os
import socket
import time

import joblib
import pandas as pd
import pika
import redis


# ----------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")

PARAMS = (
    pika.URLParameters(RABBIT)
    if "://" in RABBIT
    else pika.ConnectionParameters(RABBIT)
)

MODELO = os.getenv("MODELO_PATH", "/modelos/modelo.joblib")

RETARDO = float(os.getenv("RETARDO_MS", "200")) / 1000

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    decode_responses=True
)

modelo = None


# ----------------------------------------------------------------
# Procesamiento de solicitudes
# ----------------------------------------------------------------

def procesar(canal, metodo, props, cuerpo):
    """Procesa un mensaje recibido desde RabbitMQ."""

    global modelo

    try:
        s = json.loads(cuerpo)

        # Cargar el modelo solamente la primera vez
        if modelo is None:
            modelo = joblib.load(MODELO)

        # Preparar los datos para la predicción
        x = pd.DataFrame(
            [[s["producto_id"], s["mes"], s["precio"]]],
            columns=["producto_id", "mes", "precio"]
        )

        # Simular el tiempo de procesamiento
        time.sleep(RETARDO)

        # Generar resultado
        resultado = {
            "estado": "listo",
            "worker": f"{socket.gethostname()}:{os.getpid()}",
            "cantidad_estimada": round(
                float(modelo.predict(x)[0]), 1
            )
        }

    except Exception as e:
        print("error al procesar:", e, flush=True)

        # Si el mensaje tiene un ID, guardar el error en Redis
        if isinstance(locals().get("s"), dict) and "id" in s:
            r.set(
                f"solicitud:{s['id']}",
                json.dumps({
                    "estado": "error",
                    "detalle": str(e)
                }),
                ex=3600
            )

        # Rechazar el mensaje sin volver a encolarlo
        canal.basic_nack(
            delivery_tag=metodo.delivery_tag,
            requeue=False
        )
        return

    # Guardar resultado en Redis
    r.set(
        f"solicitud:{s['id']}",
        json.dumps(resultado),
        ex=3600
    )

    # Confirmar que el mensaje fue procesado
    canal.basic_ack(
        delivery_tag=metodo.delivery_tag
    )


# ----------------------------------------------------------------
# Ciclo principal
# ----------------------------------------------------------------

while True:
    try:
        con = pika.BlockingConnection(PARAMS)
        canal = con.channel()

        # Declarar la cola de trabajo
        canal.queue_declare(
            "inferencias",
            durable=True
        )

        # Reparto justo: un mensaje a la vez por worker
        canal.basic_qos(prefetch_count=1)

        # Escuchar mensajes de la cola
        canal.basic_consume(
            "inferencias",
            procesar
        )

        print("worker listo", flush=True)

        # Mantener el worker trabajando
        canal.start_consuming()

    except pika.exceptions.AMQPConnectionError:
        print(
            "No se pudo conectar a RabbitMQ. Reintentando en 3 segundos...",
            flush=True
        )
        time.sleep(3)