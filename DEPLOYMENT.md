# Deployment Guide - Government Services Assistant

Complete guide for deploying the Government Services Assistant to production.

## Prerequisites

- AWS Account with appropriate permissions
- Domain name with SSL certificate
- Google AI API key
- DigiLocker OAuth credentials
- Docker and Docker Compose

## Infrastructure Setup

### 1. AWS Services Configuration

#### S3 Bucket for Document Storage
```bash
aws s3 mb s3://gov-services-documents-prod --region ap-south-1
aws s3api put-bucket-encryption \
  --bucket gov-services-documents-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

#### RDS PostgreSQL Database
```bash
aws rds create-db-instance \
  --db-instance-identifier gov-services-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username admin \
  --master-user-password <secure-password> \
  --allocated-storage 20 \
  --vpc-security-group-ids <security-group-id> \
  --db-subnet-group-name <subnet-group> \
  --backup-retention-period 7 \
  --storage-encrypted
```

#### ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id gov-services-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --security-group-ids <security-group-id>
```

### 2. Environment Configuration

Create production environment files:

**backend/.env.production**
```env
# Database
DATABASE_URL=postgresql://admin:<password>@<rds-endpoint>:5432/govservices

# Redis
REDIS_URL=redis://<elasticache-endpoint>:6379/0

# AWS
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>
S3_BUCKET_NAME=gov-services-documents-prod

# Google AI
GOOGLE_API_KEY=<google-api-key>

# Security
SECRET_KEY=<generate-strong-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# DigiLocker
DIGILOCKER_CLIENT_ID=<client-id>
DIGILOCKER_CLIENT_SECRET=<client-secret>
DIGILOCKER_REDIRECT_URI=https://yourdomain.com/api/v1/digilocker/callback

# CORS
CORS_ORIGINS=https://yourdomain.com

# Document Storage
MAX_DOCUMENT_SIZE_MB=10
MAX_STORAGE_PER_USER_MB=100
```

**frontend/.env.production**
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### 3. Docker Production Build

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file:
      - backend/.env.production
    ports:
      - "8000:8000"
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    env_file:
      - frontend/.env.production
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: always
```

### 4. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # API requests
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Deployment Steps

### 1. Build and Push Docker Images

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Tag images
docker tag gov-services-backend:latest <registry>/gov-services-backend:latest
docker tag gov-services-frontend:latest <registry>/gov-services-frontend:latest

# Push to registry
docker push <registry>/gov-services-backend:latest
docker push <registry>/gov-services-frontend:latest
```

### 2. Database Migration

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml run backend alembic upgrade head

# Seed initial data
docker-compose -f docker-compose.prod.yml run backend python -m app.scripts.seed_data
```

### 3. Start Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment

```bash
# Check service health
curl https://yourdomain.com/api/v1/health

# Check frontend
curl https://yourdomain.com

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Monitoring

### CloudWatch Setup

```bash
# Create log group
aws logs create-log-group --log-group-name /gov-services/backend
aws logs create-log-group --log-group-name /gov-services/frontend

# Create alarms
aws cloudwatch put-metric-alarm \
  --alarm-name gov-services-high-error-rate \
  --alarm-description "Alert when error rate is high" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

### Application Monitoring

Add to backend:
```python
# app/core/monitoring.py
import logging
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
```

## Backup and Recovery

### Database Backup

```bash
# Automated daily backups
aws rds modify-db-instance \
  --db-instance-identifier gov-services-db \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00"

# Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier gov-services-db \
  --db-snapshot-identifier gov-services-backup-$(date +%Y%m%d)
```

### S3 Backup

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket gov-services-documents-prod \
  --versioning-configuration Status=Enabled

# Enable lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket gov-services-documents-prod \
  --lifecycle-configuration file://lifecycle.json
```

## Security Hardening

### 1. Network Security

- Configure VPC with private subnets for database and Redis
- Use security groups to restrict access
- Enable AWS WAF for API protection
- Configure rate limiting

### 2. Application Security

- Rotate SECRET_KEY regularly
- Use AWS Secrets Manager for sensitive credentials
- Enable HTTPS only
- Implement rate limiting on API endpoints
- Add request validation and sanitization

### 3. Data Security

- Enable encryption at rest for all data stores
- Use encrypted connections (SSL/TLS)
- Implement data retention policies
- Regular security audits

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### Load Balancing

Use AWS Application Load Balancer:

```bash
aws elbv2 create-load-balancer \
  --name gov-services-alb \
  --subnets <subnet-ids> \
  --security-groups <security-group-id>
```

## Maintenance

### Regular Tasks

- **Daily**: Check error logs, monitor performance
- **Weekly**: Review storage usage, check backup status
- **Monthly**: Update dependencies, security patches
- **Quarterly**: Review and update service data

### Update Procedure

```bash
# 1. Pull latest code
git pull origin main

# 2. Build new images
docker-compose -f docker-compose.prod.yml build

# 3. Run migrations
docker-compose -f docker-compose.prod.yml run backend alembic upgrade head

# 4. Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker-compose -f docker-compose.prod.yml up -d --no-deps --build frontend
```

## Rollback Procedure

```bash
# 1. Identify last working version
git log --oneline

# 2. Checkout previous version
git checkout <commit-hash>

# 3. Rebuild and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4. Rollback database if needed
docker-compose -f docker-compose.prod.yml run backend alembic downgrade -1
```

## Cost Optimization

- Use AWS Reserved Instances for predictable workloads
- Implement S3 lifecycle policies for old documents
- Use CloudFront CDN for static assets
- Enable auto-scaling based on load
- Monitor and optimize database queries

## Compliance

- Ensure GDPR compliance for data handling
- Implement data retention policies
- Regular security audits
- Maintain audit logs for sensitive operations
- Document data processing activities

## Support

For deployment issues:
- Check logs: `docker-compose -f docker-compose.prod.yml logs`
- Verify environment variables
- Check AWS service status
- Review security group rules
- Verify DNS configuration
