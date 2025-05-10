-- Insert version info for each service
-- Values should match the version IDs to create (will be used in migration scripts)

-- Auth service version
INSERT INTO auth.alembic_version (version_num) VALUES ('5a1c414e6123');

-- Meeting service version
INSERT INTO meetings.alembic_version (version_num) VALUES ('3b7d9c82a516');

-- Chat service version 
INSERT INTO chat.alembic_version (version_num) VALUES ('7f452a69c018'); 