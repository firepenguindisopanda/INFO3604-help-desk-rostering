# -*- coding: utf-8 -*-
import psycopg2
from psycopg2 import sql
import sys
import csv
import os
from werkzeug.security import generate_password_hash

def connect_to_database():
    """Connect to the PostgreSQL database"""
    connection_string = "postgresql://flask_postgres_api_db_user:cR6VhPlUISY8ukqOGSM1sN4jn5TGa5eT@dpg-d2q86el6ubrc73d33d80-a.oregon-postgres.render.com/flask_postgres_api_db"
    # connection_string = "postgresql://neondb_owner:npg_M9NLwQJqs8tZ@ep-shiny-smoke-adsd00ve-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    try:
        conn = psycopg2.connect(connection_string)
        print("Successfully connected to the database!")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_database_info(conn):
    """Get basic database information"""
    try:
        cursor = conn.cursor()
        
        # Get database version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n📊 Database Version: {version}")
        
        # Get current database name
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"📋 Current Database: {db_name}")
        
        cursor.close()
    except psycopg2.Error as e:
        print(f"❌ Error getting database info: {e}")

def list_tables(conn):
    """List all tables in the database"""
    try:
        cursor = conn.cursor()
        
        # Get all tables in the public schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n📝 Found {len(tables)} table(s):")
            for i, (table_name,) in enumerate(tables, 1):
                print(f"  {i}. {table_name}")
        else:
            print("\n📝 No tables found in the database")
        
        cursor.close()
        return [table[0] for table in tables]
    except psycopg2.Error as e:
        print(f"❌ Error listing tables: {e}")
        return []

def analyze_table(conn, table_name):
    """Analyze a specific table"""
    try:
        cursor = conn.cursor()
        
        print(f"\n🔍 Analyzing table: {table_name}")
        print("-" * 40)
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        if columns:
            print("📋 Table Structure:")
            for col_name, data_type, is_nullable, default in columns:
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                default_val = f", Default: {default}" if default else ""
                print(f"  • {col_name}: {data_type} ({nullable}{default_val})")
        
        # Get row count
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table_name)
        ))
        row_count = cursor.fetchone()[0]
        print(f"\n📊 Row Count: {row_count}")
        
        # Show sample data if table has rows
        if row_count > 0:
            cursor.execute(sql.SQL("SELECT * FROM {} LIMIT 5").format(
                sql.Identifier(table_name)
            ))
            sample_data = cursor.fetchall()
            
            print(f"\n📄 Sample Data (first 5 rows):")
            col_names = [desc[0] for desc in cursor.description]
            
            # Print column headers
            print("  " + " | ".join(f"{col:<15}" for col in col_names))
            print("  " + "-" * (len(col_names) * 17))
            
            # Print sample rows
            for row in sample_data:
                formatted_row = []
                for item in row:
                    if item is None:
                        formatted_row.append("NULL")
                    else:
                        str_item = str(item)
                        formatted_row.append(str_item[:15] if len(str_item) > 15 else str_item)
                print("  " + " | ".join(f"{item:<15}" for item in formatted_row))
        
        cursor.close()
        
    except psycopg2.Error as e:
        print(f"❌ Error analyzing table {table_name}: {e}")

def hash_password(password):
    """Hash password using Werkzeug's generate_password_hash (same as the app)"""
    return generate_password_hash(password)

def create_tables(conn):
    """Create all necessary tables - matching the application's schema exactly"""
    try:
        cursor = conn.cursor()
        
        # Create users table (main table name in the app)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(20) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL
            )
        """)
        
        # Create student table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student (
                username VARCHAR(20) PRIMARY KEY REFERENCES users(username),
                degree VARCHAR(3) DEFAULT 'BSc',
                name VARCHAR(100),
                profile_data TEXT
            )
        """)
        
        # Create admin table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                username VARCHAR(20) PRIMARY KEY REFERENCES users(username),
                role VARCHAR(20) NOT NULL
            )
        """)
        
        # Create course table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            )
        """)
        
        # Create help_desk_assistant table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS help_desk_assistant (
                username VARCHAR(20) PRIMARY KEY REFERENCES student(username),
                rate DOUBLE PRECISION NOT NULL,
                active BOOLEAN NOT NULL,
                hours_worked INTEGER NOT NULL,
                hours_minimum INTEGER NOT NULL
            )
        """)
        
        # Create lab_assistant table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_assistant (
                username VARCHAR(20) PRIMARY KEY REFERENCES student(username),
                active BOOLEAN NOT NULL,
                experience BOOLEAN NOT NULL
            )
        """)
        
        # Create availability table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL REFERENCES student(username),
                day_of_week INTEGER NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL
            )
        """)
        
        # Create course_capability table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_capability (
                id SERIAL PRIMARY KEY,
                assistant_username VARCHAR(20) NOT NULL REFERENCES help_desk_assistant(username),
                course_code VARCHAR(10) NOT NULL
            )
        """)
        
        # Create additional tables that exist in the app but might not be core to initialization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL,
                message VARCHAR(255) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration_request (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                degree VARCHAR(3) NOT NULL,
                reason TEXT,
                transcript_path VARCHAR(255),
                profile_picture_path VARCHAR(255) NOT NULL,
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by VARCHAR(20),
                password VARCHAR(255)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration_course (
                id SERIAL PRIMARY KEY,
                registration_id INTEGER NOT NULL REFERENCES registration_request(id),
                course_code VARCHAR(10) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_requests (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL,
                reason VARCHAR(255),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by VARCHAR(20),
                rejection_reason VARCHAR(255)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id SERIAL PRIMARY KEY,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                type VARCHAR(50) NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_published BOOLEAN DEFAULT FALSE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shift (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                schedule_id INTEGER REFERENCES schedule(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shift_course_demand (
                id SERIAL PRIMARY KEY,
                shift_id INTEGER NOT NULL REFERENCES shift(id),
                course_code VARCHAR(10) NOT NULL,
                tutors_required INTEGER NOT NULL,
                weight INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS allocation (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL REFERENCES student(username),
                shift_id INTEGER NOT NULL REFERENCES shift(id),
                schedule_id INTEGER NOT NULL REFERENCES schedule(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL,
                shift_id INTEGER REFERENCES shift(id),
                date TIMESTAMP,
                time_slot VARCHAR(50) NOT NULL,
                reason TEXT NOT NULL,
                replacement VARCHAR(20),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                rejected_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semester (
                id SERIAL PRIMARY KEY,
                academic_year VARCHAR(20) NOT NULL,
                semester INTEGER NOT NULL,
                "start" TIMESTAMP NOT NULL,
                "end" TIMESTAMP NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entry (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) NOT NULL,
                shift_id INTEGER REFERENCES shift(id),
                clock_in TIMESTAMP NOT NULL,
                clock_out TIMESTAMP,
                status VARCHAR(20)
            )
        """)
        
        # Create alembic_version table for migrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) PRIMARY KEY
            )
        """)
        
        conn.commit()
        cursor.close()
        print("✅ All tables created successfully")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()

def drop_all_tables(conn):
    """Drop all tables to start fresh"""
    try:
        cursor = conn.cursor()
        
        # Drop tables in reverse order of dependencies
        tables_to_drop = [
            'course_capability',
            'availability',
            'time_entry',
            'request',
            'allocation',
            'shift_course_demand',
            'shift',
            'schedule',
            'registration_course',
            'registration_request',
            'password_reset_requests',
            'notification',
            'help_desk_assistant',
            'lab_assistant',
            'admin',
            'student',
            'course',
            'semester',
            'alembic_version',
            'users',
            'user'
        ]
        
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        
        conn.commit()
        cursor.close()
        print("✅ All existing tables dropped")
        
    except psycopg2.Error as e:
        print(f"❌ Error dropping tables: {e}")
        conn.rollback()

def create_admins(conn):
    """Create admin users"""
    try:
        cursor = conn.cursor()
        
        # Create admin 'a' with role 'helpdesk'
        hashed_password = hash_password('123')
        cursor.execute("""
            INSERT INTO users (username, password, type) 
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('a', hashed_password, 'admin'))
        
        cursor.execute("""
            INSERT INTO admin (username, role) 
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('a', 'helpdesk'))
        
        # Create admin 'b' with role 'lab'
        cursor.execute("""
            INSERT INTO users (username, password, type) 
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('b', hashed_password, 'admin'))
        
        cursor.execute("""
            INSERT INTO admin (username, role) 
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('b', 'lab'))
        
        conn.commit()
        cursor.close()
        print("✅ Admin users created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating admins: {e}")
        conn.rollback()

def create_courses(conn):
    """Create courses from CSV"""
    try:
        cursor = conn.cursor()
        
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample')
        courses_file = os.path.join(sample_dir, 'courses.csv')
        
        with open(courses_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cursor.execute("""
                    INSERT INTO course (code, name) 
                    VALUES (%s, %s)
                    ON CONFLICT (code) DO NOTHING
                """, (row['code'], row['name']))
        
        conn.commit()
        cursor.close()
        print("✅ Courses created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating courses: {e}")
        conn.rollback()
    except FileNotFoundError:
        print("❌ Error: sample/courses.csv not found")

def create_help_desk_assistants(conn):
    """Create help desk assistants from CSV"""
    try:
        cursor = conn.cursor()
        
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample')
        assistants_file = os.path.join(sample_dir, 'help_desk_assistants.csv')
        
        with open(assistants_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Create user
                hashed_password = hash_password(row['password'])
                cursor.execute("""
                    INSERT INTO users (username, password, type) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], hashed_password, 'student'))
                
                # Create student
                cursor.execute("""
                    INSERT INTO student (username, degree, name) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], row['degree'], row['name']))
                
                # Create help desk assistant with proper rate calculation
                rate = 35.0 if row['degree'] == 'MSc' else 20.0
                cursor.execute("""
                    INSERT INTO help_desk_assistant (username, rate, active, hours_worked, hours_minimum) 
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], rate, True, 0, 4))
        
        conn.commit()
        cursor.close()
        print("✅ Help desk assistants created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating help desk assistants: {e}")
        conn.rollback()
    except FileNotFoundError:
        print("❌ Error: sample/help_desk_assistants.csv not found")

def create_lab_assistants(conn):
    """Create lab assistants from CSV"""
    try:
        cursor = conn.cursor()
        
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample')
        assistants_file = os.path.join(sample_dir, 'lab_assistants.csv')
        
        with open(assistants_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Create user
                hashed_password = hash_password(row['password'])
                cursor.execute("""
                    INSERT INTO users (username, password, type) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], hashed_password, 'student'))
                
                # Create student
                cursor.execute("""
                    INSERT INTO student (username, degree, name) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], row['degree'], row['name']))
                
                # Create lab assistant
                cursor.execute("""
                    INSERT INTO lab_assistant (username, active, experience) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (row['username'], True, bool(int(row['experience']))))
        
        conn.commit()
        cursor.close()
        print("✅ Lab assistants created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating lab assistants: {e}")
        conn.rollback()
    except FileNotFoundError:
        print("❌ Error: sample/lab_assistants.csv not found")

def create_availability_data(conn):
    """Create availability data from CSV files"""
    try:
        cursor = conn.cursor()
        
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample')
        
        # Help desk assistants availability
        hd_file = os.path.join(sample_dir, 'help_desk_assistants_availability.csv')
        with open(hd_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cursor.execute("""
                    INSERT INTO availability (username, day_of_week, start_time, end_time) 
                    VALUES (%s, %s, %s, %s)
                """, (row['username'], int(row['day_of_week']), row['start_time'], row['end_time']))
        
        # Lab assistants availability
        lab_file = os.path.join(sample_dir, 'lab_assistants_availability.csv')
        with open(lab_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cursor.execute("""
                    INSERT INTO availability (username, day_of_week, start_time, end_time) 
                    VALUES (%s, %s, %s, %s)
                """, (row['username'], int(row['day_of_week']), row['start_time'], row['end_time']))
        
        conn.commit()
        cursor.close()
        print("✅ Availability data created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating availability data: {e}")
        conn.rollback()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")

def create_course_capabilities(conn):
    """Create course capabilities from CSV"""
    try:
        cursor = conn.cursor()
        
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample')
        capabilities_file = os.path.join(sample_dir, 'help_desk_assistants_courses.csv')
        
        with open(capabilities_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cursor.execute("""
                    INSERT INTO course_capability (assistant_username, course_code) 
                    VALUES (%s, %s)
                """, (row['username'], row['code']))
        
        conn.commit()
        cursor.close()
        print("✅ Course capabilities created")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating course capabilities: {e}")
        conn.rollback()
    except FileNotFoundError:
        print("❌ Error: sample/help_desk_assistants_courses.csv not found")

def populate_database_full(conn):
    """Populate the database with complete sample data including help desk assistants"""
    try:
        print("🔄 Dropping existing tables...")
        drop_all_tables(conn)
        
        print("🔄 Creating database tables...")
        create_tables(conn)
        
        print("🔄 Populating database with complete sample data...")
        
        # Create admin users
        create_admins(conn)
        
        # Create courses
        create_courses(conn)
        
        # Create help desk assistants
        create_help_desk_assistants(conn)
        
        # Create lab assistants
        create_lab_assistants(conn)
        
        # Create availability data
        create_availability_data(conn)
        
        # Create course capabilities
        create_course_capabilities(conn)
        
        print("✅ Database populated successfully with complete sample data!")
        
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        conn.rollback()

def populate_database(conn):
    """Populate the database with sample data using psycopg2"""
    try:
        print("🔄 Dropping existing tables...")
        drop_all_tables(conn)
        
        print("🔄 Creating database tables...")
        create_tables(conn)
        
        print("🔄 Populating database with sample data...")
        
        # Create admin users
        create_admins(conn)
        
        # Create courses
        create_courses(conn)
        
        # Create help desk assistants
        # create_help_desk_assistants(conn)
        
        # Create lab assistants
        create_lab_assistants(conn)
        
        # Create availability data
        # create_availability_data(conn)
        
        # Create course capabilities
        # create_course_capabilities(conn)
        
        print("✅ Database populated successfully with sample data!")
        
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        conn.rollback()

# provide a quick function to remove the user table
def remove_user_table(conn):
    """
    Remove the user table and all dependent objects.
    This will CASCADE to drop foreign key constraints and dependent data.
    Note: 'user' is a reserved keyword in PostgreSQL, so we need to quote it.
    """
    try:
        with conn.cursor() as cursor:
            # Use CASCADE to drop all dependent objects (foreign keys, dependent data)
            # Quote "user" because it's a reserved keyword in PostgreSQL
            cursor.execute('DROP TABLE IF EXISTS "user" CASCADE')
            conn.commit()
            print("✅ User table and all dependent objects removed successfully!")
            print("⚠️  Warning: This also removed all data from tables that reference user (admin, student, etc.)")
    except Exception as e:
        print(f"❌ Error removing user table: {e}")
        conn.rollback()

def main():
    """Main function to run the database check"""
    print("Connecting to Render PostgreSQL Database...")
    print("=" * 50)
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        sys.exit(1)
    
    try:
        # Get database info
        get_database_info(conn)
        
        # List all tables
        tables = list_tables(conn)
        
        # Analyze each table
        if tables:
            print("\nAnalyzing all tables...")
            print("=" * 50)
            
            for table in tables:
                analyze_table(conn, table)
        else:
            print("\nThe database appears to be empty (no tables found)")
        
        print("\nDatabase analysis complete!")
        

        
        # Test database population with complete sample data (uncomment to test)
        # print("\nTesting FULL database population to ensure it matches the app exactly...")
        # populate_database_full(conn)
        # populate_database(conn)
        # remove_user_table(conn)
        
    finally:
        # Close connection
        conn.close()
        print("Database connection closed")

if __name__ == "__main__":
    main()