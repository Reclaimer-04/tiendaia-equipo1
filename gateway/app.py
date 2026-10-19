"""API Gateway de TiendaIA: punto único de entrada (Laboratorio 2).
Recibe todas las peticiones externas en /api/<servicio>/... y las reenvía
(proxy inverso) al microservicio correspondiente: Clientes, Productos, Ventas o IA.
El usuario solo conoce la dirección del gateway; los microservicios quedan ocultos
en la red interna de Docker. También ofrece /health con el estado de cada servicio.
"""
import os
import requests # cliente HTTP para reenviar las peticiones a los microservicios
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
# ---------------------------------------------------------------- Configuración
# Tabla de ruteo: prefijo de la URL -> dirección interna del microservicio.
# En Docker Compose cada servicio se llama por su nombre (http://clientes:8000).
RUTAS = {
"clientes": os.getenv("CLIENTES_URL", "http://clientes:8000"),
"productos": os.getenv("PRODUCTOS_URL", "http://productos:8000"),
"ventas": os.getenv("VENTAS_URL", "http://ventas:8000"),
"ia": os.getenv("IA_URL", "http://ia:8000"),
}
app = FastAPI(title="TiendaIA - API Gateway")
# CORS (Cross-Origin Resource Sharing): el navegador bloquea las peticiones de una
# página a OTRO origen (esquema + host + puerto) salvo que el servidor lo autorice.
# El cliente web vive en otro origen (http://localhost:5500, Render...), por eso el
# gateway responde con las cabeceras Access-Control-Allow-*. CORS_ORIGINS es una
# lista separada por comas; "*" permite cualquier origen (en producción, ponga
# solo la URL de su frontend).
ORIGENES = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=ORIGENES,
allow_methods=["*"], allow_headers=["*"])

# Se reutiliza: conexiones persistentes (no se abre una conexión TCP nueva cada vez)
sesion = requests.Session()
TIEMPO_ESPERA = 60 # segundos; generoso porque entrenar el modelo tarda
TIEMPO_SALUD = 3 # /health debe contestar rápido o se considera caído
# ---------------------------------------------------------------- Endpoints
@app.get("/health")
async def health():
    return {"servicio": "gateway", "status": "ok"}



from fastapi import Path

@app.api_route("/api/{servicio}/{ruta:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, servicio: str = Path(...), ruta: str = Path(...)):
    if servicio not in RUTAS:
        return {"error": f"Servicio '{servicio}' no encontrado"}

    url_destino = f"{RUTAS[servicio]}/{ruta}"
    metodo = request.method.lower()
    cuerpo = await request.body()
    headers = dict(request.headers)

    respuesta = await run_in_threadpool(
        lambda: sesion.request(metodo, url_destino, data=cuerpo, headers=headers, timeout=TIEMPO_ESPERA)
    )

    return Response(content=respuesta.content, status_code=respuesta.status_code, headers=dict(respuesta.headers))
#varias correct¿ciones