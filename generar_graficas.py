import pandas as pd
import matplotlib.pyplot as plt

# Cargar datos
df = pd.read_csv("resultados_almacenamiento.csv", encoding="latin1")
df["valor"] = df["media"].astype(str) + " +/- " + df["desv"].astype(str)

# 1. Crear tabla comparativa
tabla = df.pivot_table(index="prueba", columns="destino", values="valor", aggfunc="last")
print("\n--- Tabla Comparativa ---")
print(tabla.to_string())
tabla.to_csv("tabla_comparativa.csv")

# 2. Gráfica de Subida
plt.figure(figsize=(8, 5))
sub = df[df["prueba"].str.startswith("subida")].copy()
sub["mb"] = sub["prueba"].str.split().str[1].astype(int)
for destino, d in sub.groupby("destino"):
    d = d.groupby("mb")[["media", "desv"]].last()
    plt.errorbar(d.index, d["media"], yerr=d["desv"], marker="o", capsize=3, label=destino)
plt.xlabel("Tamaño del archivo (MB)")
plt.ylabel("Velocidad de Subida (MB/s)")
plt.title("Rendimiento de Subida por Proveedor")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.savefig("grafica_subida.png", dpi=150)
plt.close()

# 3. Gráfica de Bajada
plt.figure(figsize=(8, 5))
baj = df[df["prueba"].str.startswith("bajada")].copy()
baj["mb"] = baj["prueba"].str.split().str[1].astype(int)
for destino, d in baj.groupby("destino"):
    d = d.groupby("mb")[["media", "desv"]].last()
    plt.errorbar(d.index, d["media"], yerr=d["desv"], marker="o", capsize=3, label=destino)
plt.xlabel("Tamaño del archivo (MB)")
plt.ylabel("Velocidad de Bajada (MB/s)")
plt.title("Rendimiento de Bajada por Proveedor")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.savefig("grafica_bajada.png", dpi=150)
plt.close()

print("\n¡Listo! Se generaron: tabla_comparativa.csv, grafica_subida.png y grafica_bajada.png")