
import os
import time
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="TiendaIA - Integrador",
    description="API de recomendaciones con historial en Supabase",
    version="1.0.0"
)

# Variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

USAR_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Historial temporal para pruebas sin Supabase
historial_memoria = []


# --------------------------------------
# CONEXIÓN CON SUPABASE
# --------------------------------------

def headers_supabase():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }


def guardar_registro(ciudad):
    if not USAR_SUPABASE:
        historial_memoria.append({
            "id": len(historial_memoria) + 1,
            "ciudad": ciudad,
            "creado": datetime.now(timezone.utc).isoformat()
        })
        return

    url = (
        f"{SUPABASE_URL}/rest/v1/"
        "consultas"
    )

    try:
        respuesta = requests.post(
            url,
            headers={
                **headers_supabase(),
                "Prefer": "return=minimal"
            },
            json={"ciudad": ciudad},
            timeout=10
        )

        respuesta.raise_for_status()

    except requests.RequestException as error:
        print(f"Error al guardar en Supabase: {error}")

        raise HTTPException(
            status_code=502,
            detail="Error al guardar en Supabase"
        )


def obtener_registros(limite):
    if not USAR_SUPABASE:
        return historial_memoria[-limite:][::-1]

    url = (
        f"{SUPABASE_URL}/rest/v1/"
        "consultas"
    )

    try:
        respuesta = requests.get(
            url,
            headers=headers_supabase(),
            params={
                "select": "id,ciudad,creado",
                "order": "creado.desc,id.desc",
                "limit": limite
            },
            timeout=10
        )

        respuesta.raise_for_status()
        return respuesta.json()

    except (requests.RequestException, ValueError) as error:
        print(f"Error al consultar Supabase: {error}")

        raise HTTPException(
            status_code=502,
            detail="Error al consultar Supabase"
        )


# --------------------------------------
# ENDPOINT 1: HEALTH
# --------------------------------------

@app.get("/health")
def health():
    return {
        "servicio": "integrador",
        "status": "ok",
        "historial": (
            "supabase" if USAR_SUPABASE else "memoria"
        )
    }


# --------------------------------------
# ENDPOINT 2: CLIMA
# --------------------------------------

@app.get("/clima")
def clima(ciudad: str):
    return {
        "ciudad": ciudad,
        "temperatura": 27.3,
        "descripcion": "cielo parcialmente nublado"
    }


# --------------------------------------
# ENDPOINT 3: PAISES
# --------------------------------------

@app.get("/paises")
def paises():
    return [
        "México",
        "Argentina",
        "España",
        "Colombia",
        "Chile"
    ]


# --------------------------------------
# ENDPOINT 4: RECOMENDACION
# --------------------------------------

@app.post("/recomendacion")
def recomendacion(ciudad: str = Query(min_length=1)):
    ciudad = ciudad.strip()

    if not ciudad:
        raise HTTPException(
            status_code=422,
            detail="Debes introducir una ciudad"
        )

    texto = (
        f"Visita el centro histórico de {ciudad} "
        "y prueba la comida local."
    )

    # Guardar la ciudad en Supabase o memoria
    guardar_registro(ciudad)

    return {
        "ciudad": ciudad,
        "recomendacion": texto
    }


# --------------------------------------
# ENDPOINT 5: HISTORIAL
# --------------------------------------

@app.get("/historial")
def historial(
    limite: int = Query(default=5, ge=1, le=100)
):
    inicio = time.perf_counter()

    registros = obtener_registros(limite)

    latencia_ms = round(
        (time.perf_counter() - inicio) * 1000,
        2
    )

    return {
        "almacen": (
            "supabase" if USAR_SUPABASE else "memoria"
        ),
        "latencia_consulta_ms": latencia_ms,
        "elementos_guardados": len(registros),
        "registros": registros
    }
