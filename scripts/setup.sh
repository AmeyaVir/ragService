#!/bin/bash
set -e

echo "Setting up Analytics RAG Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and credentials."
    echo "Required:"
    echo "  - GEMINI_API_KEY: Your Google Gemini API key"
    echo "  - GOOGLE_OAUTH_CLIENT_ID: Your Google OAuth Client ID"
    echo "  - GOOGLE_OAUTH_CLIENT_SECRET: Your Google OAuth Client Secret"
    echo ""
    read -p "Press enter to continue after updating .env file..."
fi

# Start services
echo "Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check service health
echo "Checking service health..."
curl -f http://localhost:8000/health || echo "Backend not ready yet"
curl -f http://localhost:3000 || echo "Frontend not ready yet"
curl -f http://localhost:5173 || echo "Microsite not ready yet"

echo ""
echo "Setup complete! Services are starting up."
echo ""
echo "Access the application:"
echo "  - Chat Interface: http://localhost:3000"
echo "  - API Documentation: http://localhost:8000/docs" 
echo "  - Microsite Preview: http://localhost:5173"
echo ""
echo "Login with demo credentials: username 'demo', password 'demo'"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
