#!/bin/bash
# init-databases.sh
# Runs once on first container start to create the two application databases.
# Called by the postgres entrypoint as the postgres superuser.
set -e

# agri_auth  — Express gateway / Prisma (users, sessions, refresh tokens)
# agri_memory — FastAPI / LangGraph (conversation checkpoints, agent state)

for DB in agri_auth agri_memory; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE "$DB"'
    WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$DB')\gexec
EOSQL
  echo "Database '$DB': ready."
done
