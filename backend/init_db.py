import os
import sys
import psycopg2

# Database connection parameters
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'appdb')
DB_USER = os.environ.get('DB_USER', 'appuser')
DB_PASS = os.environ.get('DB_PASS', 'secret')

# SQL statements to create tables
auth_tables = """
DROP SCHEMA IF EXISTS auth CASCADE;
CREATE SCHEMA auth;

CREATE TABLE auth.users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE auth.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    PRIMARY KEY (version_num)
);
"""

meetings_tables = """
DROP SCHEMA IF EXISTS meetings CASCADE;
CREATE SCHEMA meetings;

CREATE TABLE meetings.meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES auth.users(id),
    google_event_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meetings.participants (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings.meetings(id),
    user_id INTEGER NOT NULL REFERENCES auth.users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _meeting_user_uc UNIQUE (meeting_id, user_id)
);

CREATE TABLE meetings.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    PRIMARY KEY (version_num)
);
"""

chat_tables = """
DROP SCHEMA IF EXISTS chat CASCADE;
CREATE SCHEMA chat;

CREATE TABLE chat.chat_messages (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings.meetings(id),
    user_id INTEGER NOT NULL REFERENCES auth.users(id),
    user_name VARCHAR(100),
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    PRIMARY KEY (version_num)
);
"""

def main():
    # Connect to the database
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Creating auth schema and tables...")
        cursor.execute(auth_tables)
        
        print("Creating meetings schema and tables...")
        cursor.execute(meetings_tables)
        
        print("Creating chat schema and tables...")
        cursor.execute(chat_tables)
        
        print("Database initialization complete!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 