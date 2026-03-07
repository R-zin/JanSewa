# Government Services Assistant

An AI-powered assistant that helps citizens access and modify government services with browser automation, document management, DigiLocker integration, OCR extraction, and speech-to-text support.

## Features

### Core Capabilities
- **AI Conversational Agent**: Get guidance on government services using Google Gemini AI
- **Service Knowledge Base**: Comprehensive information on Aadhaar, PAN, certificates, and more
- **Eligibility Assessment**: Check eligibility for services with personalized guidance
- **Document Management**: Secure encrypted storage with OCR extraction
- **Browser Automation**: Automated form filling and portal navigation
- **DigiLocker Integration**: Import and sync government documents
- **Multi-language Support**: English, Hindi, Tamil, Telugu, and more
- **Speech-to-Text**: Voice commands and form input
- **User Dashboard**: Track service requests, documents, and notifications

### Services Supported
- **Aadhaar Services**: Name change, address update, mobile number update
- **Identity Cards**: PAN, Voter ID, Driving License, Passport modifications
- **Certificates**: OBC, Income, Caste, Domicile, Birth, Death, Marriage certificates
- **Data Access**: RTI requests and data access applications

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL
- **Cache**: Redis
- **AI**: Google Gemini Pro
- **Cloud**: AWS (S3, Textract)
- **OCR**: Tesseract, AWS Textract
- **Encryption**: Fernet (AES-128)

### Frontend
- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Hooks

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Browser Automation**: Selenium/Playwright (planned)
- **Speech Recognition**: Web Speech API / Whisper (planned)

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # API endpoints
│   │   ├── core/                 # Configuration
│   │   ├── db/                   # Database models
│   │   ├── models/               # Pydantic models
│   │   └── services/             # Business logic
│   ├── main.py                   # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js pages
│   │   └── components/           # React components
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Google AI API key
- AWS credentials (for S3 and Textract)
- DigiLocker OAuth credentials (optional)

### Environment Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd government-services-assistant
```

2. **Configure environment variables**

Create `backend/.env`:
```env
# Database
DATABASE_URL=postgresql://user:password@db:5432/govservices

# Redis
REDIS_URL=redis://redis:6379/0

# AWS
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=gov-services-documents

# Google AI
GOOGLE_API_KEY=your_google_api_key

# Security
SECRET_KEY=your-secret-key-change-in-production

# DigiLocker (optional)
DIGILOCKER_CLIENT_ID=your_client_id
DIGILOCKER_CLIENT_SECRET=your_client_secret
DIGILOCKER_REDIRECT_URI=http://localhost:8000/api/v1/digilocker/callback
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. **Start the application**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## API Endpoints

### Conversational Agent
- `POST /api/v1/agent/chat` - Send message to AI agent
- `GET /api/v1/agent/services` - List available services
- `GET /api/v1/agent/services/{service_id}` - Get service details
- `POST /api/v1/agent/eligibility/check` - Check eligibility

### Document Management
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/list` - List documents
- `GET /api/v1/documents/{document_id}` - Get document
- `DELETE /api/v1/documents/{document_id}` - Delete document
- `GET /api/v1/documents/ocr/status/{task_id}` - OCR status
- `GET /api/v1/documents/ocr/result/{task_id}` - OCR result

### Browser Automation
- `POST /api/v1/automation/start` - Start automation
- `POST /api/v1/automation/{session_id}/pause` - Pause automation
- `POST /api/v1/automation/{session_id}/resume` - Resume automation
- `GET /api/v1/automation/{session_id}/status` - Get status
- `GET /api/v1/automation/{session_id}/logs` - Get logs

### Dashboard
- `GET /api/v1/dashboard/{user_id}` - Get dashboard data
- `GET /api/v1/dashboard/{user_id}/summary` - Get summary
- `GET /api/v1/dashboard/{user_id}/notifications` - Get notifications
- `GET /api/v1/dashboard/{user_id}/history` - Get service history

### DigiLocker
- `GET /api/v1/digilocker/auth/url` - Get OAuth URL
- `POST /api/v1/digilocker/auth/callback` - OAuth callback
- `GET /api/v1/digilocker/documents` - List documents
- `POST /api/v1/digilocker/documents/{doc_id}/import` - Import document
- `POST /api/v1/digilocker/sync` - Sync documents

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Security Features

- **Encryption**: All documents encrypted with user-specific keys
- **Session Management**: Temporary context storage with automatic cleanup
- **Privacy Controls**: PII detection and sanitization
- **Data Minimization**: Only necessary data collected
- **Secure Credentials**: Encrypted storage for portal credentials
- **Token Management**: Encrypted OAuth tokens with automatic refresh

## Architecture

### Service Layer
- **ConversationalAgent**: AI-powered chat interface
- **ServiceKnowledgeBase**: Government service information
- **EligibilityEngine**: Eligibility assessment logic
- **DocumentManager**: Document requirements and validation
- **DocumentStorage**: Encrypted document storage with S3
- **OCREngine**: Text extraction from images
- **DocumentParser**: Structured data extraction
- **BrowserAutomationAgent**: Portal automation
- **CAPTCHAHandler**: CAPTCHA detection and guidance
- **DigiLockerClient**: DigiLocker integration
- **LanguageService**: Multi-language support
- **SpeechRecognitionEngine**: Voice input processing
- **DashboardService**: User dashboard management

### Data Flow
1. User interacts with chat interface
2. Request sent to conversational agent
3. Agent routes to appropriate service
4. Service processes request
5. Response returned with guidance
6. User can trigger automation or document operations

## Deployment

### Production Considerations
- Use production-grade database (AWS RDS)
- Configure Redis for session storage (AWS ElastiCache)
- Set up CDN for static assets
- Enable SSL/TLS certificates
- Configure proper CORS origins
- Set strong SECRET_KEY
- Enable rate limiting
- Set up monitoring and logging
- Configure backup procedures

### Docker Production Build
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Disclaimer

This system provides guidance only and does not process actual government applications. Users must complete official procedures through government portals.

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: support@example.com

## Roadmap

- [ ] Complete browser automation with Selenium/Playwright
- [ ] Implement property-based testing
- [ ] Add browser extension for step-by-step guidance
- [ ] Integrate AWS Textract for advanced OCR
- [ ] Add more government services
- [ ] Implement workflow definitions for common services
- [ ] Add user authentication and authorization
- [ ] Create mobile app
- [ ] Add analytics and monitoring
- [ ] Implement A/B testing for UI improvements
