
"""Mide la latencia de un endpoint desplegado en la nube."""

import statistics as st
import sys
import time

import requests

URL = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30

TIEMPO_ESPERA = 60

with requests.Session() as sesion:
    t = time.perf_counter()
    r = sesion.get(URL, timeout=TIEMPO_ESPERA)
    primera = (time.perf_counter() - t) * 1000

    tiempos, errores = [], 0

    for _ in range(N):
        t = time.perf_counter()

        errores += sesion.get(
            URL, timeout=TIEMPO_ESPERA
        ).status_code >= 400

        tiempos.append(
            (time.perf_counter() - t) * 1000
        )

tiempos.sort()

print(f"URL: {URL}")
print(f"primera petición: {primera:.0f} ms (código {r.status_code})")

print(
    f"siguientes {N}: "
    f"p50={st.median(tiempos):.0f} ms "
    f"p95={tiempos[int(0.95 * N) - 1]:.0f} ms "
    f"máx={tiempos[-1]:.0f} ms "
    f"errores={errores}"
)
