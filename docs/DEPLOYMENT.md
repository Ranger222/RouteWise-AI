# 🚀 RouteWise AI Deployment Guide

> **Complete guide for deploying RouteWise AI in various environments**

## 📋 Table of Contents

- [Deployment Overview](#deployment-overview)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Configuration Management](#configuration-management)
- [Monitoring & Logging](#monitoring--logging)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## 🌐 Deployment Overview

RouteWise AI supports multiple deployment strategies to fit different use cases:

- **🏠 Local Development**: Quick setup for development and testing
- **🐳 Docker**: Containerized deployment for consistency
- **☁️ Cloud**: Scalable deployment on AWS, GCP, or Azure
- **🔧 Self-Hosted**: On-premises deployment with full control

### Architecture Components

```mermaid
graph TB
    subgraph "Frontend Layer"
        Web[Next.js Web App]
        Mobile[Mobile App]
    end
    
    subgraph "API Layer"
        Gateway[API Gateway]
        LB[Load Balancer]
    end
    
    subgraph "Application Layer"
        API[RouteWise API]
        Agents[MCP Agents]
        Workers[Background Workers]
    end
    
    subgraph "Data Layer"
        DB[(SQLite/PostgreSQL)]
        Cache[Redis Cache]
        Files[File Storage]
    end
    
    subgraph "External Services"
        Mistral[Mistral AI]
        Gemini[Google Gemini]
        Search[Search APIs]
    end
    
    Web --> Gateway
    Mobile --> Gateway
    Gateway --> LB
    LB --> API
    API --> Agents
    API --> Workers
    Agents --> DB
    Agents --> Cache
    Workers --> Files
    Agents --> Mistral
    Agents --> Gemini
    Agents --> Search
```

## 📋 Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 10 GB | 50+ GB SSD |
| **Network** | 10 Mbps | 100+ Mbps |

### Software Dependencies

- **Python**: 3.9+ (3.11+ recommended)
- **Node.js**: 18+ (20+ recommended)
- **npm/yarn**: Latest version
- **Git**: For version control
- **Docker**: 20.10+ (optional)

### API Keys Required

```bash
# Essential APIs
MISTRAL_API_KEY=your_mistral_key
GEMINI_API_KEY=your_gemini_key

# Optional but recommended
TAVILY_API_KEY=your_tavily_key

# For production monitoring
SENTRY_DSN=your_sentry_dsn
```

## 🏠 Local Development

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/routewise-ai.git
cd routewise-ai

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Set up web interface
cd web
npm install
cd ..

# 5. Start development servers
# Terminal 1: Backend
python -m src.main --mode api --port 8000

# Terminal 2: Frontend
cd web && npm run dev
```

### Development Environment Variables

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=localhost
API_PORT=8000
WEB_PORT=3000

# Database
DATABASE_URL=sqlite:///src/data/memory.db

# Cache
CACHE_DIR=src/data/cache
CACHE_TTL=3600

# External APIs
MISTRAL_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# Search Configuration
SEARCH_PROVIDER=hybrid
MAX_SEARCH_RESULTS=10
REQUEST_TIMEOUT=20
```

### Development Scripts

```json
{
  "scripts": {
    "dev:api": "python -m src.main --mode api --port 8000",
    "dev:web": "cd web && npm run dev",
    "dev:cli": "python -m src.main --mode cli",
    "test": "pytest tests/",
    "lint": "flake8 src/ && cd web && npm run lint",
    "format": "black src/ && cd web && npm run format"
  }
}
```

## 🏭 Production Deployment

### Production Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/HAProxy]
    end
    
    subgraph "Application Servers"
        API1[RouteWise API #1]
        API2[RouteWise API #2]
        API3[RouteWise API #3]
    end
    
    subgraph "Worker Nodes"
        W1[Agent Worker #1]
        W2[Agent Worker #2]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        Redis[(Redis Cluster)]
        S3[(S3 Storage)]
    end
    
    subgraph "Monitoring"
        Metrics[Prometheus]
        Logs[ELK Stack]
        APM[Sentry]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> W1
    API2 --> W2
    API3 --> W1
    
    API1 --> DB
    API2 --> DB
    API3 --> DB
    
    W1 --> Redis
    W2 --> Redis
    
    API1 --> S3
    API2 --> S3
    API3 --> S3
    
    API1 --> Metrics
    API2 --> Metrics
    API3 --> Metrics
    
    API1 --> Logs
    API2 --> Logs
    API3 --> Logs
```

### Production Setup

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql redis-server

# Create application user
sudo useradd -m -s /bin/bash routewise
sudo usermod -aG sudo routewise
```

#### 2. Application Deployment

```bash
# Switch to application user
sudo su - routewise

# Clone and setup application
git clone https://github.com/your-org/routewise-ai.git
cd routewise-ai

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn supervisor

# Setup configuration
cp .env.example .env.production
# Edit .env.production with production values
```

#### 3. Database Setup

```bash
# PostgreSQL setup
sudo -u postgres createuser routewise
sudo -u postgres createdb routewise_prod -O routewise
sudo -u postgres psql -c "ALTER USER routewise PASSWORD 'secure_password';"

# Run migrations (if applicable)
python -m src.database.migrate
```

#### 4. Web Server Configuration

```nginx
# /etc/nginx/sites-available/routewise
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /home/routewise/routewise-ai/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Frontend (if serving from same domain)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 5. Process Management

```ini
# /etc/supervisor/conf.d/routewise-api.conf
[program:routewise-api]
command=/home/routewise/routewise-ai/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 src.main:app
directory=/home/routewise/routewise-ai
user=routewise
autostart=true
autorestart=true
stdout_logfile=/var/log/routewise/api.log
stderr_logfile=/var/log/routewise/api.error.log
environment=PATH="/home/routewise/routewise-ai/venv/bin"

[program:routewise-workers]
command=/home/routewise/routewise-ai/venv/bin/python -m src.workers.main
directory=/home/routewise/routewise-ai
user=routewise
autostart=true
autorestart=true
numprocs=2
process_name=%(program_name)s_%(process_num)02d
stdout_logfile=/var/log/routewise/worker.log
stderr_logfile=/var/log/routewise/worker.error.log
```

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env.docker .env

# Create non-root user
RUN useradd -m -u 1000 routewise && chown -R routewise:routewise /app
USER routewise

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "-m", "src.main", "--mode", "api", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://routewise:password@db:5432/routewise
      - REDIS_URL=redis://redis:6379/0
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api
    restart: unless-stopped
    
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=routewise
      - POSTGRES_USER=routewise
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - api
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Docker Deployment Commands

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Scale API instances
docker-compose up -d --scale api=3

# Update application
docker-compose pull
docker-compose up -d

# Backup database
docker-compose exec db pg_dump -U routewise routewise > backup.sql

# Restore database
docker-compose exec -T db psql -U routewise routewise < backup.sql
```

## ☁️ Cloud Deployment

### AWS Deployment

#### ECS with Fargate

```yaml
# aws-task-definition.json
{
  "family": "routewise-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "routewise-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/routewise:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/routewise"
        }
      ],
      "secrets": [
        {
          "name": "MISTRAL_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:routewise/mistral"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/routewise",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Terraform Configuration

```hcl
# main.tf
provider "aws" {
  region = var.aws_region
}

# VPC and Networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "routewise-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
}

# RDS Database
resource "aws_db_instance" "routewise" {
  identifier = "routewise-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  
  db_name  = "routewise"
  username = "routewise"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.routewise.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
}

# ECS Cluster
resource "aws_ecs_cluster" "routewise" {
  name = "routewise"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "routewise" {
  name               = "routewise-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
}
```

### Google Cloud Platform

#### Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/routewise:$COMMIT_SHA', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/routewise:$COMMIT_SHA']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'run'
    - 'deploy'
    - 'routewise-api'
    - '--image'
    - 'gcr.io/$PROJECT_ID/routewise:$COMMIT_SHA'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
```

### Azure Deployment

#### Container Instances

```yaml
# azure-container-group.yaml
apiVersion: 2019-12-01
location: eastus
name: routewise-container-group
properties:
  containers:
  - name: routewise-api
    properties:
      image: your-registry.azurecr.io/routewise:latest
      resources:
        requests:
          cpu: 1
          memoryInGb: 2
      ports:
      - port: 8000
      environmentVariables:
      - name: DATABASE_URL
        secureValue: postgresql://user:pass@server:5432/routewise
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8000
```

## ⚙️ Configuration Management

### Environment-Specific Configurations

```python
# src/config/settings.py
from pydantic import BaseSettings
from typing import Optional, Literal

class Settings(BaseSettings):
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    
    # API Configuration
    api_host: str = "localhost"
    api_port: int = 8000
    api_workers: int = 4
    
    # Database
    database_url: str = "sqlite:///data/memory.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Cache
    redis_url: Optional[str] = None
    cache_ttl: int = 3600
    
    # External APIs
    mistral_api_key: str
    gemini_api_key: str
    tavily_api_key: Optional[str] = None
    
    # Search Configuration
    search_provider: Literal["duckduckgo", "tavily", "hybrid"] = "hybrid"
    max_search_results: int = 10
    request_timeout: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Security
    secret_key: str
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    metrics_enabled: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Load settings based on environment
def get_settings() -> Settings:
    return Settings()
```

### Configuration Validation

```python
# src/config/validator.py
import sys
from .settings import get_settings

def validate_configuration():
    """Validate configuration before starting the application"""
    settings = get_settings()
    errors = []
    
    # Required API keys
    if not settings.mistral_api_key:
        errors.append("MISTRAL_API_KEY is required")
    
    if not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is required")
    
    # Database validation
    if settings.environment == "production" and "sqlite" in settings.database_url:
        errors.append("SQLite is not recommended for production")
    
    # Security validation
    if settings.environment == "production":
        if settings.debug:
            errors.append("Debug mode should be disabled in production")
        
        if not settings.secret_key or len(settings.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters in production")
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("Configuration validation passed")
```

## 📊 Monitoring & Logging

### Application Metrics

```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# Metrics definitions
REQUEST_COUNT = Counter('routewise_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('routewise_request_duration_seconds', 'Request duration')
ACTIVE_SESSIONS = Gauge('routewise_active_sessions', 'Active user sessions')
AGENT_CALLS = Counter('routewise_agent_calls_total', 'Agent calls', ['agent', 'status'])
AGENT_DURATION = Histogram('routewise_agent_duration_seconds', 'Agent processing time', ['agent'])

def track_request_metrics(func):
    """Decorator to track request metrics"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            REQUEST_COUNT.labels(method='POST', endpoint='/api/plan', status='success').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/api/plan', status='error').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    
    return wrapper

def start_metrics_server(port=9090):
    """Start Prometheus metrics server"""
    start_http_server(port)
    print(f"Metrics server started on port {port}")
```

### Structured Logging

```python
# src/monitoring/logging.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        
        if hasattr(record, 'agent'):
            log_entry['agent'] = record.agent
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging(level: str = "INFO", format_type: str = "json"):
    """Setup application logging"""
    
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Configure root logger
    logging.root.setLevel(level)
    logging.root.addHandler(handler)
    
    # Configure specific loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
```

### Health Checks

```python
# src/monitoring/health.py
from typing import Dict, Any
import asyncio
import time
from ..agents import SearchMCPServer, RealityMinerMCPServer

class HealthChecker:
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'search_agent': self._check_search_agent,
            'reality_miner': self._check_reality_miner,
            'external_apis': self._check_external_apis
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                results[check_name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'duration': duration,
                    'details': result if isinstance(result, dict) else {}
                }
                
                if not result:
                    overall_status = 'unhealthy'
                    
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'timestamp': time.time(),
            'checks': results
        }
    
    async def _check_database(self) -> bool:
        """Check database connectivity"""
        # Implement database health check
        return True
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity"""
        # Implement Redis health check
        return True
    
    async def _check_search_agent(self) -> bool:
        """Check search agent health"""
        # Implement agent health check
        return True
```

## 🔒 Security Considerations

### Security Checklist

- [ ] **API Keys**: Store in environment variables or secret management
- [ ] **HTTPS**: Enable SSL/TLS in production
- [ ] **CORS**: Configure appropriate CORS policies
- [ ] **Rate Limiting**: Implement request rate limiting
- [ ] **Input Validation**: Validate all user inputs
- [ ] **Error Handling**: Don't expose sensitive information in errors
- [ ] **Logging**: Don't log sensitive data
- [ ] **Dependencies**: Keep dependencies updated
- [ ] **Secrets**: Use secret management services
- [ ] **Network**: Restrict network access where possible

### Security Configuration

```python
# src/security/middleware.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
from collections import defaultdict

class RateLimitMiddleware:
    def __init__(self, calls: int = 100, period: int = 60):
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
    
    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if now - req_time < self.period
        ]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Record this request
        self.clients[client_ip].append(now)
        
        response = await call_next(request)
        return response

def setup_security(app: FastAPI, settings):
    """Setup security middleware"""
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Trusted hosts
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. API Key Errors

```bash
# Check environment variables
echo $MISTRAL_API_KEY
echo $GEMINI_API_KEY

# Verify API key validity
curl -H "Authorization: Bearer $MISTRAL_API_KEY" https://api.mistral.ai/v1/models
```

#### 2. Database Connection Issues

```python
# Test database connection
from sqlalchemy import create_engine
from src.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")
```

#### 3. Agent Communication Failures

```bash
# Check agent logs
docker-compose logs -f api | grep "agent"

# Test individual agent
python -c "from src.agents.search_agent import SearchMCPServer; print('Search agent OK')"
```

#### 4. Memory Issues

```bash
# Monitor memory usage
docker stats

# Check for memory leaks
python -m memory_profiler src/main.py
```

### Performance Tuning

#### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_sessions_created_at ON conversations(created_at);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_trip_context_destinations ON trip_context USING GIN(destinations);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM conversations WHERE created_at > NOW() - INTERVAL '1 day';
```

#### Cache Optimization

```python
# Implement cache warming
async def warm_cache():
    """Pre-populate cache with common queries"""
    common_queries = [
        "Tokyo travel guide",
        "Paris attractions",
        "London food scene"
    ]
    
    for query in common_queries:
        await search_agent.search(query)
```

### Monitoring Commands

```bash
# Check application status
curl http://localhost:8000/health

# Monitor logs in real-time
tail -f /var/log/routewise/api.log | jq .

# Check resource usage
htop
iotop
netstat -tulpn

# Database monitoring
psql -h localhost -U routewise -d routewise_prod -c "SELECT * FROM pg_stat_activity;"

# Redis monitoring
redis-cli info memory
redis-cli monitor
```

---

<div align="center">
  <strong>Deploy with confidence, scale with intelligence</strong>
  <br>
  <sub>Production-ready deployment for RouteWise AI</sub>
</div>

## ⏱️ Time & Performance Environment Variables

The planning orchestration supports time-aware behavior controlled by environment variables:

- FAST_MODE ("1"/"true"): Enables a development-fast path that caps initial search queries, trims mined documents, skips deep refinement, and limits insights for faster iteration.
  - Recommended: Enable in local development to reduce turnaround time.
  - Production: Disable unless you explicitly want faster-but-slimmer outputs.

- PLANNER_TIME_BUDGET (seconds): Total time budget for the planning workflow.
  - Default: ~90s (clamped internally to ~45–100s).
  - Behavior: The system performs remaining-time checks to gate deeper steps, may fall back to a quick inline itinerary, skip specialized submodules (flights/visa/budget/checklist), and avoid saving artifacts if nearly out of time.
  - Production: Tune based on throughput and latency SLOs. Longer budgets yield more thorough plans at the cost of higher latency.

Notes:
- The Next.js dev API route sets FAST_MODE=1 by default for a snappier DX.
- No API request parameter is required; these are server-side controls.