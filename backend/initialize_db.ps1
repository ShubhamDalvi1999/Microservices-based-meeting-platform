# Initialize and run database migrations for all services
# This script should be run after starting all services with docker-compose up

Write-Host "Initializing database migrations for all services..."

# Wait for database to be ready
Write-Host "Waiting for database to be available..."
Start-Sleep -Seconds 10

# Initialize PostgreSQL schemas for each service
Write-Host "Creating PostgreSQL schemas..."
# Uncommented schema creation to ensure proper schema isolation
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS auth;"
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS meetings;"
docker-compose exec db psql -U appuser -d appdb -c "CREATE SCHEMA IF NOT EXISTS chat;"

# Initialize migrations for auth-service
Write-Host "Initializing auth-service migrations..."
docker-compose exec auth-service flask db init 
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Migration already initialized for auth-service" 
}
docker-compose exec auth-service flask db migrate -m "Initial migration for auth-service"
docker-compose exec auth-service flask db upgrade

# Initialize migrations for meeting-service
Write-Host "Initializing meeting-service migrations..."
docker-compose exec meeting-service flask db init
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Migration already initialized for meeting-service" 
}
docker-compose exec meeting-service flask db migrate -m "Initial migration for meeting-service"
docker-compose exec meeting-service flask db upgrade

# Initialize migrations for chat-service
Write-Host "Initializing chat-service migrations..."
docker-compose exec chat-service flask db init
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Migration already initialized for chat-service" 
}
docker-compose exec chat-service flask db migrate -m "Initial migration for chat-service"
docker-compose exec chat-service flask db upgrade

Write-Host "Database migrations completed!" 