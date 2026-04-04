#!/bin/bash
# RAG Application Startup Script for Unix/Linux/macOS

set -e

echo "========================================="
echo "RAG Application - Startup Script"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Check Python version
echo -e "${BLUE}[1/5] Checking Python version...${NC}"
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# 2. Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[2/5] Creating virtual environment...${NC}"
    python -m venv venv
else
    echo -e "${BLUE}[2/5] Virtual environment exists${NC}"
fi

# 3. Activate virtual environment
echo -e "${BLUE}[3/5] Activating virtual environment...${NC}"
source venv/bin/activate

# 4. Install dependencies
echo -e "${BLUE}[4/5] Installing dependencies...${NC}"
pip install -r requirements.txt

# 5. Create necessary directories
echo -e "${BLUE}[5/5] Creating data directories...${NC}"
mkdir -p data/uploads logs backups monitoring

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "To start the development server:"
echo "  python -m uvicorn src.main:app --reload"
echo ""
echo "To access the API:"
echo "  http://localhost:8000/docs"
