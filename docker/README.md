# Docker Development Setup

This guide explains how to run the Help Desk Rostering application using Docker Compose with PostgreSQL.

## Quick Start

1. **Setup environment**:
   ```bash
   # Copy the environment template
   cp .env.docker.example .env.docker
   
   # Edit the file and change passwords
   # At minimum, change POSTGRES_PASSWORD and SECRET_KEY
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**:
   ```bash
   # Run database migrations
   docker-compose exec api flask db upgrade
   
   # Initialize with sample data
   docker-compose exec api flask init
   ```

4. **Access the application**:
   - API: http://localhost:8000
   - Health check: http://localhost:8000/healthcheck
   - PostgreSQL: localhost:5432

## Services

### PostgreSQL Database (`db`)
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Database**: helpdesk_db (configurable via .env.docker)
- **Data**: Persisted in Docker volume `postgres_data`
- **Import folder**: `./docker/postgres-data/` (auto-executed on first start)

### Flask API (`api`)
- **Build**: Multi-stage Dockerfile (optimized)
- **Port**: 8000
- **Health check**: /healthcheck endpoint
- **Uploads**: Persisted in `./App/static/uploads/`

## Environment Configuration

### Required Variables (.env.docker)
```bash
# Database credentials (CHANGE THESE!)
POSTGRES_DB=helpdesk_db
POSTGRES_USER=helpdesk_user  
POSTGRES_PASSWORD=your_secure_password_here

# Flask secret (CHANGE THIS!)
SECRET_KEY=your-super-secret-flask-key

# Optional settings
FLASK_ENV=development
WEB_CONCURRENCY=2
SKIP_HELP_DESK_SAMPLE=false
```

## Database Management

### Data Import/Export

**Import SQL dump** (automatic on first start):
```bash
# Place SQL files in docker/postgres-data/
cp your-backup.sql docker/postgres-data/01-restore.sql
docker-compose up -d  # Will auto-import on first DB creation
```

**Import SQL dump** (manual):
```bash
# Copy file to running container
docker cp backup.sql helpdesk_postgres:/tmp/backup.sql

# Import via psql
docker-compose exec db psql -U helpdesk_user -d helpdesk_db -f /tmp/backup.sql
```

**Export database**:
```bash
# Full database dump
docker-compose exec db pg_dump -U helpdesk_user helpdesk_db > backup-$(date +%Y%m%d).sql

# Specific tables only
docker-compose exec db pg_dump -U helpdesk_user -t user -t student helpdesk_db > users-backup.sql
```

### Database Access
```bash
# Connect to PostgreSQL directly
docker-compose exec db psql -U helpdesk_user -d helpdesk_db

# View database logs
docker-compose logs db

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

## Development Workflow

### Common Commands
```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f db

# Restart API only (after code changes)
docker-compose restart api

# Run Flask commands
docker-compose exec api flask --help
docker-compose exec api flask user create admin adminpass
docker-compose exec api flask db migrate -m "Add new table"

# Access API container shell
docker-compose exec api bash

# Stop all services
docker-compose down

# Stop and remove volumes (reset everything)
docker-compose down -v
```

### Code Development
The API service mounts your source code as read-only volumes for development:
- `./App` -> `/app/App` (Flask application)  
- `./wsgi.py` -> `/app/wsgi.py` (WSGI entry point)
- `./gunicorn_config.py` -> `/app/gunicorn_config.py` (server config)

After code changes, restart the API:
```bash
docker-compose restart api
```

For production deployment, remove the volume mounts in docker-compose.yml.

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is ready
docker-compose exec db pg_isready -U helpdesk_user

# Check database logs
docker-compose logs db

# Verify environment variables
docker-compose exec api env | grep DATABASE_URL
```

### API Issues
```bash
# Check API health
curl http://localhost:8000/healthcheck

# Check API logs
docker-compose logs api

# Debug inside container
docker-compose exec api bash
```

### Port Conflicts
If ports 5432 or 8000 are in use, override in docker-compose.override.yml:
```yaml
version: '3.8'
services:
  db:
    ports:
      - "5433:5432"  # Use port 5433 instead
  api:
    ports:
      - "8001:8000"  # Use port 8001 instead
```

### Performance Tuning
Edit `docker/postgres.conf` to adjust PostgreSQL settings:
- `shared_buffers`: Increase for more RAM
- `max_connections`: Adjust connection limit
- `log_min_duration_statement`: Set to 0 to log all queries

## Production Considerations

1. **Security**: Change all default passwords in .env.docker
2. **Volumes**: Use named volumes or bind mounts for data persistence
3. **Networks**: Consider using custom networks for isolation
4. **Monitoring**: Add health checks and log aggregation
5. **Backups**: Set up automated database backups
6. **SSL**: Configure SSL certificates for HTTPS
7. **Environment**: Set FLASK_ENV=production and DEBUG=False