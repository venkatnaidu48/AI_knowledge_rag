#!/bin/bash
# Docker deployment and testing script for RAG Application
# Usage: bash scripts/docker_deploy_test.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ragapp"
DOCKERFILE_PATH="./Dockerfile"
DOCKER_COMPOSE_FILE="./docker-compose.yml"
REGISTRY="${DOCKER_REGISTRY:-localhost}"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}RAG Application - Docker Deployment${NC}"
echo -e "${BLUE}==========================================${NC}\n"

# ============================================================================
# PHASE 1: BUILD DOCKER IMAGE
# ============================================================================

echo -e "${YELLOW}[PHASE 1] Building Docker image...${NC}"

if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo -e "${RED}❌ Dockerfile not found at $DOCKERFILE_PATH${NC}"
    exit 1
fi

docker build -t ${APP_NAME}:latest -f "$DOCKERFILE_PATH" . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Docker image built successfully: ${APP_NAME}:latest${NC}\n"

# ============================================================================
# PHASE 2: VALIDATE DOCKER COMPOSE
# ============================================================================

echo -e "${YELLOW}[PHASE 2] Validating docker-compose configuration...${NC}"

if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    exit 1
fi

docker-compose -f "$DOCKER_COMPOSE_FILE" config > /dev/null || {
    echo -e "${RED}❌ docker-compose.yml validation failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ docker-compose.yml is valid${NC}\n"

# ============================================================================
# PHASE 3: STOP AND REMOVE EXISTING CONTAINERS
# ============================================================================

echo -e "${YELLOW}[PHASE 3] Cleaning up existing containers...${NC}"

docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

echo -e "${GREEN}✓ Cleanup complete${NC}\n"

# ============================================================================
# PHASE 4: START DOCKER COMPOSE STACK
# ============================================================================

echo -e "${YELLOW}[PHASE 4] Starting Docker Compose stack...${NC}"

docker-compose -f "$DOCKER_COMPOSE_FILE" up -d || {
    echo -e "${RED}❌ Docker Compose startup failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Docker Compose stack started${NC}\n"

# ============================================================================
# PHASE 5: WAIT FOR SERVICES TO BE READY
# ============================================================================

echo -e "${YELLOW}[PHASE 5] Waiting for services to be ready...${NC}"

# Function to wait for service
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=0

    echo "  Waiting for $service..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}  ✓ $service is ready${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}  ✗ $service startup timeout${NC}"
    return 1
}

# Wait for PostgreSQL
wait_for_service "PostgreSQL" "http://localhost:5432" || {
    echo -e "${YELLOW}  Note: PostgreSQL may not respond to HTTP, checking container status...${NC}"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep postgres || exit 1
}

# Wait for Redis
wait_for_service "Redis" "http://localhost:6379" || {
    echo -e "${YELLOW}  Note: Redis may not respond to HTTP, checking container status...${NC}"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep redis || exit 1
}

# Wait for main application
wait_for_service "RAG API" "http://localhost:8000/api/health" || exit 1

echo -e "${GREEN}✓ All services are ready${NC}\n"

# ============================================================================
# PHASE 6: TEST APPLICATION ENDPOINTS
# ============================================================================

echo -e "${YELLOW}[PHASE 6] Testing application endpoints...${NC}"

# Test health endpoint
echo "  Testing /api/health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}  ✓ Health check passed (HTTP $HTTP_CODE)${NC}"
    echo "    Response: $BODY"
else
    echo -e "${RED}  ✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

# Test the Q&A endpoint (optional)
echo "  Testing /api/generate endpoint..."
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/generate \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the company?"}' \
    -w "\nHTTP_%{http_code}")

HTTP_CODE=$(echo "$QUERY_RESPONSE" | grep -oP '(?<=HTTP_)\d+' || echo "000")

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "401" ];then
    echo -e "${GREEN}  ✓ Query endpoint responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}  ⚠ Query endpoint returned HTTP $HTTP_CODE (may need authentication)${NC}"
fi

echo -e "${GREEN}✓ Endpoint tests complete${NC}\n"

# ============================================================================
# PHASE 7: DISPLAY DOCKER COMPOSE STATUS
# ============================================================================

echo -e "${YELLOW}[PHASE 7] Docker Compose stack status:${NC}"
docker-compose -f "$DOCKER_COMPOSE_FILE" ps

echo -e "\n"

# ============================================================================
# PHASE 8: LOG SUMMARY
# ============================================================================

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✓ Docker deployment completed successfully!${NC}"
echo -e "${GREEN}==========================================${NC}\n"

echo -e "${BLUE}Available Endpoints:${NC}"
echo "  API:        http://localhost:8000"
echo "  Health:     http://localhost:8000/api/health"
echo "  Docs:       http://localhost:8000/docs"
echo "  Prometheus: http://localhost:9090"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:       docker-compose -f $DOCKER_COMPOSE_FILE logs -f app"
echo "  Stop stack:      docker-compose -f $DOCKER_COMPOSE_FILE down"
echo "  Clean volumes:   docker-compose -f $DOCKER_COMPOSE_FILE down -v"
echo "  Restart app:     docker-compose -f $DOCKER_COMPOSE_FILE restart app"
echo ""

echo -e "${BLUE}To enable monitoring stack:${NC}"
echo "  docker-compose -f $DOCKER_COMPOSE_FILE --profile monitoring up -d"
echo ""

echo -e "${BLUE}To test Q&A system:${NC}"
echo "  curl -X POST http://localhost:8000/api/generate \\\"
echo "    -H 'Content-Type: application/json' \\\"
echo "    -d '{\"query\": \"What is the company?\"}'"
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Check logs: docker-compose logs -f app"
echo "  2. Access API docs: http://localhost:8000/docs"
echo "  3. Create .env file from .env.example"
echo "  4. Update authentication credentials"
echo "  5. Enable monitoring for production"
