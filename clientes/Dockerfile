FROM python:3.12-slim

WORKDIR /app

# Instalar netcat para que wait-for-it.sh funcione
RUN apt-get update && apt-get install -y netcat-openbsd

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

EXPOSE 8000

ENTRYPOINT ["/wait-for-it.sh", "mysql", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
 #correccion