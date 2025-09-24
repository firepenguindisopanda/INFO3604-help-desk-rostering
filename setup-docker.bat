@echo off
REM Docker Setup Script for Help Desk Rostering Application (Windows)

echo  Setting up Help Desk Rostering with Docker...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Docker Compose is not installed. Please install Docker Desktop or Docker Compose first.
    pause
    exit /b 1
)

REM Create environment file if it doesn't exist
if not exist .env.docker (
    echo  Creating .env.docker from template...
    copy .env.docker.example .env.docker
    echo  Created .env.docker
    echo  Please edit .env.docker and change the default passwords before continuing!
    echo    - Change POSTGRES_PASSWORD
    echo    - Change SECRET_KEY
    echo.
    pause
) else (
    echo  .env.docker already exists
)

REM Create docker directory if it doesn't exist
if not exist docker\postgres-data mkdir docker\postgres-data

echo Building and starting Docker services...
docker-compose up -d --build

if %errorlevel% neq 0 (
    echo Failed to start Docker services
    pause
    exit /b 1
)

echo Waiting for database to be ready...
timeout /t 10 /nobreak >nul

REM Wait for database to be ready (simplified check)
echo Running database migrations...
docker-compose exec -T api flask db upgrade

if %errorlevel% neq 0 (
    echo Database migration failed. Checking if database is ready...
    docker-compose exec -T db pg_isready
    echo Please wait a moment and try running: docker-compose exec api flask db upgrade
    pause
    exit /b 1
)

echo Initializing database with sample data...
docker-compose exec -T api flask init

echo Setup complete!
echo.
echo Application URLs:
echo    - API: http://localhost:8000
echo    - Health check: http://localhost:8000/healthcheck
echo    - Database: localhost:5432
echo.
echo Useful commands:
echo    - View logs: docker-compose logs -f
echo    - Stop services: docker-compose down
echo    - Database shell: docker-compose exec db psql -U helpdesk_user -d helpdesk_db
echo    - API shell: docker-compose exec api bash
echo.
echo See docker\README.md for detailed documentation
pause