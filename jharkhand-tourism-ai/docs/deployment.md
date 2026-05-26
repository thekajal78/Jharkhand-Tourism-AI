# Deployment Guide - Jharkhand Tourism AI Platform

This guide covers deployment of the Jharkhand Tourism AI Platform using Docker and Docker Compose.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM (recommended for AI/ML components)
- 20GB+ disk space

## Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/jharkhand-tourism-ai.git
   cd jharkhand-tourism-ai
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - AI Service: http://localhost:8001
   - Admin Dashboard: http://localhost:3001

## Service Architecture

### Core Services
- **Frontend**: React.js web application (Port 3000)
- **Backend**: FastAPI server (Port 8000)
- **AI Service**: ML/CLIP processing service (Port 8001)

### Supporting Services
- **PostgreSQL**: Primary database (Port 5432)
- **Redis**: Caching and session storage (Port 6379)
- **Elasticsearch**: Search functionality (Port 9200)
- **Nginx**: Reverse proxy and static file serving (Port 80)

### Monitoring Stack
- **Prometheus**: Metrics collection (Port 9090)
- **Grafana**: Visualization dashboards (Port 3001)
- **Kibana**: Log analysis (Port 5601)

## Environment Configuration

### Required Environment Variables

```bash
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://tourism_user:password@postgres:5432/jharkhand_tourism

# Security
JWT_SECRET_KEY=your_super_secret_jwt_key
OPENAI_API_KEY=your_openai_api_key

# External APIs
MAPS_API_KEY=your_google_maps_api_key
WEATHER_API_KEY=your_weather_api_key

# Application
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
```

## Production Deployment

### Docker Swarm Deployment

1. **Initialize Docker Swarm**:
   ```bash
   docker swarm init
   ```

2. **Deploy the stack**:
   ```bash
   docker stack deploy -c docker-compose.yml tourism-ai
   ```

### Kubernetes Deployment

1. **Apply Kubernetes manifests**:
   ```bash
   kubectl apply -f k8s/
   ```

2. **Check deployment status**:
   ```bash
   kubectl get pods -n tourism-ai
   ```

## SSL/TLS Configuration

### Using Let's Encrypt with Nginx

1. **Update nginx configuration**:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://frontend:3000;
       }
   }
   ```

## Scaling Configuration

### Horizontal Scaling

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
  
  ai_service:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 4G
```

## Monitoring and Logging

### Grafana Dashboard Setup

1. **Access Grafana**: http://localhost:3001
2. **Default credentials**: admin/admin123
3. **Import dashboards** from `monitoring/grafana/dashboards/`

### Log Management

- **Application logs**: Available in Docker logs
- **Centralized logging**: Elasticsearch + Kibana
- **Log rotation**: Configured automatically

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker exec postgres pg_dump -U tourism_user jharkhand_tourism > backup.sql

# Restore from backup
docker exec -i postgres psql -U tourism_user jharkhand_tourism < backup.sql
```

### Volume Backup

```bash
# Backup all volumes
docker run --rm -v tourism_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_destinations_location ON destinations(latitude, longitude);
CREATE INDEX idx_destination_images_processed ON destination_images(is_processed);
CREATE INDEX idx_reviews_rating ON destination_reviews(rating, created_at);
```

### Redis Configuration

```redis
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

## Security Considerations

### Network Security
- Use Docker networks for service isolation
- Configure firewall rules
- Enable SSL/TLS for all external connections

### Application Security
- Keep dependencies updated
- Use strong JWT secrets
- Implement rate limiting
- Enable CORS protection

### Data Security
- Encrypt sensitive data at rest
- Use secure database connections
- Regular security audits
- Backup encryption

## Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   docker-compose logs [service_name]
   ```

2. **Database connection issues**:
   ```bash
   docker exec -it postgres psql -U tourism_user -d jharkhand_tourism
   ```

3. **Memory issues with AI service**:
   - Increase Docker memory limits
   - Consider using CPU-only CLIP models

### Health Checks

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Check database connectivity
docker exec postgres pg_isready -U tourism_user
```

## Updates and Maintenance

### Rolling Updates

```bash
# Update specific service
docker-compose pull backend
docker-compose up -d --no-deps backend

# Update all services
docker-compose pull
docker-compose up -d
```

### Maintenance Tasks

- Regular database cleanup
- Log rotation
- Security updates
- Performance monitoring

## Support

For deployment support:
- Check the logs: `docker-compose logs`
- Review configuration: `docker-compose config`
- Contact: support@jharkhand-tourism-ai.com
- Documentation: [docs/](../docs/)

---

**Note**: This is a production-ready deployment guide. Ensure all security measures are properly configured before deploying to production.