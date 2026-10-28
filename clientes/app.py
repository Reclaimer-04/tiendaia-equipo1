"""Microservicio Clientes de TiendaIA (Laboratorio 2).
Expone un CRUD (crear, leer, actualizar, borrar) de clientes mediante una API REST
hecha con FastAPI. Los datos se guardan en MySQL usando SQLAlchemy Core.
No llama a otros servicios: el microservicio Ventas lo consulta por HTTP para
validar que un cliente exista, y el API Gateway le reenvia las peticiones externas.
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (Column, Integer, MetaData, String, Table, create_engine,
                        delete, insert, select, update)
from sqlalchemy.exc import IntegrityError

# ==============================================================================
# Base de datos
# ==============================================================================
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

meta = MetaData()
clientes = Table(
    "clientes", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False),
    Column("correo", String(120), nullable=False, unique=True),
)
meta.create_all(engine)

app = FastAPI(title="TiendaIA - Clientes")

# ==============================================================================
# Modelo de entrada
# ==============================================================================
class ClienteIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    correo: str = Field(pattern=r"^\S+@\S+\.\S+$")

# ==============================================================================
# Endpoints
# ==============================================================================
@app.get("/health")
def salud():
    return {"servicio": "clientes", "status": "ok"}

@app.post("/clientes", status_code=201)
def crear(c: ClienteIn):
    with engine.begin() as conn:
        try:
            res = conn.execute(insert(clientes).values(**c.model_dump()))
            return {"id": res.lastrowid, **c.model_dump()}
        except IntegrityError:
            raise HTTPException(409, "El correo ya esta registrado")

@app.get("/clientes")
def listar():
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(select(clientes))]

@app.get("/clientes/{cliente_id}")
def obtener(cliente_id: int):
    with engine.connect() as conn:
        r = conn.execute(select(clientes).where(clientes.c.id == cliente_id)).first()
        if r is None:
            raise HTTPException(404, "Cliente no encontrado")
        return dict(r._mapping)

@app.put("/clientes/{cliente_id}")
def actualizar(cliente_id: int, c: ClienteIn):
    with engine.begin() as conn:
        try:
            res = conn.execute(update(clientes).where(clientes.c.id == cliente_id)
                               .values(**c.model_dump()))
            if res.rowcount == 0:
                raise HTTPException(404, "Cliente no encontrado")
            return {"id": cliente_id, **c.model_dump()}
        except IntegrityError:
            raise HTTPException(409, "El correo ya esta registrado")

@app.delete("/clientes/{cliente_id}", status_code=204)
def eliminar(cliente_id: int):
    with engine.begin() as conn:
        if conn.execute(delete(clientes).where(clientes.c.id == cliente_id)).rowcount == 0:
            raise HTTPException(404, "Cliente no encontrado")