"""Microservicio Ventas de TiendaIA (Laboratorio 2).
Registra ventas en Redis (base de datos clave-valor en memoria). Antes de guardar
una venta consulta a los microservicios Clientes y Productos por HTTP
(comunicación síncrona) para validar que existan y obtener el precio.
El servicio de IA le pide la lista de ventas para entrenar su modelo.
"""
import json
import os
from datetime import date
import redis
import requests
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from eventos import publicar
from seguridad import requiere_servicio  # Lab. 6: valida x-api-key con Auth

# ==============================================================================
# Configuración
# ==============================================================================
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)

CLIENTES_URL = os.getenv("CLIENTES_URL", "http://clientes:8000")
PRODUCTOS_URL = os.getenv("PRODUCTOS_URL", "http://productos:8000")

app = FastAPI(
    title="TiendaIA - Ventas",
    dependencies=[Depends(requiere_servicio)],  # Lab. 6
)

TIEMPO_ESPERA = 5
sesion = requests.Session()
# Lab. 6: la cabecera se agrega a TODAS las peticiones que haga esta sesión
sesion.headers.update({"x-api-key": os.getenv("API_KEY", "")})

# ==============================================================================
# Modelo de entrada
# ==============================================================================
class VentaIn(BaseModel):
    """Datos de una venta. Si no son válidos, FastAPI responde 422."""
    cliente_id: int = Field(gt=0)
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000)
    fecha: date | None = None

def consultar(url: str):
    """Llamada síncrona a otro microservicio; None si no existe el recurso."""
    resp = sesion.get(url, timeout=TIEMPO_ESPERA)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()

# ==============================================================================
# Endpoints
# ==============================================================================
@app.get("/health")
def salud():
    """Verificación de salud (200). Incluye si Redis responde a PING."""
    return {"servicio": "ventas", "status": "ok", "redis": r.ping()}

@app.post("/ventas", status_code=201)
def crear(v: VentaIn):
    """Registra una venta y devuelve el registro completo con id, precio y total."""
    if consultar(f"{CLIENTES_URL}/clientes/{v.cliente_id}") is None:
        raise HTTPException(422, "El cliente no existe")
    
    producto = consultar(f"{PRODUCTOS_URL}/productos/{v.producto_id}")
    if producto is None:
        raise HTTPException(422, "El producto no existe")

    venta_id = r.incr("venta:siguiente_id")

    venta = {"id": venta_id, **v.model_dump(mode="json"),
             "fecha": (v.fecha or date.today()).isoformat(),
             "precio": producto["precio"],
             "total": round(producto["precio"] * v.cantidad, 2)}

    r.set(f"venta:{venta_id}", json.dumps(venta))
    r.rpush("ventas", venta_id)
    venta["evento_publicado"] = publicar("venta.creada", venta)
    return venta

@app.get("/ventas")
def listar():
    """Devuelve todas las ventas en orden de registro (200)."""
    ids = r.lrange("ventas", 0, -1)
    if not ids:
        return []
    return [json.loads(v) for v in r.mget([f"venta:{i}" for i in ids]) if v]

@app.get("/ventas/{venta_id}")
def obtener(venta_id: int):
    """Devuelve una venta por su id (200) o 404 si no existe."""
    v = r.get(f"venta:{venta_id}")
    if v is None:
        raise HTTPException(404, "Venta no encontrada")
    return json.loads(v)

@app.delete("/ventas/{venta_id}", status_code=204)
def eliminar(venta_id: int):
    """Borra una venta. Responde 204 (sin contenido) o 404 si no existe."""
    if r.delete(f"venta:{venta_id}") == 0:
        raise HTTPException(404, "Venta no encontrada")
    r.lrem("ventas", 0, venta_id)