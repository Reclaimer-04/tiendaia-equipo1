"""Solicitudes de inferencia asincronas (cola de trabajo en RabbitMQ, Laboratorio 3)."""
import json
import os
import uuid
import pika
import redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

RABBIT = os.getenv("RABBITMQ_HOST", "rabbitmq")
PARAMS = (pika.URLParameters(RABBIT) if "://" in RABBIT else pika.ConnectionParameters(RABBIT))
COLA = "inferencias"
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)

router = APIRouter()

class Solicitud(BaseModel):
    producto_id: int = Field(gt=0)
    mes: int = Field(ge=1, le=12)
    precio: float = Field(gt=0)

@router.post("/ia/solicitudes", status_code=202)
def encolar(s: Solicitud):
    sid = str(uuid.uuid4())
    r.set(f"solicitud:{sid}", json.dumps({"estado": "pendiente"}), ex=3600)
    
    con = pika.BlockingConnection(PARAMS)
    canal = con.channel()
    canal.queue_declare(COLA, durable=True)
    canal.basic_publish("", COLA, json.dumps({"id": sid, **s.model_dump()}),
                        pika.BasicProperties(delivery_mode=2))
    con.close()
    return {"id": sid, "estado": "pendiente"}

@router.get("/ia/solicitudes/{sid}")
def consultar(sid: str):
    v = r.get(f"solicitud:{sid}")
    if v is None:
        raise HTTPException(404, "Solicitud no encontrada")
    return {"id": sid, **json.loads(v)}