-- Initialize Auth Schema
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

-- Initialize Meetings Schema
DROP SCHEMA IF EXISTS meetings CASCADE;
CREATE SCHEMA meetings;

CREATE TABLE meetings.meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    owner_id INTEGER NOT NULL,
    guest_owner_id VARCHAR(255),
    google_event_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_meeting_owner FOREIGN KEY (owner_id) REFERENCES auth.users(id)
);

CREATE TABLE meetings.participants (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _meeting_user_uc UNIQUE (meeting_id, user_id),
    CONSTRAINT fk_participant_meeting FOREIGN KEY (meeting_id) REFERENCES meetings.meetings(id),
    CONSTRAINT fk_participant_user FOREIGN KEY (user_id) REFERENCES auth.users(id)
);

CREATE TABLE meetings.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    PRIMARY KEY (version_num)
);

-- Initialize Chat Schema
DROP SCHEMA IF EXISTS chat CASCADE;
CREATE SCHEMA chat;

CREATE TABLE chat.chat_messages (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_name VARCHAR(100),
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_meeting FOREIGN KEY (meeting_id) REFERENCES meetings.meetings(id),
    CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES auth.users(id)
);

CREATE TABLE chat.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    PRIMARY KEY (version_num)
); 