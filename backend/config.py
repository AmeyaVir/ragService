#!/usr/bin/env python3
import os
import base64
import json
from functools import lru_cache
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv
import sys # Added sys import for path checks if necessary

# --- CRITICAL FIX: EXPLICIT ABSOLUTE PATH LOADING ---
# Paste the absolute path to your project root here, followed by '/.env'
# Example: /home/ameyaumesh/rag-folder/code_repo_clean_exploded/.env
ABSOLUTE_ENV_PATH = "/home/ameyaumesh/rag-folder/code_repo_clean_exploded/backend/.env" 

if not os.path.exists(ABSOLUTE_ENV_PATH):
    print(f"FATAL ERROR: .env file not found at: {ABSOLUTE_ENV_PATH}")
    sys.exit(1) # Exit if the .env file is not found

load_dotenv(ABSOLUTE_ENV_PATH)

class Settings(BaseSettings):
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API Keys
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    
    # --- NEW: Google OAuth Settings for User-Specific Drive Access ---
    GOOGLE_OAUTH_CLIENT_ID: str = Field(..., env="GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: str = Field(..., env="GOOGLE_OAUTH_CLIENT_SECRET")
    # Drive Readonly Scope is sufficient for RAG synchronization
    GOOGLE_OAUTH_SCOPES: str = Field(default="https://www.googleapis.com/auth/drive.readonly", env="GOOGLE_OAUTH_SCOPES")
    # This MUST match the URL registered in Google Cloud Console
    GOOGLE_OAUTH_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/google/callback", env="GOOGLE_OAUTH_REDIRECT_URI")

    # Database URLs
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    qdrant_url: str = Field(..., env="QDRANT_URL")
    neo4j_url: str = Field(..., env="NEO4J_URL")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    class Config:
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton instance of the settings."""
    return Settings()
