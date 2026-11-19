"""Mide cuánto cuesta entrenar e inferir el modelo del IA-Service (Laboratorio 5)."""

import argparse
import csv
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    import resource
except ImportError:
    resource = None

CATALOGO = {
    1: (120.0, 8),
    2: (35.0, 15),
    3: (150.0, 5),
    4: (60.0, 12),
    5: (90.0, 6),
}
TEMPORADA = {12: 1.8, 11: 1.4, 1: 1.2, 7: 1.3}
COLUMNAS = ["producto_id", "mes", "precio"]


def generar_ventas(n: int, semilla: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    prod = rng.integers(1, 6, n)
    mes = rng.integers(1, 13, n)
    precio_base = np.array([CATALOGO[int(p)][0] for p in prod])
    demanda = np.array([CATALOGO[int(p)][1] for p in prod])
    factor = np.array([TEMPORADA.get(int(m), 1.0) for m in mes])
    precio = np.round(precio_base * rng.uniform(0.9, 1.1, n), 2)
    cantidad = np.maximum(1, np.round(demanda * factor + rng.normal(0, 1.5, n)))
    return pd.DataFrame({
        "producto_id": prod,
        "mes": mes,
        "precio": precio,
        "cantidad": cantidad,
    })


def crear_modelo(n_jobs: int):
    return make_pipeline(
        ColumnTransformer(
            [("prod", OneHotEncoder(handle_unknown="ignore"), ["producto_id"])],
            remainder="passthrough",
        ),
        RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=n_jobs),
    )


def memoria_proceso_mb() -> float:
    try:
        with open("/proc/self/statm", encoding="utf-8") as f:
            paginas = int(f.read().split()[1])
        page_size = os.sysconf("SC_PAGE_SIZE")
        return (paginas * page_size) / (1024 ** 2)
    except (OSError, ValueError, AttributeError):
        if resource is None:
            return -1.0
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        divisor = (1024 ** 2) if sys.platform == "darwin" else 1024
        return rss / divisor


def tamano_modelo_mb(modelo) -> float:
    bosque = modelo[-1].estimators_
    estado = bosque[0].tree_.__getstate__()
    por_nodo = (
        estado["nodes"].nbytes + estado["values"].nbytes
    ) / estado["node_count"]
    nodos = sum(arbol.tree_.node_count for arbol in bosque)
    return (nodos * por_nodo) / (1024 ** 2)


def medir(n: int, n_jobs: int) -> dict:
    df = generar_ventas(n)
    X, y = df[COLUMNAS], df["cantidad"]
    modelo = crear_modelo(n_jobs)

    inicio = time.perf_counter()
    modelo.fit(X, y)
    t_entrenar = time.perf_counter() - inicio

    consultas = generar_ventas(1000, semilla=7)[COLUMNAS]
    inicio = time.perf_counter()
    modelo.predict(consultas)
    t_lote = time.perf_counter() - inicio

    inicio = time.perf_counter()
    for i in range(20):
        modelo.predict(consultas.iloc[[i]])
    lat_una = (time.perf_counter() - inicio) / 20 * 1000

    return {
        "filas": n,
        "n_jobs": n_jobs,
        "nucleos_maquina": os.cpu_count(),
        "entrenar_s": round(t_entrenar, 2),
        "inferir_1000_lote_s": round(t_lote, 3),
        "latencia_1_fila_ms": round(lat_una, 1),
        "modelo_mb": round(tamano_modelo_mb(modelo), 1),
        "memoria_proceso_mb": round(memoria_proceso_mb(), 1),
    }


def main():
    nucleos = os.cpu_count()
    p = argparse.ArgumentParser(
        description="Benchmark de entrenamiento e inferencia"
    )
    p.add_argument("--tamanos", type=int, nargs="+", default=[1000, 10000, 50000])
    p.add_argument("--njobs", type=int, nargs="+", default=[1, 2, 4])
    p.add_argument(
        "--salida", default=f"bench_entrenamiento_{nucleos}nucleos.csv"
    )
    args = p.parse_args()

    print(f"Máquina con {nucleos} núcleos. Puede tardar varios minutos...")
    filas = []
    for n in args.tamanos:
        for nj in args.njobs:
            fila = medir(n, nj)
            filas.append(fila)
            print(
                f"filas={n:>6} n_jobs={nj} entrenar={fila['entrenar_s']:>7} s "
                f"1000 inferencias={fila['inferir_1000_lote_s']} s "
                f"1 fila={fila['latencia_1_fila_ms']} ms "
                f"modelo={fila['modelo_mb']} MB "
                f"proceso={fila['memoria_proceso_mb']} MB",
                flush=True,
            )

    if filas:
        with open(args.salida, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            escritor.writeheader()
            escritor.writerows(filas)
        print(f"Resultados guardados en {args.salida}")


if __name__ == "__main__":
    main()