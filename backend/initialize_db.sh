#!/bin/bash

# Initialize and run database migrations for all services
# This script should be run after starting all services with docker-compose up

echo "Initializing database migrations for all services..."

# Wait for database to be ready
echo "Waiting for database to be available..."
sleep 10

# Initialize PostgreSQL schemas for each service
echo "Creating PostgreSQL schemas..."
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS auth;"
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS meetings;"
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS chat;"

# Initialize migrations for auth-service
echo "Initializing auth-service migrations..."
docker-compose exec auth-service flask db init || echo "Migration already initialized for auth-service"
docker-compose exec auth-service flask db migrate -m "Initial migration for auth-service"
docker-compose exec auth-service flask db upgrade

# Initialize migrations for meeting-service
echo "Initializing meeting-service migrations..."
docker-compose exec meeting-service flask db init || echo "Migration already initialized for meeting-service"
docker-compose exec meeting-service flask db migrate -m "Initial migration for meeting-service"
docker-compose exec meeting-service flask db upgrade

# Initialize migrations for chat-service
echo "Initializing chat-service migrations..."
docker-compose exec chat-service flask db init || echo "Migration already initialized for chat-service"
docker-compose exec chat-service flask db migrate -m "Initial migration for chat-service"
docker-compose exec chat-service flask db upgrade

echo "Database migrations completed!" 