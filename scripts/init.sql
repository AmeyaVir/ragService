-- Initial database setup for Analytics RAG Platform

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    tenant_id INTEGER REFERENCES tenants(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- NEW: Fields for Google Drive OAuth token
    gdrive_refresh_token TEXT, 
    gdrive_linked_at TIMESTAMP WITH TIME ZONE
);

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tenant_id INTEGER REFERENCES tenants(id),
    folder_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    project_id INTEGER REFERENCES projects(id),
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert demo data
INSERT INTO tenants (name, slug, settings) 
VALUES ('Demo Company', 'demo', '{"max_projects": 10}')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO users (username, email, hashed_password, tenant_id)
VALUES ('demo', 'demo@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFaY9T9C8xK.K0K', 1)
ON CONFLICT (username) DO NOTHING;

INSERT INTO projects (name, description, tenant_id, folder_id, status)
VALUES 
    ('MARS Analytics Platform', 'Comprehensive analytics solution for MARS operations', 1, 'demo_folder_123', 'active'),
    ('Shell Production Optimization', 'AI-driven optimization for Shell production facilities', 1, 'demo_folder_456', 'active')
ON CONFLICT DO NOTHING;
