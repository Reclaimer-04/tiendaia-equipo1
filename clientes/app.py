"""Microservicio Clientes de TiendaIA (Laboratorio 2).
Expone un CRUD (crear, leer, actualizar, borrar) de clientes mediante una API REST
hecha con FastAPI. Los datos se guardan en MySQL usando SQLAlchemy Core.
No llama a otros servicios: el microservicio Ventas lo consulta por HTTP para
validar que un cliente exista, y el API Gateway le reenvía las peticiones externas.
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, Integer, MetaData, String, Table, create_engine,
    delete, insert, select, update
)
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------- Base de datos
# La URL de conexión llega por variable de entorno (la define docker-compose.yml),
# p. ej. mysql+pymysql://usuario:clave@mysql:3306/tienda.
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

# Descripción de la tabla "clientes" (SQLAlchemy Core, sin ORM).
meta = MetaData()
clientes = Table(
    "clientes", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False),
    Column("correo", String(120), nullable=False, unique=True),
)
meta.create_all(engine)  # crea la tabla si no existe

app = FastAPI(title="TiendaIA - Clientes")

# ---------------------------------------------------------------- Modelo de entrada
class ClienteIn(BaseModel):
    """Datos que el usuario envía en el cuerpo JSON para crear o actualizar."""
    nombre: str = Field(min_length=1, max_length=100)
    correo: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)

# ---------------------------------------------------------------- Endpoints
@app.get("/health")
def salud():
    """Verificación de salud: el gateway y Docker la usan para saber si está vivo."""
    return {"servicio": "clientes", "status": "ok"}

@app.get("/clientes")
def listar():
    """Devuelve la lista de todos los clientes (200)."""
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(select(clientes))]

@app.get("/clientes/{cliente_id}")
def obtener(cliente_id: int):
    """Devuelve un cliente por su id (200) o 404 si no existe."""
    with engine.connect() as c:
        r = c.execute(select(clientes).where(clientes.c.id == cliente_id)).first()
        if r is None:
            raise HTTPException(404, "Cliente no encontrado")
        return dict(r._mapping)

@app.post("/clientes", status_code=201)
def crear(cli: ClienteIn):
    """Crea un cliente y devuelve sus datos con el id asignado."""
    try:
        with engine.begin() as c:
            r = c.execute(insert(clientes).values(**cli.model_dump()))
    except IntegrityError:
        raise HTTPException(409, "El correo ya está registrado")
    return {"id": r.inserted_primary_key[0], **cli.model_dump()}

@app.put("/clientes/{cliente_id}")
def actualizar(cliente_id: int, cli: ClienteIn):
    """Reemplaza nombre y correo de un cliente (200) o responde 404 si no existe."""
    with engine.begin() as c:
        r = c.execute(update(clientes).where(clientes.c.id == cliente_id).values(**cli.model_dump()))
        if r.rowcount == 0:
            raise HTTPException(404, "Cliente no encontrado")
    return {"id": cliente_id, **cli.model_dump()}

@app.delete("/clientes/{cliente_id}", status_code=204)
def eliminar(cliente_id: int):
    """Borra un cliente. Responde 204 (sin contenido) o 404 si no existe."""
    with engine.begin() as c:
        r = c.execute(delete(clientes).where(clientes.c.id == cliente_id))
        if r.rowcount == 0:
            raise HTTPException(404, "Cliente no encontrado")
    # 204 No Content: éxito sin cuerpo de respuesta
