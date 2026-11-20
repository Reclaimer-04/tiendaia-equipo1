# TiendaIA — Equipo 1

Proyecto de tienda en línea desarrollado mediante microservicios. Este repositorio reúne los componentes de los laboratorios 2, 3 y 4.

## Integrantes

- Jose Maria Santiago Antonio
- Saul Gonzales Campillo
- Adiel Josafat Aguilar Hernandez

## Arquitectura

La configuración Docker Compose contempla:

- **Bases de datos:** MySQL, MongoDB y Redis.
- **Microservicios:** clientes, productos, ventas e inteligencia artificial.
- **Comunicación:** RabbitMQ.
- **Acceso:** API Gateway y frontend estático servido con Nginx.
- **Almacenamiento de objetos:** SeaweedFS (interfaz S3) y Azurite (Azure Blob Storage).
- **Procesos en segundo plano:** notificaciones, worker de IA e IA listener.

## Requisitos

- Docker Engine o Docker Desktop.
- Docker Compose v2.
- Archivos/código fuente de los servicios y carpeta `frontend` presentes en la raíz del proyecto.

## Preparación

1. Copia `.env.ejemplo` como `.env`.
2. Cambia las contraseñas y secretos de ejemplo.
3. Crea la configuración S3 de SeaweedFS:

   ```bash
   mkdir -p seaweed
   cp seaweed/s3.ejemplo.json seaweed/s3.json
   ```

4. Edita `seaweed/s3.json` y coloca el mismo `accessKey` y `secretKey` definidos en `.env` (`S3_ADMIN_KEY` y `S3_ADMIN_SECRET`).
5. Verifica que `.env` y `seaweed/s3.json` estén excluidos de Git. No publiques secretos reales.

> La configuración S3 de ejemplo contiene credenciales de demostración. Cámbialas antes de cualquier uso compartido o despliegue.

## Ejecución local

Desde la carpeta raíz:

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

`docker compose config` permite detectar errores de sintaxis y variables requeridas sin iniciar los contenedores.

## Direcciones locales

- API Gateway: http://localhost:8080
- Frontend Nginx: http://localhost:8081
- SeaweedFS S3: http://localhost:8333
- Azurite Blob: http://localhost:10000
- RabbitMQ Management: http://localhost:15672 (publicado solo en la interfaz local)

Las rutas concretas de la API dependen de los endpoints implementados en cada microservicio; consulta su código fuente o documentación.

## Comandos útiles

```bash
# Ver estado
docker compose ps

# Consultar logs de un servicio
docker compose logs -f gateway

# Consultar logs de todos los servicios
docker compose logs -f

# Detener los contenedores
docker compose down

# Detener y eliminar también los volúmenes (BORRA los datos persistidos)
docker compose down -v
```

## Notas de configuración

- Los healthchecks HTTP se reservan para servicios que exponen `/health`.
- Los consumidores de segundo plano (`notificaciones`, `worker` e `ia_listener`) no heredan el healthcheck HTTP, porque su función principal es consumir mensajes o ejecutar tareas.
- Las dependencias con `condition: service_healthy` esperan a que las bases de datos y servicios HTTP declaren estar saludables.
- Para RabbitMQ local, `RABBITMQ_HOST` debe ser `rabbitmq`, que es el nombre del servicio dentro de la red Docker.
- El contenedor `imagenes` recibe configuración para SeaweedFS y Azurite. La selección efectiva del proveedor depende de cómo la implemente el código del microservicio.

## Solución de problemas

1. Si Compose informa que falta una variable, revisa que hayas creado `.env` a partir de `.env.ejemplo`.
2. Si SeaweedFS no inicia, comprueba que exista `seaweed/s3.json` y que su JSON sea válido.
3. Si el servicio de imágenes no autentica contra S3, verifica que las credenciales de `.env` coincidan exactamente con las de `seaweed/s3.json`.
4. Si un contenedor HTTP queda `unhealthy`, confirma que realmente exponga `GET /health` en el puerto `8000`.
