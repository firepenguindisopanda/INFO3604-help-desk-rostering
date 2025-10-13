# PostgreSQL Data Import Directory

This directory is mounted to `/docker-entrypoint-initdb.d/` in the PostgreSQL container.

## Usage

### Automatic Initialization
Any `.sql`, `.sql.gz`, or `.sh` files placed in this directory will be automatically executed when the PostgreSQL container starts for the first time (when the database is empty).

### Manual Data Import
1. **Copy SQL dump files here**: Place your `.sql` dump files in this directory
2. **Access the container**: 
   ```bash
   docker-compose exec db bash
   ```
3. **Import manually**:
   ```bash
   psql -U helpdesk_user -d helpdesk_db -f /docker-entrypoint-initdb.d/your-dump.sql
   ```

### Export Data
```bash
# Export full database
docker-compose exec db pg_dump -U helpdesk_user helpdesk_db > backup.sql

# Export specific tables
docker-compose exec db pg_dump -U helpdesk_user -t user -t student helpdesk_db > users_backup.sql
```

### Examples

#### sample_data.sql
```sql
-- Sample initialization script
INSERT INTO course (code, name) VALUES 
('COMP1601', 'Computer Programming I'),
('COMP2601', 'Computer Programming II');
```

#### restore_backup.sql
```sql
-- Place your database backup/restore commands here
-- This will run automatically on first container startup
```

## File Execution Order
Files are executed in alphabetical order. Use prefixes like:
- `01_schema.sql`
- `02_data.sql` 
- `03_indexes.sql`