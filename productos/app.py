"""Microservicio Productos de TiendaIA.
Expone un CRUD de productos (nombre, precio, categoría) con FastAPI y guarda los
datos en MongoDB, una base de datos de documentos (cada producto es un JSON).
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument

# ==============================================================================
# Base de datos
# ==============================================================================
# MONGO_URL llega por variable de entorno (p. ej. mongodb://mongo:27017, donde
# "mongo" es el nombre del contenedor en docker-compose.yml).
db = MongoClient(os.environ["MONGO_URL"])["tienda"]
# ["tienda"] selecciona la base de datos; MongoDB la crea al primer uso.
db.productos.create_index("id", unique=True)

app = FastAPI(title="TiendaIA - Productos")

# ==============================================================================
# Modelos de entrada
# ==============================================================================
class ProductoIn(BaseModel):
    """Datos de un producto enviados en el cuerpo JSON."""
    nombre: str = Field(min_length=1, max_length=100)
    precio: float = Field(gt=0)
    categoria: str = "general" # valor por omisión si no se envía

class ImagenIn(BaseModel):
    """Modelo para recibir la clave de la imagen (Lab 4)."""
    imagen_key: str | None


def siguiente_id() -> int:
    """Id entero autoincremental (MongoDB no lo tiene: usamos un contador)."""
    doc = db.contadores.find_one_and_update(
        {"_id": "productos"}, {"$inc": {"valor": 1}},
        upsert=True, return_document=ReturnDocument.AFTER)
    return doc["valor"]

# ==============================================================================
# Endpoints
# ==============================================================================
@app.get("/health")
def salud():
    """Verificación de salud usada por el gateway; responde 200."""
    return {"servicio": "productos", "status": "ok"}

@app.get("/productos")
def listar(categoria: str | None = None, precio_max: float | None = None):
    """Devuelve los productos (200), aplicando filtros opcionales."""
    filtro = {}
    if categoria is not None:
        filtro["categoria"] = categoria
    if precio_max is not None:
        filtro["precio"] = {"$lte": precio_max}
        
    # {"_id": 0} es una proyección: excluye el campo id interno de MongoDB
    return list(db.productos.find(filtro, {"_id": 0}))

@app.get("/productos/{producto_id}")
def obtener(producto_id: int):
    """Devuelve un producto por su id (200) o 404 si no existe."""
    p = db.productos.find_one({"id": producto_id}, {"_id": 0})
    if p is None:
        raise HTTPException(404, "Producto no encontrado")
    return p

@app.post("/productos", status_code=201)
def crear(p: ProductoIn):
    """Crea un producto con id nuevo. Responde 201 (Created) o 422 si es inválido."""
    doc = {"id": siguiente_id(), **p.model_dump()}
    db.productos.insert_one(dict(doc)) # copia: insert_one agrega _id
    return doc

@app.put("/productos/{producto_id}")
def actualizar(producto_id: int, p: ProductoIn):
    """Actualiza los campos de un producto (200) o responde 404 si no existe."""
    r = db.productos.update_one({"id": producto_id}, {"$set": p.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(404, "Producto no encontrado")
    return {"id": producto_id, **p.model_dump()}

@app.put("/productos/{id}/imagen")
def actualizar_imagen(id: int, imagen: ImagenIn):
    """Actualiza solo la clave de la imagen en el producto (Lab 4)."""
    resultado = db.productos.update_one(
        {"id": id}, 
        {"$set": {"imagen_key": imagen.imagen_key}}
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"id": id, "imagen_key": imagen.imagen_key}

@app.delete("/productos/{producto_id}", status_code=204)
def eliminar(producto_id: int):
    """Borra un producto. Responde 204 (sin contenido) o 404 si no existe."""
    if db.productos.delete_one({"id": producto_id}).deleted_count == 0:
        raise HTTPException(404, "Producto no encontrado")