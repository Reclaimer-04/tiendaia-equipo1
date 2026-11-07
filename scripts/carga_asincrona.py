"""Envia N solicitudes de inferencia asincronas y mide el tiempo hasta que todas terminan."""
import os
import sys
import time
from collections import Counter
import requests

GW = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
TOKEN = os.getenv("TOKEN")
TIEMPO_ESPERA = 10

sesion = requests.Session()
if TOKEN:
    sesion.headers.update({"Authorization": f"Bearer {TOKEN}"})

t0 = time.perf_counter()
ids = [sesion.post(f"{GW}/api/ia/solicitudes", timeout=TIEMPO_ESPERA,
                   json={"producto_id": 1 + i % 5, "mes": 1 + i % 12, "precio": 90.0}).json()["id"]
       for i in range(N)]
t_envio = time.perf_counter() - t0

pendientes, por_worker = set(ids), Counter()

while pendientes:
    for sid in list(pendientes):
        res = sesion.get(f"{GW}/api/ia/solicitudes/{sid}", timeout=TIEMPO_ESPERA).json()
        if res["estado"] == "listo":
            pendientes.discard(sid)
            por_worker[res["worker"]] += 1
        elif res["estado"] == "error":
            pendientes.discard(sid)
            por_worker["errores"] += 1
    time.sleep(0.2)

total = time.perf_counter() - t0
print(f"N={N} envio={t_envio:.1f}s total={total:.1f}s "
      f"rendimiento={N/total:.1f} sol/s por worker {dict(por_worker)}")