import os
import time
import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

GEOCODING_URL = os.getenv("GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search")
CLIMA_URL = os.getenv("CLIMA_URL", "https://api.open-meteo.com/v1/forecast")
PAISES_URL = os.getenv("PAISES_URL", "https://countries.trevorblades.com/")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = FastAPI(title="TiendaIA - Servicio integrador")
TIEMPO_ESPERA = (3, 10)
sesion = requests.Session()
_cache: dict[str, tuple[object, float]] = {}

CODIGOS_WMO = {0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado",
               3: "nublado", 45: "niebla", 51: "llovizna", 61: "lluvia ligera",
               63: "lluvia", 65: "lluvia fuerte", 80: "chubascos", 95: "tormenta"}

def llamar(metodo: str, url: str, **kwargs) -> dict:
    for intento in (1, 2):
        try:
            r = sesion.request(metodo, url, timeout=TIEMPO_ESPERA, **kwargs)
            if r.status_code >= 500 and intento == 1:
                time.sleep(0.5)
                continue
            if r.status_code == 429:
                raise HTTPException(503, "Límite de uso del proveedor alcanzado; intente más tarde")
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            if intento == 2:
                raise HTTPException(504, f"{url} no respondió a tiempo")
        except requests.HTTPError as e:
            raise HTTPException(502, f"{url} respondió {e.response.status_code}")
        except requests.JSONDecodeError:
            raise
        except requests.RequestException:
            if intento == 2:
                raise HTTPException(502, f"No fue posible conectar con {url}")
    raise HTTPException(502, f"{url} falló después de 2 intentos")

def con_cache(clave: str, segundos: int, obtener):
    valor, expira = _cache.get(clave, (None, 0.0))
    if time.time() < expira:
        return valor, True
    valor = obtener()
    _cache[clave] = (valor, time.time() + segundos)
    return valor, False

@app.get("/health")
def salud():
    return {"servicio": "integrador", "status": "ok", "historial": ALMACEN}

@app.get("/clima")
def clima(ciudad: str = Query("Ciudad Valles", min_length=2, max_length=80)):
    t0 = time.perf_counter()
    def obtener():
        geo = llamar("GET", GEOCODING_URL, params={"name": ciudad, "count": 1, "language": "es"})
        if not geo.get("results"):
            raise HTTPException(404, f"No se encontró la ciudad '{ciudad}'")
        lugar = geo["results"][0]
        datos = llamar("GET", CLIMA_URL, params={
            "latitude": lugar["latitude"], "longitude": lugar["longitude"],
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
            "timezone": "auto"})
        actual = datos["current"]
        return {"ciudad": lugar["name"], "pais": lugar.get("country"),
                "temperatura_c": actual["temperature_2m"],
                "humedad_pct": actual["relative_humidity_2m"],
                "precipitacion_mm": actual["precipitation"],
                "descripcion": CODIGOS_WMO.get(actual["weather_code"], "otro"),
                "hora_local": actual["time"]}
    
    datos, de_cache = con_cache(f"clima:{ciudad.lower()}", 600, obtener)
    return {**datos, "desde_cache": de_cache,
            "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}

CONSULTA_PAIS = """
query ($codigo: ID!) {
  country(code: $codigo) { name native capital currency languages {name} continent {name} }
}
"""
@app.get("/paises/{codigo}")
def pais(codigo: str):
    if len(codigo) != 2 or not codigo.isalpha():
        raise HTTPException(422, "Use el código ISO de 2 letras, p. ej. MX")
    t0 = time.perf_counter()
    resp, de_cache = con_cache(f"pais:{codigo.upper()}", 86400, lambda: llamar(
        "POST", PAISES_URL, json={"query": CONSULTA_PAIS, "variables": {"codigo": codigo.upper()}}))
    if resp.get("errors") or not resp.get("data", {}).get("country"):
        raise HTTPException(404, "País no encontrado")
    p = resp["data"]["country"]
    return {"nombre": p["name"], "nombre_nativo": p["native"], "capital": p["capital"],
            "moneda": p["currency"], "idiomas": [i["name"] for i in p["languages"]],
            "continente": p["continent"]["name"], "desde_cache": de_cache,
            "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}

class SolicitudRecomendacion(BaseModel):
    ciudad: str = Field("Ciudad Valles", min_length=2, max_length=80)
    productos: list[str] = Field(
        default_factory=lambda: ["Café de la Huasteca", "Piloncillo", "Miel de abeja", "Zacahuil", "Bocoles"],
        min_length=1,
        max_length=10,
    )

def regla_simple(c: dict, productos: list[str]) -> str:
    if c["precipitacion_mm"] > 0 or c["temperatura_c"] < 20:
        return f"Con {c['descripcion']} y {c['temperatura_c']} °C, recomiende {productos[0]}."
    return f"Con {c['temperatura_c']} °C, recomiende {productos[-1]} para llevar."

ALMACEN = "supabase" if (SUPABASE_URL and SUPABASE_KEY) else "memoria"
_historial: list[dict] = []

def _cabeceras_supabase() -> dict:
    h = {"apikey": SUPABASE_KEY}
    if SUPABASE_KEY.startswith("eyJ"):
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    return h

def guardar_consulta(registro: dict) -> dict:
    if ALMACEN == "memoria":
        registro = {"id": len(_historial) + 1, "creado": time.strftime("%Y-%m-%dT%H:%M:%S"), **registro}
        _historial.append(registro)
        return registro
    filas = llamar(
        "POST",
        f"{SUPABASE_URL}/rest/v1/consultas",
        json=registro,
        headers={
            **_cabeceras_supabase(),
            "Prefer": "return=representation",
        },
    )
    return filas[0]

def leer_historial(limite: int) -> list[dict]:
    if ALMACEN == "memoria":
        return list(reversed(_historial))[:limite]
    return llamar("GET", f"{SUPABASE_URL}/rest/v1/consultas", headers=_cabeceras_supabase(),
                  params={"select": "*", "order": "creado.desc", "limit": limite})

@app.post("/recomendacion")
def recomendacion(s: SolicitudRecomendacion):
    c = clima(s.ciudad)
    texto = regla_simple(c, s.productos)
    t0 = time.perf_counter()
    registro = guardar_consulta({"ciudad": c["ciudad"], "temperatura_c": c["temperatura_c"],
                                 "descripcion": c["descripcion"], "recomendacion": texto})
    return {"clima": c, "recomendacion": texto, "registro": registro, "almacen": ALMACEN,
            "latencia_guardado_ms": round((time.perf_counter() - t0) * 1000, 1)}

@app.get("/historial")
def historial(limite: int = Query(10, ge=1, le=100)):
    filas = leer_historial(limite)
    return {"almacen": ALMACEN, "total": len(filas), "consultas": filas}