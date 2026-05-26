# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project: Jharkhand Tourism AI Platform

## Overview

This is a comprehensive AI-powered tourism platform for Jharkhand state featuring:
- **CLIP-based visual search** for destination discovery via images
- **ML recommendation systems** with collaborative and content-based filtering
- **Multilingual chatbot** with NLP capabilities
- **Real-time analytics** and interactive maps
- **Microservices architecture** with Docker orchestration

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + Redis + Celery
- **Frontend**: React 18 + TypeScript + Material-UI + React Query + Redux Toolkit
- **AI/ML**: PyTorch + OpenAI CLIP + Transformers + scikit-learn + FAISS
- **Infrastructure**: Docker Compose + Nginx + Elasticsearch + Prometheus + Grafana

## Environment Notes

- Commands shown work on Windows PowerShell, macOS, and Linux
- On Windows, use `python` (not `python3`) and `npm` (not yarn/pnpm) unless specified
- Full-stack development uses docker-compose for service orchestration
- AI/ML models default to CPU-friendly versions but support GPU acceleration

## Common Commands

### Full Stack Operations

```bash
# Start complete platform (all services)
docker-compose up -d

# Stop all services
docker-compose down

# View logs (follow mode)
docker-compose logs -f backend
docker-compose logs -f ai_service

# Rebuild and restart specific service
docker-compose up -d --build backend
docker-compose up -d --build ai_service

# Check service status
docker-compose ps

# Scale services
docker-compose up -d --scale backend=3
```

### Backend Development (FastAPI)

**Setup and Run:**
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Development server (with hot reload)
python -m uvicorn main:app --reload --port 8000

# With environment variables (Windows)
$env:ENVIRONMENT="development"; $env:CORS_ORIGINS="http://localhost:3000"; python -m uvicorn main:app --reload --port 8000

# With environment variables (Unix)
ENVIRONMENT=development CORS_ORIGINS=http://localhost:3000 python -m uvicorn main:app --reload --port 8000
```

**Testing:**
```bash
# Run all tests
pytest backend/tests -v

# Run specific test file
pytest backend/tests/test_destinations.py -v

# Run single test method
pytest backend/tests/test_destinations.py::TestDestinations::test_create_destination -v

# Coverage report
pytest backend/tests --cov=backend --cov-report=term-missing --cov-report=html

# Test specific router
pytest backend/tests -k "test_auth" -v
```

**Key Backend Architecture:**
- **Routers**: Domain-organized under `app/routers/` (auth, destinations, images, chatbot, etc.)
- **Services**: AI/CLIP services initialized in lifespan manager (`main.py`)
- **Database**: SQLAlchemy async with Alembic migrations
- **Auth**: JWT-based with role-based access control

### Frontend Development (React + TypeScript)

**Setup and Run:**
```bash
# Install dependencies
npm install --prefix frontend

# Development server (port 3000)
npm start --prefix frontend

# Production build
npm run build --prefix frontend

# Serve production build locally
npx serve -s frontend/build
```

**Development Tools:**
```bash
# Linting
npm run lint --prefix frontend
npm run lint:fix --prefix frontend

# Code formatting
npm run format --prefix frontend

# TypeScript checking
npm run type-check --prefix frontend

# Run all checks together
npm run lint --prefix frontend && npm run type-check --prefix frontend
```

**Testing:**
```bash
# Interactive test runner
npm test --prefix frontend

# Run tests once
npm test --prefix frontend -- --watchAll=false

# Test specific component
npm test --prefix frontend -- src/components/Navigation.test.tsx

# Test coverage
npm test --prefix frontend -- --coverage --watchAll=false
```

**Key Frontend Architecture:**
- **State Management**: Redux Toolkit + React Query for server state
- **UI Framework**: Material-UI with custom theme
- **Maps**: React Leaflet for interactive mapping
- **Routing**: React Router with lazy loading
- **Forms**: React Hook Form for validation

### AI/ML Service Development

**Setup and Run:**
```bash
# Install dependencies (CPU-optimized by default)
pip install -r ai_ml/requirements.txt

# For GPU support, install CUDA-enabled PyTorch
pip install torch==2.1.1+cu118 torchvision==0.16.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Run AI service (FastAPI on port 8001)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Core AI Services:**
```bash
# Test CLIP image encoding
cd ai_ml && python -c "from services.clip_service import CLIPService; import asyncio; asyncio.run(CLIPService().initialize())"

# Test recommendation service
cd ai_ml && python services/recommendation_service.py

# Test chatbot service
cd ai_ml && python services/chatbot_service.py
```

**Testing:**
```bash
# Run all AI/ML tests
pytest ai_ml/tests -v

# Test CLIP functionality
pytest ai_ml/tests/test_clip.py::test_image_encoding -v
pytest ai_ml/tests/test_clip.py::test_text_search -v

# Test recommendation algorithms
pytest ai_ml/tests/test_recommendations.py -v

# Performance testing
pytest ai_ml/tests -m "performance" --tb=short
```

**Key AI/ML Components:**
- **CLIP Service**: OpenAI CLIP (ViT-B/32) for visual-text matching, FAISS for similarity search
- **Recommendations**: Collaborative filtering, content-based filtering, hybrid models
- **Chatbot**: Transformers + spaCy for NLP, multilingual support
- **Vector Search**: Redis caching + FAISS indexing for real-time queries

### Infrastructure and Monitoring

**Database Operations:**
```bash
# Access PostgreSQL shell
docker exec -it jharkhand_tourism_db psql -U tourism_user -d jharkhand_tourism

# Database backup
docker exec jharkhand_tourism_db pg_dump -U tourism_user jharkhand_tourism > backup.sql

# Database restore
docker exec -i jharkhand_tourism_db psql -U tourism_user jharkhand_tourism < backup.sql

# Run migrations (if using Alembic)
cd backend && alembic upgrade head
```

**Health Checks and Monitoring:**
```bash
# Service health checks
curl http://localhost:8000/health    # Backend API
curl http://localhost:8001/health    # AI Service
curl http://localhost:3000          # Frontend
curl http://localhost:9200          # Elasticsearch

# Monitoring dashboards
# - Grafana: http://localhost:3001 (admin/admin123)
# - Prometheus: http://localhost:9090
# - Kibana: http://localhost:5601
# - API Docs: http://localhost:8000/docs
```

**Redis Operations:**
```bash
# Access Redis CLI
docker exec -it jharkhand_tourism_redis redis-cli

# Monitor Redis operations
docker exec jharkhand_tourism_redis redis-cli MONITOR

# Check Redis memory usage
docker exec jharkhand_tourism_redis redis-cli INFO memory
```

## High-Level Architecture

### Core Services

**Frontend (./frontend)** - React 18 + TypeScript SPA
- **Tech Stack**: Material-UI, React Query, Redux Toolkit, React Router, Leaflet maps
- **Communication**: REST APIs to Backend (port 8000) and AI service (port 8001)
- **Features**: Visual search interface, interactive maps, admin dashboard, real-time chat
- **State Management**: Redux Toolkit for app state, React Query for server state caching

**Backend (./backend)** - FastAPI REST API
- **Architecture**: Domain-driven design with routers under `app/routers/`
- **Key Routers**: auth, users, destinations, bookings, recommendations, images (CLIP), chatbot, analytics, admin
- **Startup Process**:
  1. Creates database tables via SQLAlchemy metadata
  2. Initializes AIService and CLIPService (attached to `app.state`)
  3. Sets up static file serving for uploads at `/static`
  4. Configures CORS and security middleware
- **Authentication**: JWT-based with role-based access control

**AI/ML Service (./ai_ml)** - Specialized AI processing service
- **Core Models**: OpenAI CLIP (ViT-B/32), Transformers, scikit-learn
- **Key Services**:
  - `CLIPService`: Visual-text matching, image similarity search, geo-tagging
  - `RecommendationService`: Collaborative filtering, content-based recommendations
  - `ChatbotService`: Multilingual NLP with intent recognition
- **Performance**: CPU-optimized by default, GPU support available
- **Caching**: Redis for embedding cache, FAISS for vector similarity search

### Supporting Infrastructure

**Data Layer**:
- **PostgreSQL 15**: Primary database with async SQLAlchemy ORM
- **Redis 7**: Session management, caching, background task queuing
- **Elasticsearch 8**: Full-text search, log aggregation

**Monitoring Stack**:
- **Prometheus**: Metrics collection from all services
- **Grafana**: Custom dashboards for tourism analytics
- **Kibana**: Log analysis and search

**Infrastructure**:
- **Nginx**: Reverse proxy, SSL termination, static file serving
- **Docker Compose**: Service orchestration with health checks
- **Volume Management**: Persistent storage for uploads, models, logs

### Data Flow and Integration

**Frontend → Backend**:
- REST API calls to `/api/v1` endpoints
- JWT authentication for protected routes
- File uploads for image processing
- Real-time features via WebSocket (planned)

**Backend → AI Services**:
- Internal service calls via `app.state` references
- Alternative: HTTP calls to ai_service container (port 8001)
- Image processing pipeline: Upload → CLIP encoding → Vector indexing
- Recommendation pipeline: User data → ML models → Personalized results

**Data Persistence**:
- **PostgreSQL**: User data, destinations, bookings, analytics
- **Redis**: Session data, CLIP embeddings cache, background tasks
- **File System**: Uploaded images, model files (via Docker volumes)
- **Elasticsearch**: Search indexes, application logs

### Configuration and Environment

**Required Environment Variables** (see `.env.example`):
```bash
# Database
DATABASE_URL=postgresql://tourism_user:password@postgres:5432/jharkhand_tourism
POSTGRES_PASSWORD=your_secure_password

# Security
JWT_SECRET_KEY=your_super_secret_jwt_key
OPENAI_API_KEY=your_openai_api_key

# External APIs
MAPS_API_KEY=your_google_maps_api_key
WEATHER_API_KEY=your_weather_api_key

# Application
ENVIRONMENT=development|production
DEBUG=true|false
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# AI/ML
CUDA_VISIBLE_DEVICES=0  # For GPU support
CLIP_MODEL_PATH=/app/models/clip
```

**Docker Compose Configuration**:
- **Volumes**: Persistent data for PostgreSQL, Redis, Elasticsearch, Grafana
- **Networks**: Isolated `tourism_network` for service communication
- **Health Checks**: Automatic service monitoring and restart
- **Resource Limits**: AI service limited to 4GB RAM by default
- **Port Mapping**: All services exposed for development

## Development Workflows

### Local Development (No Containers)

**Prerequisites**: PostgreSQL 13+, Redis 6+, Python 3.9+, Node.js 16+

```bash
# 1. Start infrastructure services
docker-compose up -d postgres redis elasticsearch

# 2. Backend setup
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# 3. Frontend setup (new terminal)
cd frontend
npm install
npm start  # Runs on port 3000

# 4. AI service setup (new terminal)
cd ai_ml
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Full Stack Development (Containers)

```bash
# Start all services
docker-compose up -d

# Development with live reload (after changes)
docker-compose up -d --build backend frontend ai_service

# Access services
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/docs
# - AI Service: http://localhost:8001/docs
```

### Hybrid Development (Mix of local and containers)

```bash
# Infrastructure only
docker-compose up -d postgres redis elasticsearch prometheus grafana

# Run application services locally for faster development
# (Follow local development steps above)
```

## Testing Strategy

### Backend Testing
```bash
# Full test suite
pytest backend/tests -v --tb=short

# Test categories
pytest backend/tests -m "unit" -v          # Unit tests only
pytest backend/tests -m "integration" -v   # Integration tests only

# Coverage reporting
pytest backend/tests --cov=backend --cov-report=html --cov-report=term-missing

# Performance tests
pytest backend/tests -m "performance" --durations=10
```

### Frontend Testing
```bash
# Interactive test runner
npm test --prefix frontend

# CI mode (single run)
npm test --prefix frontend -- --coverage --watchAll=false

# Component testing
npm test --prefix frontend -- src/components/VisualSearch.test.tsx

# E2E tests (if configured)
npm run test:e2e --prefix frontend
```

### AI/ML Testing
```bash
# ML model tests
pytest ai_ml/tests -v --tb=line

# CLIP service tests
pytest ai_ml/tests/test_clip.py -v

# Performance benchmarks
pytest ai_ml/tests -m "benchmark" --benchmark-only

# Integration tests with live models
pytest ai_ml/tests -m "integration" --tb=short
```

## Documentation and References

### Project Documentation
- **README.md**: Feature overview, quick start guide, architecture summary
- **docs/api.md**: Complete REST API documentation with examples
- **docs/deployment.md**: Production deployment, scaling, monitoring, security
- **Interactive API Docs**: 
  - Swagger UI: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc

### Key API Endpoints
```
# Core APIs
GET  /api/v1/destinations/              # List destinations
POST /api/v1/images/visual-search       # CLIP-based image search
GET  /api/v1/recommendations/personalized  # ML recommendations
POST /api/v1/chatbot/message            # Chatbot interactions
GET  /api/v1/analytics/overview         # Platform analytics

# Admin endpoints
POST /api/v1/admin/destinations         # Create destinations
GET  /api/v1/admin/users                # User management
```

## Development Guidelines

### Code Organization
- **Backend**: Domain-driven routers under `app/routers/`, shared services in `app/services/`
- **Frontend**: Feature-based organization under `src/components/`, `src/pages/`, `src/services/`
- **AI/ML**: Service-oriented architecture under `ai_ml/services/`

### Best Practices
- **Security**: Never inline secrets in commands; always use environment variables
- **Testing**: Write tests for new features; maintain coverage above 80%
- **Performance**: Use Redis caching for expensive operations (CLIP embeddings, ML predictions)
- **Monitoring**: Add Prometheus metrics for new endpoints
- **Documentation**: Update API docs when adding new endpoints

### Service Integration
- **Backend ↔ AI Service**: Use `app.state` services for internal calls, HTTP for external
- **Database Changes**: Use Alembic migrations for schema changes
- **File Uploads**: Store in `./backend/uploads/`, serve via `/static` endpoint
- **Background Tasks**: Use Celery + Redis for async processing

### Debugging and Development
- **Logs**: Use structured logging with correlation IDs
- **Development**: Use `--reload` flags for hot reloading during development
- **Validation**: Prefer docker-compose for end-to-end testing; rebuild with `--build` after changes
- **Performance**: Monitor AI service memory usage; scale horizontally if needed
