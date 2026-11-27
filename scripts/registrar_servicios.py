"""Lab. 6: registra cada microservicio en Auth-Service y guarda sus API Keys.
Las llaves quedan en el archivo .env.claves.
Uso: python scripts/registrar_servicios.py http://localhost:8081 <contraseña-admin>
Después: docker compose --env-file .env --env-file .env.claves up -d
"""
import sys
import requests  # cliente HTTP para llamar al gateway

GW, CONTRASENA = sys.argv[1], sys.argv[2]
SERVICIOS = ["gateway", "ventas", "ia", "imagenes"]  # quienes LLAMAN a otros
TIEMPO_ESPERA = 10
sesion = requests.Session()

# Inicio de sesión: usuario y contraseña -> token JWT de acceso
token = sesion.post(
    f"{GW}/api/auth/login",
    timeout=TIEMPO_ESPERA,
    json={"usuario": "admin", "contrasena": CONTRASENA},
)
token.raise_for_status()

cab = {"Authorization": f"Bearer {token.json()['access_token']}"}

with open(".env.claves", "w") as f:
    for s in SERVICIOS:
        r = sesion.post(
            f"{GW}/api/auth/servicios",
            json={"servicio": s},
            headers=cab,
            timeout=TIEMPO_ESPERA,
        )
        r.raise_for_status()
        # La API Key solo se muestra una vez: se anota ya
        f.write(f"API_KEY_{s.upper()}={r.json()['api_key']}\n")
        print("registrado:", s)

print("Claves guardadas en .env.claves (agregue el archivo a .gitignore)")