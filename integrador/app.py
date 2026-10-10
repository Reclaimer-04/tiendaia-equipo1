from fastapi import FastAPI
from typing import List

app = FastAPI()

# Endpoint de salud
@app.get("/health")
def health():
    return {"servicio": "integrador", "status": "ok", "historial": "supabase"}

# Endpoint de clima
@app.get("/clima")
def clima(ciudad: str):
    # Aquí normalmente llamarías a una API externa (OpenWeather, etc.)
    # Para pruebas, devolvemos datos fijos
    return {
        "ciudad": ciudad,
        "temperatura": 27.3,
        "descripcion": "cielo parcialmente nublado"
    }

# Endpoint de países
@app.get("/paises")
def paises() -> List[str]:
    return ["México", "Argentina", "España", "Colombia", "Chile"]

# Endpoint de recomendación
@app.post("/recomendacion")
def recomendacion(ciudad: str):
    # Ejemplo fijo, normalmente se conectaría a Supabase
    return {
        "ciudad": ciudad,
        "recomendacion": f"Visita el centro histórico de {ciudad} y prueba la comida local."
    }

# Endpoint de historial
@app.get("/historial")
def historial(limite: int = 5):
    # Ejemplo fijo, normalmente se leería de Supabase
    return {
        "almacen": "supabase",
        "latencia_guardado_ms": 12,
        "registros": [
            {"id": 1, "ciudad": "Monterrey", "creado": "2026-10-09T18:00:00"},
            {"id": 2, "ciudad": "Mérida", "creado": "2026-10-09T18:05:00"}
        ][:limite]
    }
