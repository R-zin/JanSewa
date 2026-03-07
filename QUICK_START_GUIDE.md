# Government Services Assistant - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker Desktop installed
- AWS account (free tier works)
- Google AI API key (free tier available)

---

## Step 1: Clone and Setup (2 minutes)

```bash
# Navigate to project
cd government-services-assistant

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

---

## Step 2: Configure Environment (2 minutes)

### Backend Configuration (`backend/.env`)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/govt_services

# Redis
REDIS_URL=redis://redis:6379/0

# AWS S3 (Get from AWS Console)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# Google AI (Get from https://makersuite.google.com/app/apikey)
GOOGLE_AI_API_KEY=your_gemini_api_key

# Encryption (Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_32_byte_encryption_key

# DigiLocker (Optional for demo)
DIGILOCKER_CLIENT_ID=your_client_id
DIGILOCKER_CLIENT_SECRET=your_client_secret
DIGILOCKER_REDIRECT_URI=http://localhost:8000/api/v1/digilocker/callback
```

### Frontend Configuration (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 3: Start Services (1 minute)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Services will be available at:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## Step 4: Verify Installation

### Check Backend Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Check Frontend
Open browser: http://localhost:3000
- You should see the chat interface

### Check API Docs
Open browser: http://localhost:8000/docs
- Interactive API documentation

---

## Step 5: Try Demo Scenarios

### Scenario 1: Chat with AI Assistant
1. Go to http://localhost:3000
2. Type: "I need to change my name on Aadhaar"
3. Follow the AI guidance

### Scenario 2: Upload a Document
1. Click "Documents" in navigation
2. Click "Upload Document"
3. Select a PDF or image file
4. View malware scan results
5. See document in list

### Scenario 3: View Dashboard
1. Click "Dashboard" in navigation
2. See service requests
3. Check notifications
4. View storage usage

### Scenario 4: Browser Extension
1. Open Chrome/Edge
2. Go to Extensions → Developer Mode
3. Click "Load Unpacked"
4. Select `extension/` folder
5. Visit https://uidai.gov.in
6. See guidance panel appear

---

## Common Issues & Solutions

### Issue: Docker containers won't start
**Solution:**
```bash
# Stop all containers
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild and start
docker-compose up --build -d
```

### Issue: Backend can't connect to database
**Solution:**
```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Issue: Frontend can't reach backend
**Solution:**
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Should be `http://localhost:8000`
- Restart frontend: `docker-compose restart frontend`

### Issue: AWS S3 errors
**Solution:**
- Verify AWS credentials in `backend/.env`
- Check S3 bucket exists and is accessible
- Verify IAM permissions for S3 access

### Issue: Google AI API errors
**Solution:**
- Verify API key in `backend/.env`
- Check API key is enabled at https://makersuite.google.com
- Ensure Gemini Pro API is enabled

---

## Development Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
```

### Stop Services
```bash
# Stop all
docker-compose stop

# Stop and remove
docker-compose down

# Stop and remove with volumes
docker-compose down -v
```

### Run Tests
```bash
# Backend tests
docker-compose exec backend pytest

# Specific test file
docker-compose exec backend pytest tests/test_config.py -v
```

### Access Database
```bash
# PostgreSQL shell
docker-compose exec db psql -U postgres -d govt_services

# Run SQL
docker-compose exec db psql -U postgres -d govt_services -c "SELECT * FROM users;"
```

### Access Redis
```bash
# Redis CLI
docker-compose exec redis redis-cli

# Check keys
docker-compose exec redis redis-cli KEYS "*"
```

---

## API Quick Reference

### Chat with AI
```bash
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help with Aadhaar name change",
    "language": "en",
    "session_id": "test-session"
  }'
```

### Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@document.pdf" \
  -F "document_type=identity_proof" \
  -F "category=identity" \
  -F "user_id=1"
```

### Get Dashboard Data
```bash
curl http://localhost:8000/api/v1/dashboard/1
```

### List Services
```bash
curl http://localhost:8000/api/v1/agent/services
```

---

## Project Structure

```
government-services-assistant/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Configuration
│   │   ├── db/             # Database models
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   └── workflows/      # Workflow definitions
│   ├── tests/              # Backend tests
│   └── main.py             # Entry point
├── frontend/               # Next.js frontend
│   └── src/
│       ├── app/            # Pages
│       └── components/     # React components
├── extension/              # Browser extension
│   ├── manifest.json
│   ├── content.js
│   └── background.js
└── docker-compose.yml      # Docker configuration
```

---

## Next Steps

### For Development
1. Read `README.md` for detailed documentation
2. Check `API_DOCUMENTATION.md` for API reference
3. Review `DEPLOYMENT.md` for deployment guide
4. Explore `backend/app/services/` for service implementations

### For Testing
1. Try all demo scenarios
2. Upload different document types
3. Test OCR with various images
4. Explore browser extension on different portals

### For Customization
1. Add new services in `backend/app/data/services_data.py`
2. Create new workflows in `backend/app/workflows/`
3. Customize UI in `frontend/src/components/`
4. Add new API endpoints in `backend/app/api/v1/endpoints/`

---

## Support & Resources

### Documentation
- `README.md` - Project overview
- `API_DOCUMENTATION.md` - API reference
- `DEPLOYMENT.md` - Deployment guide
- `PROJECT_STATUS_REPORT.md` - Detailed status
- `PROTOTYPE_STATUS_FINAL.md` - Prototype capabilities

### API Documentation
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

### Logs
- Backend: `docker-compose logs backend`
- Frontend: `docker-compose logs frontend`
- Database: `docker-compose logs db`

---

## Security Notes

⚠️ **This is a prototype for demonstration purposes**

- No authentication implemented
- No authorization checks
- Not suitable for production
- Do not use with real user data
- Do not expose to public internet

For production deployment, implement:
- User authentication (JWT)
- Role-based access control
- API rate limiting
- HTTPS/TLS
- Security headers
- Input validation
- SQL injection prevention
- XSS protection

---

## Troubleshooting Checklist

- [ ] Docker Desktop is running
- [ ] All environment variables are set
- [ ] AWS credentials are valid
- [ ] Google AI API key is valid
- [ ] S3 bucket exists and is accessible
- [ ] Ports 3000, 8000, 5432, 6379 are available
- [ ] Docker has enough resources (4GB RAM minimum)
- [ ] Internet connection is active

---

**Quick Start Complete!** 🎉

You now have a fully functional Government Services Assistant prototype running locally.

For questions or issues, check the documentation files or review the logs.
