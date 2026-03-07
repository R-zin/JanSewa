# AWS Deployment Guide - Jan Sewa Government Services Assistant

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Database Configuration](#database-configuration)
5. [Application Deployment](#application-deployment)
6. [Security Configuration](#security-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Cost Optimization](#cost-optimization)
10. [Backup & Disaster Recovery](#backup--disaster-recovery)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CloudFront CDN                        │
│                    (Global Distribution)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                  Application Load Balancer                   │
│                    (Multi-AZ, SSL/TLS)                       │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
    ┌──────┴──────┐            ┌───────┴────────┐
    │   ECS/EC2   │            │   ECS/EC2      │
    │  (AZ-1a)    │            │   (AZ-1b)      │
    │  Backend    │            │   Backend      │
    └──────┬──────┘            └───────┬────────┘
           │                            │
    ┌──────┴────────────────────────────┴─────────┐
    │         RDS PostgreSQL (Multi-AZ)           │
    │         ElastiCache Redis (Multi-AZ)        │
    └─────────────────────────────────────────────┘
           │                            │
    ┌──────┴──────┐            ┌───────┴────────┐
    │  S3 Bucket  │            │  CloudWatch    │
    │ (Documents) │            │  (Monitoring)  │
    └─────────────┘            └────────────────┘
```

### AWS Services Used

1. **Compute**: ECS Fargate or EC2 Auto Scaling Group
2. **Database**: RDS PostgreSQL (Multi-AZ)
3. **Cache**: ElastiCache Redis (Multi-AZ)
4. **Storage**: S3 (documents, backups)
5. **CDN**: CloudFront (optional, for static assets)
6. **Load Balancer**: Application Load Balancer (ALB)
7. **Networking**: VPC, Subnets, Security Groups, NAT Gateway
8. **DNS**: Route 53
9. **Secrets**: AWS Secrets Manager
10. **Monitoring**: CloudWatch, CloudWatch Logs
11. **Security**: WAF, Shield, IAM
12. **CI/CD**: CodePipeline, CodeBuild, CodeDeploy

### Cost Estimate (Monthly)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| EC2/ECS | 2x t3.medium (24/7) | $60-80 |
| RDS PostgreSQL | db.t3.medium Multi-AZ | $120-150 |
| ElastiCache Redis | cache.t3.micro | $25-30 |
| ALB | Standard | $20-25 |
| S3 | 100GB storage + requests | $5-10 |
| CloudWatch | Logs + Metrics | $10-15 |
| Data Transfer | 100GB/month | $10-15 |
| **Total** | | **$250-325/month** |

---

## Prerequisites

### Required Tools
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Terraform (Infrastructure as Code)
brew install terraform

# Docker
brew install --cask docker

# kubectl (if using EKS)
brew install kubectl
```

### AWS Account Setup
1. Create AWS account at https://aws.amazon.com
2. Enable MFA on root account
3. Create IAM admin user with programmatic access
4. Configure AWS CLI:
```bash
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: ap-south-1 (Mumbai)
# Default output format: json
```

### Domain & SSL
1. Register domain (Route 53 or external registrar)
2. Request SSL certificate in AWS Certificate Manager (ACM)
3. Validate domain ownership

---

## Infrastructure Setup

### Option 1: Terraform (Recommended)

Create `terraform/main.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "jan-sewa-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name        = "jan-sewa-vpc"
    Environment = var.environment
  }
}

# Public Subnets (for ALB)
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "jan-sewa-public-1a"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "jan-sewa-public-1b"
  }
}

# Private Subnets (for ECS/EC2, RDS)
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "jan-sewa-private-1a"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"
  
  tags = {
    Name = "jan-sewa-private-1b"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "jan-sewa-igw"
  }
}

# NAT Gateway (for private subnets to access internet)
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1.id
  
  tags = {
    Name = "jan-sewa-nat"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "jan-sewa-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  
  tags = {
    Name = "jan-sewa-private-rt"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private.id
}
```

Create `terraform/variables.tf`:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "jan-sewa"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}
```

### Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

---

## Database Configuration

### RDS PostgreSQL Setup

Create `terraform/rds.tf`:

```hcl
# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "jan-sewa-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "jan-sewa-rds-sg"
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "jan-sewa-db-subnet"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  
  tags = {
    Name = "jan-sewa-db-subnet"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  identifier     = "jan-sewa-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "govservices"
  username = var.db_username
  password = var.db_password
  
  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "jan-sewa-db-final-snapshot"
  
  tags = {
    Name        = "jan-sewa-db"
    Environment = var.environment
  }
}

# Store DB credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "jan-sewa/db/credentials"
  
  tags = {
    Name = "jan-sewa-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
  })
}
```

### ElastiCache Redis Setup

Create `terraform/redis.tf`:

```hcl
# Security Group for Redis
resource "aws_security_group" "redis" {
  name        = "jan-sewa-redis-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "jan-sewa-redis-sg"
  }
}

# Redis Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "jan-sewa-redis-subnet"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "jan-sewa-redis"
  replication_group_description = "Redis cluster for Jan Sewa"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t3.micro"
  num_cache_clusters   = 2
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"
  
  tags = {
    Name        = "jan-sewa-redis"
    Environment = var.environment
  }
}
```

---

## Application Deployment

### Option A: ECS Fargate (Recommended)

Create `terraform/ecs.tf`:

```hcl
# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "jan-sewa-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "jan-sewa-cluster"
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs" {
  name        = "jan-sewa-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "jan-sewa-ecs-sg"
  }
}

# ECR Repository
resource "aws_ecr_repository" "backend" {
  name                 = "jan-sewa-backend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "AES256"
  }
  
  tags = {
    Name = "jan-sewa-backend"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "jan-sewa-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "jan-sewa-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# Policy for S3 access
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.documents.arn,
        "${aws_s3_bucket.documents.arn}/*"
      ]
    }]
  })
}

# Policy for AWS Textract access
resource "aws_iam_role_policy" "ecs_task_textract" {
  name = "textract-access"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "textract:DetectDocumentText",
        "textract:AnalyzeDocument",
        "textract:AnalyzeID",
        "textract:StartDocumentTextDetection",
        "textract:GetDocumentTextDetection",
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis"
      ]
      Resource = "*"
    }]
  })
}

# Policy for Secrets Manager access
resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.db_credentials.arn,
        aws_secretsmanager_secret.app_secrets.arn
      ]
    }]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/jan-sewa-backend"
  retention_in_days = 30
  
  tags = {
    Name = "jan-sewa-backend-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "jan-sewa-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"  # 1 vCPU
  memory                   = "2048"  # 2 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([{
    name  = "backend"
    image = "${aws_ecr_repository.backend.repository_url}:latest"
    
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    
    environment = [
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "ENVIRONMENT"
        value = var.environment
      },
      {
        name  = "S3_BUCKET_NAME"
        value = aws_s3_bucket.documents.id
      },
      {
        name  = "REDIS_URL"
        value = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0"
      }
    ]
    
    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:DATABASE_URL::"
      },
      {
        name      = "SECRET_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:SECRET_KEY::"
      },
      {
        name      = "GOOGLE_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:GOOGLE_API_KEY::"
      },
      {
        name      = "DIGILOCKER_CLIENT_ID"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:DIGILOCKER_CLIENT_ID::"
      },
      {
        name      = "DIGILOCKER_CLIENT_SECRET"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:DIGILOCKER_CLIENT_SECRET::"
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
  
  tags = {
    Name = "jan-sewa-backend"
  }
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "jan-sewa-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
  
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
  
  depends_on = [aws_lb_listener.https]
  
  tags = {
    Name = "jan-sewa-backend-service"
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  name               = "cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

### Application Load Balancer

Create `terraform/alb.tf`:

```hcl
# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "jan-sewa-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "jan-sewa-alb-sg"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "jan-sewa-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  
  enable_deletion_protection = true
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  
  tags = {
    Name = "jan-sewa-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "backend" {
  name        = "jan-sewa-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
  
  deregistration_delay = 30
  
  tags = {
    Name = "jan-sewa-backend-tg"
  }
}

# HTTP Listener (redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.acm_certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
```

### S3 Bucket for Documents

Create `terraform/s3.tf`:

```hcl
# S3 Bucket for Documents
resource "aws_s3_bucket" "documents" {
  bucket = "jan-sewa-documents-${var.environment}"
  
  tags = {
    Name        = "jan-sewa-documents"
    Environment = var.environment
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  rule {
    id     = "delete-old-versions"
    status = "Enabled"
    
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
  
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}
```

### Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

# Build image
cd backend
docker build -t jan-sewa-backend .

# Tag image
docker tag jan-sewa-backend:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/jan-sewa-backend:latest

# Push image
docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/jan-sewa-backend:latest
```

### Run Database Migrations

```bash
# Connect to ECS task
aws ecs execute-command \
  --cluster jan-sewa-cluster \
  --task <task-id> \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Inside container, run migrations
cd /app
alembic upgrade head
```

---

## Security Configuration

### Secrets Manager

Create `terraform/secrets.tf`:

```hcl
# Application Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "jan-sewa/app/secrets"
  
  tags = {
    Name = "jan-sewa-app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    SECRET_KEY                = var.secret_key
    GOOGLE_API_KEY           = var.google_api_key
    DIGILOCKER_CLIENT_ID     = var.digilocker_client_id
    DIGILOCKER_CLIENT_SECRET = var.digilocker_client_secret
  })
}
```

### WAF (Web Application Firewall)

Create `terraform/waf.tf`:

```hcl
# WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name  = "jan-sewa-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Rate limiting rule
  rule {
    name     = "rate-limit"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRule"
      sampled_requests_enabled  = true
    }
  }
  
  # AWS Managed Rules - Core Rule Set
  rule {
    name     = "aws-managed-core-rules"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedCoreRules"
      sampled_requests_enabled  = true
    }
  }
  
  # AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "aws-managed-known-bad-inputs"
    priority = 3
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedKnownBadInputs"
      sampled_requests_enabled  = true
    }
  }
  
  # SQL Injection Protection
  rule {
    name     = "aws-managed-sql-injection"
    priority = 4
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedSQLInjection"
      sampled_requests_enabled  = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "JanSewaWAF"
    sampled_requests_enabled  = true
  }
  
  tags = {
    Name = "jan-sewa-waf"
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}
```

### Security Best Practices

1. **Enable AWS Shield Standard** (free DDoS protection)
2. **Use AWS Secrets Manager** for all sensitive data
3. **Enable VPC Flow Logs** for network monitoring
4. **Use IAM roles** instead of access keys
5. **Enable MFA** for all IAM users
6. **Regular security audits** with AWS Security Hub
7. **Enable AWS GuardDuty** for threat detection
8. **Use AWS Config** for compliance monitoring

---

## Monitoring & Logging

### CloudWatch Dashboards

Create `terraform/monitoring.tf`:

```hcl
# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "jan-sewa-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average" }],
            [".", "MemoryUtilization", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Resource Utilization"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average" }],
            [".", "RequestCount", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ALB Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            [".", "DatabaseConnections", { stat = "Average" }],
            [".", "FreeStorageSpace", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "RDS Metrics"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "jan-sewa-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS CPU utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "jan-sewa-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "jan-sewa-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Too many 5xx errors from ALB"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "jan-sewa-alerts"
  
  tags = {
    Name = "jan-sewa-alerts"
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

### Application Logging

Update `backend/app/core/logging_config.py` to send logs to CloudWatch:

```python
import watchtower
import logging

def setup_cloudwatch_logging():
    """Configure CloudWatch logging"""
    logger = logging.getLogger()
    
    # Add CloudWatch handler
    cloudwatch_handler = watchtower.CloudWatchLogHandler(
        log_group='/ecs/jan-sewa-backend',
        stream_name='application',
        use_queues=True
    )
    
    logger.addHandler(cloudwatch_handler)
```

---

## CI/CD Pipeline

### CodePipeline Setup

Create `terraform/cicd.tf`:

```hcl
# S3 Bucket for Pipeline Artifacts
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket = "jan-sewa-pipeline-artifacts"
  
  tags = {
    Name = "jan-sewa-pipeline-artifacts"
  }
}

# CodeBuild Project
resource "aws_codebuild_project" "backend" {
  name          = "jan-sewa-backend-build"
  service_role  = aws_iam_role.codebuild.arn
  
  artifacts {
    type = "CODEPIPELINE"
  }
  
  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"
    
    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
    
    environment_variable {
      name  = "ECR_REPOSITORY_URI"
      value = aws_ecr_repository.backend.repository_url
    }
    
    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = aws_ecs_cluster.main.name
    }
    
    environment_variable {
      name  = "ECS_SERVICE_NAME"
      value = aws_ecs_service.backend.name
    }
  }
  
  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec.yml"
  }
  
  tags = {
    Name = "jan-sewa-backend-build"
  }
}

# CodePipeline
resource "aws_codepipeline" "backend" {
  name     = "jan-sewa-backend-pipeline"
  role_arn = aws_iam_role.codepipeline.arn
  
  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
  }
  
  stage {
    name = "Source"
    
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]
      
      configuration = {
        ConnectionArn    = var.github_connection_arn
        FullRepositoryId = var.github_repository
        BranchName       = "main"
      }
    }
  }
  
  stage {
    name = "Build"
    
    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      
      configuration = {
        ProjectName = aws_codebuild_project.backend.name
      }
    }
  }
  
  stage {
    name = "Deploy"
    
    action {
      name            = "Deploy"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "ECS"
      version         = "1"
      input_artifacts = ["build_output"]
      
      configuration = {
        ClusterName = aws_ecs_cluster.main.name
        ServiceName = aws_ecs_service.backend.name
        FileName    = "imagedefinitions.json"
      }
    }
  }
  
  tags = {
    Name = "jan-sewa-backend-pipeline"
  }
}
```

### BuildSpec File

Create `backend/buildspec.yml`:

```yaml
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
  
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $ECR_REPOSITORY_URI:latest .
      - docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG
  
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker images...
      - docker push $ECR_REPOSITORY_URI:latest
      - docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
      - echo Writing image definitions file...
      - printf '[{"name":"backend","imageUri":"%s"}]' $ECR_REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files:
    - imagedefinitions.json
```

---

## Cost Optimization

### Strategies

1. **Use Spot Instances** for non-critical workloads
2. **Right-size resources** based on actual usage
3. **Enable S3 Intelligent-Tiering** for automatic cost optimization
4. **Use Reserved Instances** for predictable workloads (save up to 72%)
5. **Enable Auto Scaling** to match capacity with demand
6. **Use CloudFront** to reduce data transfer costs
7. **Clean up unused resources** regularly
8. **Monitor costs** with AWS Cost Explorer and Budgets

### Cost Monitoring

Create `terraform/budgets.tf`:

```hcl
# AWS Budget
resource "aws_budgets_budget" "monthly" {
  name              = "jan-sewa-monthly-budget"
  budget_type       = "COST"
  limit_amount      = "500"
  limit_unit        = "USD"
  time_period_start = "2026-03-01_00:00"
  time_unit         = "MONTHLY"
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
```

---

## Backup & Disaster Recovery

### RDS Automated Backups

Already configured in RDS setup:
- Daily automated backups (7-day retention)
- Backup window: 03:00-04:00 UTC
- Multi-AZ for high availability
- Point-in-time recovery enabled

### Manual Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash

# Backup RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier jan-sewa-db \
  --db-snapshot-identifier jan-sewa-db-manual-$(date +%Y%m%d-%H%M%S)

# Backup S3 to another region
aws s3 sync \
  s3://jan-sewa-documents-production \
  s3://jan-sewa-documents-backup-us-east-1 \
  --region us-east-1

echo "Backup completed successfully"
```

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: 1 hour
2. **RPO (Recovery Point Objective)**: 5 minutes
3. **Multi-AZ deployment** for automatic failover
4. **Cross-region backups** for S3 data
5. **Infrastructure as Code** for quick rebuild
6. **Documented runbooks** for recovery procedures

### Recovery Procedures

**Database Failure:**
```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier jan-sewa-db-restored \
  --db-snapshot-identifier <snapshot-id>
```

**Complete Region Failure:**
1. Deploy infrastructure in backup region using Terraform
2. Restore RDS from cross-region snapshot
3. Sync S3 data from backup bucket
4. Update Route 53 to point to new region
5. Verify application functionality

---

## Deployment Checklist

### Pre-Deployment
- [ ] AWS account configured
- [ ] Domain registered and DNS configured
- [ ] SSL certificate issued in ACM
- [ ] Secrets stored in Secrets Manager
- [ ] Terraform state bucket created
- [ ] GitHub connection configured (for CI/CD)
- [ ] Alert email configured

### Infrastructure Deployment
- [ ] Run `terraform init`
- [ ] Run `terraform plan` and review
- [ ] Run `terraform apply`
- [ ] Verify VPC and networking
- [ ] Verify RDS database is running
- [ ] Verify ElastiCache Redis is running
- [ ] Verify S3 bucket is created

### Application Deployment
- [ ] Build Docker image
- [ ] Push image to ECR
- [ ] Run database migrations
- [ ] Deploy ECS service
- [ ] Verify health checks passing
- [ ] Test API endpoints
- [ ] Configure auto-scaling

### Security
- [ ] Enable WAF
- [ ] Configure security groups
- [ ] Enable VPC Flow Logs
- [ ] Enable GuardDuty
- [ ] Enable Security Hub
- [ ] Review IAM policies

### Monitoring
- [ ] Configure CloudWatch dashboards
- [ ] Set up CloudWatch alarms
- [ ] Configure SNS notifications
- [ ] Enable Container Insights
- [ ] Test alert notifications

### Post-Deployment
- [ ] Load testing
- [ ] Security scanning
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Team training

---

## Useful Commands

### ECS
```bash
# List clusters
aws ecs list-clusters

# List services
aws ecs list-services --cluster jan-sewa-cluster

# Describe service
aws ecs describe-services --cluster jan-sewa-cluster --services jan-sewa-backend-service

# Update service (force new deployment)
aws ecs update-service --cluster jan-sewa-cluster --service jan-sewa-backend-service --force-new-deployment

# View logs
aws logs tail /ecs/jan-sewa-backend --follow
```

### RDS
```bash
# Describe database
aws rds describe-db-instances --db-instance-identifier jan-sewa-db

# Create snapshot
aws rds create-db-snapshot --db-instance-identifier jan-sewa-db --db-snapshot-identifier manual-backup

# List snapshots
aws rds describe-db-snapshots --db-instance-identifier jan-sewa-db
```

### S3
```bash
# List buckets
aws s3 ls

# Sync local to S3
aws s3 sync ./documents s3://jan-sewa-documents-production/

# Download from S3
aws s3 cp s3://jan-sewa-documents-production/file.pdf ./
```

---

## Troubleshooting

### ECS Tasks Not Starting
1. Check CloudWatch logs: `/ecs/jan-sewa-backend`
2. Verify security groups allow traffic
3. Check IAM role permissions
4. Verify secrets are accessible
5. Check ECR image exists

### Database Connection Issues
1. Verify security group allows port 5432
2. Check database is in same VPC
3. Verify credentials in Secrets Manager
4. Test connection from ECS task

### High Costs
1. Review AWS Cost Explorer
2. Check for unused resources
3. Verify auto-scaling is working
4. Consider Reserved Instances
5. Enable S3 lifecycle policies

---

## Support & Resources

### AWS Documentation
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

### Terraform
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

### Monitoring
- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)

---

**Last Updated**: March 7, 2026  
**Version**: 1.0.0  
**Status**: Production Ready
