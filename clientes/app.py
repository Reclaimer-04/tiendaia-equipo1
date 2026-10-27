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
# La URL de conexión llega por variable de entorno (la define docker-compose.yml),
# p. ej. mysql+pymysql://usuario:clave@mysql:3306/tienda. Así el mismo código
# funciona en cualquier máquina sin escribir contraseñas dentro del programa.
# pool_pre_ping=True revisa que la conexión siga viva antes de usarla: evita errores
# si MySQL cerró conexiones inactivas o se reinició.
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

# Descripción de la tabla "clientes" (SQLAlchemy Core, sin ORM).
meta = MetaData()
clientes = Table(
    "clientes", meta,
    # Llave primaria entera que MySQL incrementa sola (1, 2, 3...)
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False),
    # unique=True: la base de datos impide dos clientes con el mismo correo
    Column("correo", String(120), nullable=False, unique=True),
)
meta.create_all(engine) # crea la tabla si no existe

app = FastAPI(title="TiendaIA - Clientes")

# ==============================================================================
# Modelo de entrada
# ==============================================================================
class ClienteIn(BaseModel):
    """Datos que el usuario envia en el cuerpo JSON para crear o actualizar.
    Pydantic valida automáticamente: si algo no cumple, FastAPI responde 422
    (Unprocessable Entity) sin que se ejecute el código del endpoint.
    """
    # Field(min_length=1, max_length=100): texto no vacío y de máximo 100 letras,
    # igual que la columna String(100) de la tabla.
    nombre: str = Field(min_length=1, max_length=100)
    # pattern: expresión regular sencilla