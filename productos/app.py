"""Microservicio Productos de TiendaIA (Laboratorio 2).
Expone un CRUD de productos (nombre, precio, categoría) con FastAPI y guarda los
datos en MongoDB, una base de datos de documentos (cada producto es un JSON).
No llama a otros servicios: Ventas lo consulta por HTTP para obtener el precio y
validar que el producto exista; el API Gateway le reenvía las peticiones externas.
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument

# ---------------------------------------------------------------- Base de datos
# MONGO_URL llega por variable de entorno (p. ej. mongodb://mongo:27017).
db = MongoClient(os.environ["MONGO_URL"])["tienda"]

app = FastAPI(title="TiendaIA - Productos")

# ---------------------------------------------------------------- Modelo de entrada
class ProductoIn(BaseModel):
    """Datos de un producto enviados en el cuerpo JSON."""
    nombre: str = Field(min_length=1, max_length=100)
    precio: float = Field(gt=0)  # precio debe ser positivo
    categoria: str = "general"   # valor por omisión

def siguiente_id() -> int:
    """Id entero autoincremental (MongoDB no lo tiene: usamos un contador)."""
    doc = db.contadores.find_one_and_update(
        {"_id": "productos"}, {"$inc": {"valor": 1}},
        upsert=True, return_document=ReturnDocument.AFTER
    )
    return doc["valor"]

# ---------------------------------------------------------------- Endpoints
@app.get("/health")
def salud():
    """Verificación de salud usada por el gateway; responde 200."""
    return {"servicio": "productos", "status": "ok"}

@app.get("/productos")
def listar():
    """Devuelve todos los productos (200)."""
    return list(db.productos.find({}, {"_id": 0}))

@app.get("/productos/{producto_id}")
def obtener(producto_id: int):
    """Devuelve un producto por su id (200) o 404 si no existe."""
    p = db.productos.find_one({"id": producto_id}, {"_id": 0})
    if p is None:
        raise HTTPException(404, "Producto no encontrado")
    return p

@app.post("/productos", status_code=201)
def crear(p: ProductoIn):
    """Crea un producto con id nuevo."""
    doc = {"id": siguiente_id(), **p.model_dump()}
    db.productos.insert_one(dict(doc))
    return doc

@app.put("/productos/{producto_id}")
def actualizar(producto_id: int, p: ProductoIn):
    """Actualiza los campos de un producto (200) o responde 404 si no existe."""
    r = db.productos.update_one({"id": producto_id}, {"$set": p.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(404, "Producto no encontrado")
    return {"id": producto_id, **p.model_dump()}

@app.delete("/productos/{producto_id}", status_code=204)
def eliminar(producto_id: int):
    """Borra un producto. Responde 204 o 404 si no existe."""
    if db.productos.delete_one({"id": producto_id}).deleted_count == 0:
        raise HTTPException(404, "Producto no encontrado")
