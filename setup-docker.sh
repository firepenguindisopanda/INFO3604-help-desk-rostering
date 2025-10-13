#!/bin/bash
# Docker Setup Script for Help Desk Rostering Application

set -e  # Exit on any error

echo " Setting up Help Desk Rostering with Docker..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo " Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo " Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f .env.docker ]; then
    echo " Creating .env.docker from template..."
    cp .env.docker.example .env.docker
    
    # Generate random passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    # Update the environment file with generated passwords
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/change_this_secure_password_123/${DB_PASSWORD}/" .env.docker
        sed -i '' "s/change-this-super-secret-key-in-production/${SECRET_KEY}/" .env.docker
    else
        sed -i "s/change_this_secure_password_123/${DB_PASSWORD}/" .env.docker
        sed -i "s/change-this-super-secret-key-in-production/${SECRET_KEY}/" .env.docker
    fi
    
    echo " Created .env.docker with generated passwords"
    echo " You can edit .env.docker to customize settings"
else
    echo " .env.docker already exists"
fi

mkdir -p docker/postgres-data

echo " Building and starting Docker services..."
docker-compose up -d --build

echo " Waiting for database to be ready..."
sleep 10

until docker-compose exec -T db pg_isready -U $(grep POSTGRES_USER .env.docker | cut -d '=' -f2) -d $(grep POSTGRES_DB .env.docker | cut -d '=' -f2); do
    echo "Waiting for PostgreSQL to start..."
    sleep 2
done

echo "Running database migrations..."
docker-compose exec -T api flask db upgrade

echo "Initializing database with sample data..."
docker-compose exec -T api flask init

echo " Setup complete!"
echo ""
echo "Application URLs:"
echo "   - API: http://localhost:8000"
echo "   - Health check: http://localhost:8000/healthcheck"
echo "   - Database: localhost:5432"
echo ""
echo " Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Database shell: docker-compose exec db psql -U \$(grep POSTGRES_USER .env.docker | cut -d '=' -f2) -d \$(grep POSTGRES_DB .env.docker | cut -d '=' -f2)"
echo "   - API shell: docker-compose exec api bash"
echo ""
echo " See docker/README.md for detailed documentation"