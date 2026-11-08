import csv
import hashlib
import os
import statistics as st
import time
from datetime import datetime
import boto3

DESTINO = os.getenv("DESTINO", "sin-nombre")
BUCKET = os.environ["BUCKET"]

s3 = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT"),
                  aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                  aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                  region_name=os.getenv("S3_REGION", "us-east-1"))
try:
    s3.head_bucket(Bucket=BUCKET)
except Exception:
    s3.create_bucket(Bucket=BUCKET)

filas = []

def registrar(prueba, valores, unidad, errores=0):
    fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "destino": DESTINO,
            "prueba": prueba, "media": round(st.mean(valores), 2),
            "desv": round(st.stdev(valores), 2) if len(valores) > 1 else 0,
            "unidad": unidad, "n": len(valores), "errores": errores}
    filas.append(fila)
    print(f"{DESTINO:>8} | {prueba:<22} {fila['media']:>9} ± {fila['desv']:<7} {unidad} (errores={errores})")

def archivos_grandes(mb, reps=5):
    datos = os.urandom(mb * 1024 * 1024)
    h = hashlib.sha256(datos).hexdigest()
    sub, baj, err = [], [], 0
    for i in range(reps):
        k = f"bench/{mb}MB-{i}"
        t = time.perf_counter()
        s3.put_object(Bucket=BUCKET, Key=k, Body=datos)
        sub.append(mb / (time.perf_counter() - t))
        t = time.perf_counter()
        leido = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
        baj.append(mb / (time.perf_counter() - t))
        err += hashlib.sha256(leido).hexdigest() != h
        s3.delete_object(Bucket=BUCKET, Key=k)
    registrar(f"subida {mb} MB", sub, "MB/s", err)
    registrar(f"bajada {mb} MB", baj, "MB/s", err)

def archivos_pequenos(n=200, kb=10):
    datos = os.urandom(kb * 1024)
    lat, err = [], 0
    t0 = time.perf_counter()
    for i in range(n):
        t = time.perf_counter()
        try:
            s3.put_object(Bucket=BUCKET, Key=f"bench/peq-{i}", Body=datos)
            lat.append((time.perf_counter() - t) * 1000)
        except Exception:
            err += 1
    total = time.perf_counter() - t0
    registrar(f"{n} archivos de {kb} KB", lat, "ms/archivo", err)
    registrar("rendimiento pequeños", [n / total], "archivos/s")
    for i in range(n):
        s3.delete_object(Bucket=BUCKET, Key=f"bench/peq-{i}")

for mb in (1, 10, 25):
    archivos_grandes(mb)
archivos_pequenos()

nuevo = not os.path.exists("resultados_almacenamiento.csv")
with open("resultados_almacenamiento.csv", "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=filas[0].keys())
    if nuevo:
        w.writeheader()
    w.writerows(filas)