import time
import requests

# 1. Geocodificación: ¿dónde está Ciudad Valles?
print("--- 1. Geocodificación ---")
t = time.perf_counter()
r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                 params={"name": "Ciudad Valles", "count": 1, "language": "es"},
                 timeout=10)
ms = (time.perf_counter() - t) * 1000
print(r.status_code, f"{ms:.0f} ms", len(r.content), "bytes")
print("Latitud y Longitud:", r.json()["results"][0]["latitude"], r.json()["results"][0]["longitude"])

# 2. Clima actual
print("\n--- 2. Clima actual ---")
t = time.perf_counter()
r = requests.get("https://api.open-meteo.com/v1/forecast",
                 params={"latitude": 21.98, "longitude": -99.01,
                         "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code"},
                 timeout=10)
ms = (time.perf_counter() - t) * 1000
print(r.status_code, f"{ms:.0f} ms", len(r.content), "bytes")
print(r.json()["current"])

# 3. Crear un recurso (POST)
print("\n--- 3. POST ---")
t = time.perf_counter()
r = requests.post("https://jsonplaceholder.typicode.com/posts",
                  json={"title": "hola", "body": "desde curl", "userId": 1},
                  timeout=10)
ms = (time.perf_counter() - t) * 1000
print(r.status_code, f"{ms:.0f} ms", len(r.content), "bytes")
print(r.json())

# 4. Un recurso que no existe (404)
print("\n--- 4. 404 Pokémon ---")
t = time.perf_counter()
r = requests.get("https://pokeapi.co/api/v2/pokemon/no-existe", timeout=10)
ms = (time.perf_counter() - t) * 1000
print(r.status_code, f"{ms:.0f} ms", len(r.content), "bytes")
print(r.text)