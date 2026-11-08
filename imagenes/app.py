import hashlib
import os
import uuid
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from almacen import AlmacenS3
from almacen_azure import AlmacenAzure

# ==============================================================================
# Configuración global
# ==============================================================================
PRODUCTOS_URL = os.getenv("PRODUCTOS_URL", "http://productos:8000")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
TIPOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp"
}
TIEMPO_ESPERA = 5

# ==============================================================================
# Selector de adaptador de almacenamiento
# ==============================================================================
TIPO_ALMACEN = os.getenv("ALMACEN", "s3")
if TIPO_ALMACEN == "s3":
    almacen = AlmacenS3()
elif TIPO_ALMACEN == "azure":
    almacen = AlmacenAzure()
else:
    raise ValueError(f"Proveedor de almacenamiento no soportado: {TIPO_ALMACEN}")

sesion = requests.Session()
app = FastAPI(title="TiendaIA - Imágenes")

# ==============================================================================
# Funciones auxiliares
# ==============================================================================
def producto(pid: int) -> dict:
    r = sesion.get(f"{PRODUCTOS_URL}/productos/{pid}", timeout=TIEMPO_ESPERA)
    if r.status_code == 404:
        raise HTTPException(404, "Producto no encontrado")
    return r.json()

def asociar(pid: int, clave: str | None):
    sesion.put(f"{PRODUCTOS_URL}/productos/{pid}/imagen", json={"imagen_key": clave})

# ==============================================================================
# Endpoints
# ==============================================================================
@app.get("/health")
def health():
    return {"servicio": "imagenes", "status": "ok", "bucket": almacen.bucket}

@app.post("/imagenes", status_code=201)
async def subir(producto_id: int = Form(gt=0), archivo: UploadFile = File(...)):
    p = producto(producto_id)
    
    if archivo.content_type not in TIPOS:
        raise HTTPException(415, "Solo se aceptan JPEG, PNG o WebP")
        
    datos = await archivo.read()
    if len(datos) > MAX_BYTES:
        raise HTTPException(413, "La imagen excede 5 MB")

    clave = f"productos/{producto_id}/{uuid.uuid4().hex}.{TIPOS[archivo.content_type]}"
    sha = hashlib.sha256(datos).hexdigest()

    almacen.subir(clave, datos, archivo.content_type, {"sha256": sha})
    
    # Si el producto ya tenía una imagen, la borramos para no dejar archivos huérfanos
    if p.get("imagen_key"):
        almacen.eliminar(p["imagen_key"])
        
    asociar(producto_id, clave)
    return {"producto_id": producto_id, "clave": clave, "bytes": len(datos), "sha256": sha}

@app.get("/imagenes/{producto_id}")
def obtener(producto_id: int):
    p = producto(producto_id)
    clave = p.get("imagen_key")
    if not clave:
        raise HTTPException(404, "El producto no tiene imagen")
    return {"producto_id": producto_id, "url": almacen.url(clave), "expira_en_s": 3600}

@app.delete("/imagenes/{producto_id}", status_code=204)
def eliminar(producto_id: int):
    p = producto(producto_id)
    clave = p.get("imagen_key")
    if not clave:
        raise HTTPException(404, "El producto no tiene imagen")
    almacen.eliminar(clave)
    asociar(producto_id, None)