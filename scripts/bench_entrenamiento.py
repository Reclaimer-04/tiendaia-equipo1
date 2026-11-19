"""Mide cuánto cuesta entrenar e inferir el modelo del IA-Service (Laboratorio 5)."""
import argparse
import csv
import os
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

CATALOGO = {1: (120.0, 8), 2: (35.0, 15), 3: (150.0, 5), 4: (60.0, 12), 5: (90.0, 6)}
TEMPORADA = {12: 1.8, 11: 1.4, 1: 1.2, 7: 1.3}
COLUMNAS = ["producto_id", "mes", "precio"]


def generar_ventas(n: int, semilla: int = 42) -> pd.DataFrame:
    """Devuelve un DataFrame con n ventas sintéticas."""
    rng = np.random.default_rng(semilla)
    prod = rng.integers(1, 6, n)
    mes = rng.integers(1, 13, n)
    precio_base = np.array([CATALOGO[p][0] for p in prod])
    demanda = np.array([CATALOGO[p][1] for p in prod])
    factor = np.array([TEMPORADA.get(m, 1.0) for m in mes])
    precio = np.round(precio_base * rng.uniform(0.9, 1.1, n), 2)
    cantidad = np.maximum(1, np.round(demanda * factor + rng.normal(0, 1.5, n)))
    return pd.DataFrame({
        "producto_id": prod,
        "mes": mes,
        "precio": precio,
        "cantidad": cantidad,
    })


def crear_modelo(n_jobs: int):
    """Crea el pipeline con OneHotEncoder y RandomForestRegressor."""
    return make_pipeline(
        ColumnTransformer(
            [("prod", OneHotEncoder(handle_unknown="ignore"), ["producto_id"])],
            remainder="passthrough",
        ),
        RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=n_jobs),
    )


def memoria_proceso_mb() -> float:
    """Memoria RSS del proceso actual en MB."""
    try:
        with open("/proc/self/statm", encoding="utf-8") as f:
            paginas = int(f.read().split()[1])
        return paginas * os.sysconf("SC_PAGE_SIZE") / 1024 ** 2
    except (OSError, ValueError, AttributeError):
        if resource is None:
            return -1.0
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2


def tamano_modelo_mb(modelo) -> float:
    """Calcula el tamaño aproximado en MB de los árboles del bosque."""
    bosque = modelo[-1].estimators_
    estado = bosque[0].tree_.__getstate__()
    por_nodo = (estado["nodes"].nbytes + estado["values"].nbytes) / estado["node_count"]
    nodos = sum(arbol.tree_.node_count for arbol in bosque)
    return nodos * por_nodo / 1024 ** 2


def medir(n: int, n_jobs: int) -> dict:
    """Mide entrenamiento e inferencia para n filas y n_jobs núcleos."""
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