
"""Servicio integrador de TiendaIA - Laboratorio 1.

Integra:
- Open-Meteo mediante REST.
- Countries mediante GraphQL.
- Supabase mediante su API REST.
"""

import os
import time
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


# ==================================================
# CONFIGURACIÓN
# ==================================================

GEOCODING_URL = os.getenv(
    "GEOCODING_URL",
    "https://geocoding-api.open-meteo.com/v1/search"
)

CLIMA_URL = os.getenv(
    "CLIMA_URL",
    "https://api.open-meteo.com/v1/forecast"
)

PAISES_URL = os.getenv(
    "PAISES_URL",
    "https://countries.trevorblades.com/"
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

ALMACEN = (
    "supabase"
    if SUPABASE_URL and SUPABASE_KEY
    else "memoria"
)

app = FastAPI(
    title="TiendaIA - Servicio integrador",
    description="Integración de REST, GraphQL y Supabase",
    version="1.0.0"
)

TIEMPO_ESPERA = (3, 10)
sesion = requests.Session()

_cache = {}
_historial = []

CODIGOS_WMO = {
    0: "despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    51: "llovizna",
    61: "lluvia ligera",
    63: "lluvia",
    65: "lluvia fuerte",
    80: "chubascos",
    95: "tormenta"
}


# ==================================================
# LLAMADAS A SERVICIOS EXTERNOS
# ==================================================

def llamar(metodo, url, **kwargs):
    """Realiza peticiones HTTP con timeout y reintento."""

    for intento in range(2):
        try:
            respuesta = sesion.request(
                metodo,
                url,
                timeout=TIEMPO_ESPERA,
                **kwargs
            )

            if respuesta.status_code >= 500 and intento == 0:
                time.sleep(0.5)
                continue

            if respuesta.status_code == 429:
                raise HTTPException(
                    status_code=503,
                    detail="El proveedor alcanzó su límite de uso"
                )

            respuesta.raise_for_status()

            return respuesta.json()

        except requests.Timeout:
            if intento == 1:
                raise HTTPException(
                    status_code=504,
                    detail="El servicio externo no respondió a tiempo"
                )

        except requests.HTTPError as error:
            codigo = error.response.status_code

            raise HTTPException(
                status_code=502,
                detail=f"El servicio externo respondió HTTP {codigo}"
            )

        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="El servicio externo devolvió un JSON inválido"
            )

        except requests.RequestException:
            if intento == 1:
                raise HTTPException(
                    status_code=502,
                    detail="No fue posible conectar con el servicio externo"
                )

    raise HTTPException(
        status_code=502,
        detail="La petición falló después de dos intentos"
    )


def con_cache(clave, segundos, obtener):
    """Guarda temporalmente las respuestas de APIs externas."""

    valor, expira = _cache.get(clave, (None, 0))

    if time.time() < expira:
        return valor, True

    valor = obtener()

    _cache[clave] = (
        valor,
        time.time() + segundos
    )

    return valor, False


# ==================================================
# ENDPOINT 1: HEALTH
# ==================================================

@app.get("/health")
def health():
    return {
        "servicio": "integrador",
        "status": "ok",
        "historial": ALMACEN
    }


# ==================================================
# ENDPOINT 2: CLIMA - REST
# ==================================================

@app.get("/clima")
def clima(
    ciudad: str = Query(
        default="Ciudad Valles",
        min_length=2,
        max_length=80
    )
):
    inicio = time.perf_counter()

    def obtener_clima():

        # Buscar coordenadas de la ciudad
        geocodificacion = llamar(
            "GET",
            GEOCODING_URL,
            params={
                "name": ciudad,
                "count": 1,
                "language": "es"
            }
        )

        resultados = geocodificacion.get("results")

        if not resultados:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la ciudad '{ciudad}'"
            )

        lugar = resultados[0]

        # Consultar clima real
        datos = llamar(
            "GET",
            CLIMA_URL,
            params={
                "latitude": lugar["latitude"],
                "longitude": lugar["longitude"],
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "weather_code"
                ),
                "timezone": "auto"
            }
        )

        actual = datos["current"]

        return {
            "ciudad": lugar["name"],
            "pais": lugar.get("country"),
            "temperatura_c": actual["temperature_2m"],
            "humedad_pct": actual["relative_humidity_2m"],
            "precipitacion_mm": actual["precipitation"],
            "descripcion": CODIGOS_WMO.get(
                actual["weather_code"],
                "otro"
            ),
            "hora_local": actual["time"]
        }

    datos, desde_cache = con_cache(
        f"clima:{ciudad.lower()}",
        600,
        obtener_clima
    )

    return {
        **datos,
        "desde_cache": desde_cache,
        "latencia_ms": round(
            (time.perf_counter() - inicio) * 1000,
            1
        )
    }


# ==================================================
# ENDPOINT 3: PAÍSES - GRAPHQL
# ==================================================

CONSULTA_PAIS = """
query ($codigo: ID!) {
    country(code: $codigo) {
        name
        native
        capital
        currency
        languages {
            name
        }
        continent {
            name
        }
    }
}
"""


@app.get("/paises/{codigo}")
def pais(codigo: str):

    if len(codigo) != 2 or not codigo.isalpha():
        raise HTTPException(
            status_code=422,
            detail="Utiliza un código ISO de dos letras, por ejemplo MX"
        )

    inicio = time.perf_counter()

    respuesta, desde_cache = con_cache(
        f"pais:{codigo.upper()}",
        86400,
        lambda: llamar(
            "POST",
            PAISES_URL,
            json={
                "query": CONSULTA_PAIS,
                "variables": {
                    "codigo": codigo.upper()
                }
            }
        )
    )

    pais_datos = respuesta.get("data", {}).get("country")

    if respuesta.get("errors") or not pais_datos:
        raise HTTPException(
            status_code=404,
            detail="País no encontrado"
        )

    return {
        "nombre": pais_datos["name"],
        "nombre_nativo": pais_datos["native"],
        "capital": pais_datos["capital"],
        "moneda": pais_datos["currency"],
        "idiomas": [
            idioma["name"]
            for idioma in pais_datos["languages"]
        ],
        "continente": pais_datos["continent"]["name"],
        "desde_cache": desde_cache,
        "latencia_ms": round(
            (time.perf_counter() - inicio) * 1000,
            1
        )
    }


# ==================================================
# MODELO PARA RECOMENDACIONES
# ==================================================

class SolicitudRecomendacion(BaseModel):

    ciudad: str = Field(
        default="Ciudad Valles",
        min_length=2,
        max_length=80
    )

    productos: list[str] = Field(
        default_factory=lambda: [
            "Café de la Huasteca",
            "Piloncillo",
            "Miel de abeja",
            "Zacahuil",
            "Bocoles"
        ],
        min_length=1,
        max_length=10
    )


# ==================================================
# REGLA DE RECOMENDACIÓN
# ==================================================

def regla_simple(clima_actual, productos):

    temperatura = clima_actual["temperatura_c"]
    precipitacion = clima_actual["precipitacion_mm"]
    descripcion = clima_actual["descripcion"]

    if precipitacion > 0 or temperatura < 20:
        return (
            f"Con {descripcion} y {temperatura} °C, "
            f"recomiende {productos[0]}."
        )

    return (
        f"Con {temperatura} °C, "
        f"recomiende {productos[-1]} para llevar."
    )


# ==================================================
# SUPABASE
# ==================================================

def cabeceras_supabase():
    """Construye cabeceras compatibles con llaves modernas."""

    cabeceras = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }

    # Las llaves heredadas son JWT.
    # Las llaves sb_secret_ se envían mediante apikey.
    if SUPABASE_KEY.startswith("eyJ"):
        cabeceras["Authorization"] = (
            f"Bearer {SUPABASE_KEY}"
        )

    return cabeceras


def guardar_consulta(registro):

    if ALMACEN == "memoria":

        nuevo = {
            "id": len(_historial) + 1,
            "creado": datetime.now(
                timezone.utc
            ).isoformat(),
            **registro
        }

        _historial.append(nuevo)

        return nuevo

    url = f"{SUPABASE_URL}/rest/v1/consultas"

    respuesta = llamar(
        "POST",
        url,
        headers={
            **cabeceras_supabase(),
            "Prefer": "return=representation"
        },
        json=registro
    )

    if not isinstance(respuesta, list) or not respuesta:
        raise HTTPException(
            status_code=502,
            detail="Supabase no devolvió el registro guardado"
        )

    return respuesta[0]


def leer_historial(limite):

    if ALMACEN == "memoria":
        return list(reversed(_historial))[:limite]

    return llamar(
        "GET",
        f"{SUPABASE_URL}/rest/v1/consultas",
        headers=cabeceras_supabase(),
        params={
            "select": "*",
            "order": "creado.desc",
            "limit": limite
        }
    )


# ==================================================
# ENDPOINT 4: RECOMENDACIÓN
# ==================================================

@app.post("/recomendacion")
def recomendacion(solicitud: SolicitudRecomendacion):

    # Consultar clima real
    clima_actual = clima(solicitud.ciudad)

    # Generar recomendación
    texto = regla_simple(
        clima_actual,
        solicitud.productos
    )

    # Preparar información para Supabase
    registro = {
        "ciudad": clima_actual["ciudad"],
        "temperatura_c": clima_actual["temperatura_c"],
        "descripcion": clima_actual["descripcion"],
        "recomendacion": texto
    }

    # Medir tiempo de almacenamiento
    inicio = time.perf_counter()

    registro_guardado = guardar_consulta(registro)

    latencia_guardado = round(
        (time.perf_counter() - inicio) * 1000,
        1
    )

    return {
        "clima": clima_actual,
        "recomendacion": texto,
        "registro": registro_guardado,
        "almacen": ALMACEN,
        "latencia_guardado_ms": latencia_guardado
    }


# ==================================================
# ENDPOINT 5: HISTORIAL
# ==================================================

@app.get("/historial")
def historial(
    limite: int = Query(
        default=10,
        ge=1,
        le=100
    )
):

    registros = leer_historial(limite)

    return {
        "almacen": ALMACEN,
        "total": len(registros),
        "consultas": registros
    }
