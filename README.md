# Analytics RAG Platform

Enterprise-grade RAG system for analytics companies with multi-tenant project management and executive chat interface.

## Features

- Multi-tenant Google Drive integration (via **User-Specific OAuth**)
- Intelligent document parsing (PDF, PPTX, Excel, Word)  
- Project-aware RAG with knowledge graphs
- Executive chat interface with microsite generation
- LLM agents using Gemini API
- Docker-based deployment

## Quick Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and Google OAuth Client IDs
   ```

2. Start services:
   ```bash
   docker-compose up -d
   ```

3. Initialize database:
   ```bash
   docker-compose exec backend python scripts/init_db.py
   ```

4. Access the application:
   - Chat Interface: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - Microsite Preview: http://localhost:5173

## Development

See docs/DEPLOYMENT.md for detailed setup instructions.
