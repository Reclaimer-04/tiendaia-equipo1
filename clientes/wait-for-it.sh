#!/usr/bin/env bash
set -e

host="$1"
shift
until nc -z "$host" 3306; do
  echo "Esperando a MySQL en $host:3306..."
  sleep 2
done

exec "$@"
