#!/bin/bash

# LPDP University Finder - Startup Script v2.0
# Starts API server, web server, and initializes RAG system

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║       LPDP University Finder v2.0                         ║${NC}"
echo -e "${BLUE}║       Comprehensive AI-Powered Search Platform           ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and add your OPENAI_API_KEY${NC}"
        echo -e "${YELLOW}   Then run this script again${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Set defaults
PORT_WEB=${PORT_WEB:-8000}
PORT_API=${PORT_API:-8001}

echo -e "${BLUE}🔧 Configuration:${NC}"
echo -e "   Web Server: http://localhost:${PORT_WEB}"
echo -e "   API Server: http://localhost:${PORT_API}"
echo -e "   OpenAI Key: ${OPENAI_API_KEY:+✅ Configured}${OPENAI_API_KEY:-❌ Not set}"
echo ""

# Check Python dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing Python dependencies...${NC}"
    pip3 install -r backend/requirements.txt
fi

# Check if RAG system is initialized
if [ ! -d "backend/rag/chroma_db" ] || [ -z "$(ls -A backend/rag/chroma_db 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠️  RAG system not initialized${NC}"
    echo -e "${BLUE}🔄 Initializing RAG system (this may take 5-10 minutes)...${NC}"
    python3 data/scripts/init_rag.py
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ RAG initialization failed${NC}"
        echo -e "${YELLOW}   The application will still work but without AI chat features${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ RAG system already initialized${NC}"
fi

# Kill existing servers
echo -e "${BLUE}🧹 Cleaning up existing servers...${NC}"
pkill -f "python.*backend/api/server.py" 2>/dev/null || true
pkill -f "python.*-m http.server ${PORT_WEB}" 2>/dev/null || true

# Start API server
echo -e "${BLUE}🚀 Starting API server on port ${PORT_API}...${NC}"
cd backend/api
python3 server.py > ../../api_server.log 2>&1 &
API_PID=$!
cd ../..

# Wait for API server to be ready
echo -e "${BLUE}⏳ Waiting for API server...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:${PORT_API}/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API server ready${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API server failed to start${NC}"
        echo -e "${YELLOW}   Check api_server.log for errors${NC}"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
done

# Start web server
echo -e "${BLUE}🌐 Starting web server on port ${PORT_WEB}...${NC}"
cd frontend
python3 -m http.server ${PORT_WEB} > ../web_server.log 2>&1 &
WEB_PID=$!
cd ..

# Wait for web server
sleep 2

# Check if both servers are running
if ps -p $API_PID > /dev/null && ps -p $WEB_PID > /dev/null; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║  ✅ LPDP University Finder is running!                   ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}🌐 Access the application:${NC}"
    echo -e "   ${GREEN}→ Main App:${NC} http://localhost:${PORT_WEB}"
    echo -e "   ${GREEN}→ API Docs:${NC} http://localhost:${PORT_API}"
    echo ""
    echo -e "${BLUE}📖 Features:${NC}"
    echo -e "   ${GREEN}→${NC} Search 28,000+ universities"
    echo -e "   ${GREEN}→${NC} Ask AI about LPDP (RAG-powered)"
    echo -e "   ${GREEN}→${NC} Resume analysis with AI"
    echo ""
    echo -e "${BLUE}📝 Process IDs:${NC}"
    echo -e "   API Server: ${API_PID}"
    echo -e "   Web Server: ${WEB_PID}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
    echo ""
    
    # Save PIDs for cleanup
    echo $API_PID > .api_server.pid
    echo $WEB_PID > .web_server.pid
    
    # Wait for Ctrl+C
    trap 'echo -e "\n${YELLOW}🛑 Stopping servers...${NC}"; kill $API_PID $WEB_PID 2>/dev/null; rm -f .api_server.pid .web_server.pid; echo -e "${GREEN}✅ Servers stopped${NC}"; exit 0' INT
    wait
else
    echo -e "${RED}❌ Failed to start servers${NC}"
    kill $API_PID $WEB_PID 2>/dev/null || true
    exit 1
fi
