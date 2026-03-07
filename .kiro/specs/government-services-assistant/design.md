# Design Document: Government Services Assistant

## Overview

The Government Services Assistant is an AI-powered conversational agent that provides citizens with step-by-step guidance for navigating government services. The system acts as an intelligent guide rather than a transaction processor, helping users understand requirements, prepare documentation, and follow correct procedures for services like Aadhaar modifications, data access requests, and various government record updates.

### Core Capabilities

- **Service Guidance**: Provide structured, step-by-step instructions for government services
- **Eligibility Assessment**: Determine user eligibility through interactive questioning
- **Document Management**: List and explain document requirements with alternatives
- **Status Tracking Guidance**: Help users understand and check service request status
- **Multi-Language Support**: Deliver guidance in multiple official languages
- **Privacy-First Design**: Provide guidance without storing sensitive personal information
- **Personalized Dashboard**: Track service requests, documents, and activity history in one place
- **Browser Automation**: Automatically navigate government websites and fill forms
- **CAPTCHA Handling**: Pause automation and guide users through CAPTCHA challenges
- **Browser Extension**: Provide step-by-step guidance while users browse government portals
- **Secure Document Storage**: Encrypt and store user documents for reuse across services

### Design Principles

1. **Guidance, Not Processing**: The system guides users but does not process actual applications
2. **Information Currency**: Maintain up-to-date service information with clear update timestamps
3. **Privacy by Design**: Minimize data collection and provide security warnings
4. **Accessibility**: Support multiple languages and clear communication
5. **Verification**: Always direct users to official portals for actual transactions
6. **Security First**: Encrypt sensitive documents and maintain audit logs
7. **User Control**: Allow users to control automation level and data sharing
8. **Transparency**: Log all automated actions for user review

## Architecture

### Technology Stack

**Backend Framework**: FastAPI (Python)
- High-performance async API framework
- Automatic OpenAPI documentation
- Native async/await support for concurrent operations
- Type hints and Pydantic models for data validation

**Frontend Framework**: Next.js (React)
- Server-side rendering for improved performance
- React-based component architecture
- Built-in routing and API routes
- Optimized for production deployments

**AI/LLM Integration**: Google AI SDK (Gemini)
- Conversational agent capabilities
- Multi-language support
- Context-aware responses
- Structured output generation

**Database**: 
- PostgreSQL for relational data (service guides, user profiles, document metadata)
- Redis for caching and session management

**Containerization**: Docker and Docker Compose
- Isolated service deployment
- Consistent development and production environments
- Easy scaling and orchestration

### System Components

```mermaid
graph TB
    subgraph "Frontend - Next.js"
        UI[User Interface]
        Dashboard[User Dashboard]
        BrowserExt[Browser Extension]
    end
    
    subgraph "Backend - FastAPI"
        API[FastAPI REST API]
        Agent[Conversational Agent - Gemini]
        ServiceKB[Service Knowledge Base]
        EligibilityEngine[Eligibility Engine]
        DocumentManager[Document Manager]
        LanguageService[Language Service]
        AutomationAgent[Browser Automation Agent]
        GuidanceEngine[Step-by-Step Guidance Engine]
        FormAnalyzer[Form Field Analyzer]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis Cache)]
        DocStorage[Document Storage - Encrypted]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini API]
        DigiLocker[DigiLocker API]
        OCR[OCR Engine]
    end
    
    UI --> API
    Dashboard --> API
    BrowserExt --> API
    
    API --> Agent
    API --> ServiceKB
    API --> EligibilityEngine
    API --> DocumentManager
    API --> LanguageService
    API --> AutomationAgent
    
    Agent --> Gemini
    Agent --> Redis
    
    ServiceKB --> PostgreSQL
    EligibilityEngine --> PostgreSQL
    DocumentManager --> PostgreSQL
    DocumentManager --> DocStorage
    
    AutomationAgent --> Redis
    AutomationAgent --> DocStorage
    
    LanguageService --> Gemini
    LanguageService --> Redis
    
    API --> Redis
    API --> PostgreSQL
    
    DocumentManager --> DigiLocker
    DocumentManager --> OCR
```

### Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose Environment"
        subgraph "Frontend Container"
            NextJS[Next.js App<br/>Port 3000]
        end
        
        subgraph "Backend Container"
            FastAPI[FastAPI Server<br/>Port 8000]
        end
        
        subgraph "Database Container"
            PG[PostgreSQL<br/>Port 5432]
        end
        
        subgraph "Cache Container"
            RedisDB[Redis<br/>Port 6379]
        end
        
        subgraph "Storage Volume"
            DocVol[Encrypted Documents<br/>Volume Mount]
        end
    end
    
    NextJS --> FastAPI
    FastAPI --> PG
    FastAPI --> RedisDB
    FastAPI --> DocVol
    
    Internet[Internet] --> NextJS
    FastAPI --> GeminiAPI[Google Gemini API]
    FastAPI --> DigiAPI[DigiLocker API]
```

### Docker Compose Configuration

**docker-compose.yml**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: govt-services-db
    environment:
      POSTGRES_DB: govt_services
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - govt-services-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: govt-services-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - govt-services-network

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: govt-services-backend
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/govt_services
      REDIS_URL: redis://redis:6379
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: ${ENVIRONMENT:-development}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}
    volumes:
      - ./backend:/app
      - document_storage:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - govt-services-network

  # Next.js Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: govt-services-frontend
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
      NEXT_PUBLIC_WS_URL: ${NEXT_PUBLIC_WS_URL:-ws://localhost:8000}
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    depends_on:
      - backend
    command: npm run dev
    networks:
      - govt-services-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  document_storage:
    driver: local

networks:
  govt-services-network:
    driver: bridge
```

**Backend Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run application
CMD ["npm", "run", "dev"]
```

**Environment Variables (.env.example)**

```bash
# Database
DB_USER=govt_services_user
DB_PASSWORD=secure_password_here
DATABASE_URL=postgresql://govt_services_user:secure_password_here@postgres:5432/govt_services

# Redis
REDIS_URL=redis://redis:6379

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Application
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Component Descriptions

**FastAPI Backend**
- RESTful API server handling all backend operations
- Async request handling for high concurrency
- Automatic request/response validation with Pydantic
- OpenAPI documentation at `/docs` endpoint
- JWT-based authentication for secure sessions
- CORS configuration for Next.js frontend
- WebSocket support for real-time updates

**Next.js Frontend**
- Server-side rendered React application
- Component-based UI architecture
- API routes for backend communication
- Responsive design for mobile and desktop
- Client-side state management (React Context/Redux)
- Optimized asset loading and code splitting

**Conversational Agent (Gemini-powered)**
- Powered by Google Gemini API for natural language understanding
- Interprets user requests and routes to appropriate services
- Maintains conversation context in Redis sessions
- Generates natural language responses based on structured data
- Supports multi-turn conversations with context awareness
- Structured output generation for consistent API responses

**Service Knowledge Base**
- PostgreSQL database storing structured service information
- Maintains service guides with step-by-step procedures
- Tracks document requirements and eligibility criteria
- Includes links to official portals and contact information
- Records last update timestamps for information currency
- Indexed for fast query performance

**Eligibility Engine**
- Python-based rule evaluation engine
- Evaluates user eligibility for requested services
- Asks clarifying questions to gather necessary information
- Validates responses against eligibility criteria stored in PostgreSQL
- Suggests alternative services when eligibility is not met

**Document Manager**
- FastAPI endpoints for document operations
- Maintains comprehensive document requirement lists in PostgreSQL
- Specifies document formats, validity periods, and attestation needs
- Provides alternative document options
- Explains where to obtain missing documents
- Integrates with DigiLocker API for document import

**Language Service**
- Gemini-powered translation service
- Translates guidance into user's preferred language
- Maintains consistent terminology across languages
- Redis caching for frequently translated content
- Handles technical terms with explanations when direct translation unavailable
- Preserves official terminology while providing translations

**Session Manager**
- Redis-based session storage for fast access
- Manages conversation state within session boundaries
- Implements privacy controls to prevent data persistence
- Clears sensitive information at session end
- Enforces data minimization principles
- Session expiration and cleanup

**User Dashboard (Next.js)**
- React-based personalized dashboard
- Displays service requests and status from PostgreSQL
- Shows stored documents organized by category
- Provides activity history for past 12 months
- Real-time notifications via WebSocket
- Shows storage usage and document expiration warnings
- Quick access links to frequently used services

**Browser Automation Agent**
- Python-based automation using Playwright or Selenium
- Automates navigation through government websites
- Identifies and fills form fields using user data
- Executes navigation actions (clicks, selections, page navigation)
- Handles document uploads from encrypted storage
- Maintains session state in Redis
- Pauses on errors or unexpected pages
- Logs all actions to PostgreSQL for audit and review
- Supports resuming paused sessions

**CAPTCHA Handler**
- Detects CAPTCHA challenges during automation
- Pauses automation and notifies user via WebSocket
- Provides instructions for completing CAPTCHAs
- Highlights CAPTCHA elements for visibility
- Detects completion and resumes automation
- Supports multiple CAPTCHA types (image, text, checkbox)
- Handles CAPTCHA failures with retry instructions
- Implements timeout prompts for incomplete CAPTCHAs

**Browser Extension (React)**
- Chrome/Firefox extension built with React
- Activates on supported government portals
- Displays step-by-step guidance panel
- Highlights form fields requiring input
- Tracks progress through multi-page workflows
- Detects navigation errors and provides corrections
- Offers autofill from user profile via API
- Shows tooltip guidance on field hover
- Supports manual and automated modes
- Synchronizes progress with dashboard via API
- Allows per-portal guidance toggle

**Document Storage**
- Encrypted file storage using Python cryptography library
- Stores documents with comprehensive metadata in PostgreSQL
- File storage in Docker volume with encryption at rest
- Supports PDF, JPEG, PNG, DOCX formats
- Validates file sizes (10MB limit per document)
- Malware scanning before storage
- Allows custom categorization
- Fast decryption and retrieval
- Supports permanent deletion with complete cleanup
- Enforces 100MB total storage quota per user
- Preview generation for supported formats
- Automatically archives expired documents
- Maintains audit log in PostgreSQL
- Supports document versioning
- Enables sharing with automation agent

**PostgreSQL Database**
- Stores service guides and requirements
- User profiles and preferences
- Document metadata and audit logs
- Service request tracking
- Activity history
- Eligibility criteria and rules

**Redis Cache**
- Session storage for active conversations
- Caching for frequently accessed service data
- Translation cache for language service
- Automation session state
- Real-time notification queue
- Rate limiting and throttling

## Components and Interfaces

### API Architecture

**FastAPI REST Endpoints**

```python
# Main API routes
GET  /api/v1/services                    # List available services
GET  /api/v1/services/{service_id}       # Get service details
POST /api/v1/chat                        # Process chat message
GET  /api/v1/chat/history                # Get conversation history
POST /api/v1/eligibility/check           # Check eligibility
POST /api/v1/documents/upload            # Upload document
GET  /api/v1/documents                   # List user documents
GET  /api/v1/documents/{doc_id}          # Get document
DELETE /api/v1/documents/{doc_id}        # Delete document
GET  /api/v1/dashboard                   # Get dashboard data
POST /api/v1/automation/start            # Start automation session
POST /api/v1/automation/pause            # Pause automation
POST /api/v1/automation/resume           # Resume automation
GET  /api/v1/automation/status           # Get automation status
POST /api/v1/digilocker/connect          # Connect DigiLocker
POST /api/v1/digilocker/import           # Import documents
POST /api/v1/ocr/extract                 # Extract data from document
WebSocket /ws/automation                 # Real-time automation updates
WebSocket /ws/notifications              # Real-time notifications
```

### Service Knowledge Base Schema

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

class ServiceCategory(str, Enum):
    AADHAAR = "aadhaar"
    DATA_ACCESS = "data_access"
    RECORD_MODIFICATION = "record_modification"
    STATUS_INQUIRY = "status_inquiry"
    IDENTITY_CARD = "identity_card"
    CERTIFICATE = "certificate"

class ServiceStep(BaseModel):
    step_number: int
    description: str
    requires_in_person: bool
    online_available: bool
    estimated_duration: str
    notes: Optional[str] = None

class ValidationRule(BaseModel):
    rule_type: str
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None

class EligibilityCriterion(BaseModel):
    criterion_id: str
    description: str
    required: bool
    validation_rule: ValidationRule
    failure_message: str
    alternatives: Optional[List[str]] = None

class AlternativeDocument(BaseModel):
    document_id: str
    document_name: str
    conditions: str

class DocumentRequirement(BaseModel):
    document_id: str
    document_name: str
    official_name: str
    required: bool
    accepts_copies: bool
    requires_attestation: bool
    requires_notarization: bool
    format: Optional[str] = None
    validity_period: Optional[str] = None
    alternatives: List[AlternativeDocument]
    obtainment_guidance: str

class ProcessingTime(BaseModel):
    minimum: str
    maximum: str
    typical: str
    factors: List[str]

class ContactInfo(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    helpline: Optional[str] = None

class ServiceGuide(BaseModel):
    service_id: str
    service_name: str
    category: ServiceCategory
    description: str
    steps: List[ServiceStep]
    eligibility_criteria: List[EligibilityCriterion]
    document_requirements: List[DocumentRequirement]
    processing_time: ProcessingTime
    official_portal_url: HttpUrl
    contact_info: ContactInfo
    last_updated: datetime
    available_languages: List[str]
```

### Conversational Agent Interface

```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class RequestType(str, Enum):
    SERVICE_GUIDANCE = "service_guidance"
    ELIGIBILITY_CHECK = "eligibility_check"
    DOCUMENT_INQUIRY = "document_inquiry"
    STATUS_TRACKING = "status_tracking"
    CLARIFICATION = "clarification"

class ResponseType(str, Enum):
    GUIDANCE = "guidance"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    WARNING = "warning"

class ConversationContext(BaseModel):
    service_id: Optional[str] = None
    current_step: Optional[int] = None
    collected_info: Dict[str, Any] = {}
    last_intent: Optional[str] = None

class UserRequest(BaseModel):
    message: str
    language: str
    request_type: RequestType
    context: ConversationContext

class ActionItem(BaseModel):
    action_type: str
    description: str
    url: Optional[HttpUrl] = None

class PortalLink(BaseModel):
    title: str
    url: HttpUrl
    description: str

class SecurityWarning(BaseModel):
    warning_type: str
    message: str
    severity: str
    recommendations: List[str]

class AgentResponse(BaseModel):
    message: str
    language: str
    response_type: ResponseType
    action_items: Optional[List[ActionItem]] = None
    links: Optional[List[PortalLink]] = None
    follow_up_questions: Optional[List[str]] = None
    warnings: Optional[List[SecurityWarning]] = None

class Session(BaseModel):
    session_id: str
    user_id: str
    start_time: datetime
    language: str
    conversation_history: List[Dict[str, Any]]
    temporary_context: Dict[str, Any]

class ConversationalAgent:
    """
    Gemini-powered conversational agent for government services guidance
    """
    
    async def process_request(
        self, 
        request: UserRequest, 
        session: Session
    ) -> AgentResponse:
        """Process user input and generate response using Gemini"""
        pass
    
    async def provide_service_guidance(
        self, 
        service_id: str, 
        session: Session
    ) -> AgentResponse:
        """Handle service guidance requests"""
        pass
    
    async def assess_eligibility(
        self, 
        service_id: str, 
        user_info: Dict[str, Any], 
        session: Session
    ) -> AgentResponse:
        """Assess eligibility for a service"""
        pass
    
    async def get_document_requirements(
        self, 
        service_id: str, 
        session: Session
    ) -> AgentResponse:
        """Handle document inquiries"""
        pass
    
    async def guide_status_tracking(
        self, 
        reference_number: str, 
        service_id: str, 
        session: Session
    ) -> AgentResponse:
        """Guide status tracking"""
        pass
```

### Eligibility Engine Interface

```python
from typing import List, Dict, Any
from pydantic import BaseModel
from enum import Enum

class QuestionType(str, Enum):
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    DATE = "date"
    NUMERIC = "numeric"

class Question(BaseModel):
    question_id: str
    text: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    validation_rule: Optional[ValidationRule] = None
    required: bool

class FailedCriterion(BaseModel):
    criterion_id: str
    description: str
    reason: str
    possible_remedies: List[str]

class EligibilityResult(BaseModel):
    eligible: bool
    met_criteria: List[str]
    failed_criteria: List[FailedCriterion]
    confidence: float
    appeal_available: bool
    appeal_guidance: Optional[str] = None

class AlternativeService(BaseModel):
    service_id: str
    service_name: str
    reason: str
    eligibility_likelihood: float

class EligibilityEngine:
    """
    Rule-based eligibility evaluation engine
    """
    
    def evaluate_eligibility(
        self, 
        service_id: str, 
        responses: Dict[str, Any]
    ) -> EligibilityResult:
        """Evaluate eligibility based on criteria"""
        pass
    
    def generate_questions(
        self, 
        service_id: str, 
        existing_responses: Dict[str, Any]
    ) -> List[Question]:
        """Generate clarifying questions"""
        pass
    
    def suggest_alternatives(
        self, 
        service_id: str, 
        failed_criteria: List[str]
    ) -> List[AlternativeService]:
        """Suggest alternatives when ineligible"""
        pass
```

### Language Service Interface

```python
from enum import Enum
from pydantic import BaseModel

class FormalityLevel(str, Enum):
    FORMAL = "formal"
    NEUTRAL = "neutral"
    CASUAL = "casual"

class TranslationContext(BaseModel):
    domain: str
    preserve_terms: List[str]
    formality: FormalityLevel

class TerminologyEntry(BaseModel):
    term: str
    official_term: str
    translation: str
    explanation: Optional[str] = None
    language: str

class LanguageService:
    """
    Gemini-powered translation service with Redis caching
    """
    
    async def translate(
        self, 
        content: str, 
        target_language: str, 
        context: TranslationContext
    ) -> str:
        """Translate content to target language using Gemini"""
        pass
    
    async def get_terminology(
        self, 
        term: str, 
        language: str
    ) -> TerminologyEntry:
        """Get terminology in specific language"""
        pass
    
    def is_language_supported(self, language: str) -> bool:
        """Validate language support"""
        pass
    
    def get_supported_languages(self) -> List[str]:
        """Get available languages"""
        pass
```

### Privacy and Session Management Interface

```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict

class DataType(str, Enum):
    CONVERSATION_CONTEXT = "conversation_context"
    USER_PREFERENCE = "user_preference"
    PERSONAL_INFO = "personal_info"
    SENSITIVE_INFO = "sensitive_info"

class SensitiveDataType(str, Enum):
    AADHAAR_NUMBER = "aadhaar_number"
    PERSONAL_NAME = "personal_name"
    ADDRESS = "address"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"

class WarningType(str, Enum):
    SENSITIVE_DATA_ENTRY = "sensitive_data_entry"
    LINK_VERIFICATION = "link_verification"
    GUIDANCE_ONLY = "guidance_only"

class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class SecurityWarning(BaseModel):
    warning_type: WarningType
    message: str
    severity: SeverityLevel
    recommendations: List[str]

class SessionManager:
    """
    Redis-based session management
    """
    
    async def create_session(self, user_id: str, language: str) -> Session:
        """Create new session in Redis"""
        pass
    
    async def update_context(
        self, 
        session_id: str, 
        key: str, 
        value: Any
    ) -> None:
        """Update session context in Redis"""
        pass
    
    async def get_context(self, session_id: str, key: str) -> Any:
        """Get session context from Redis"""
        pass
    
    async def clear_sensitive_data(self, session_id: str) -> None:
        """Clear sensitive data from session"""
        pass
    
    async def end_session(self, session_id: str) -> None:
        """End session and cleanup from Redis"""
        pass
    
    def should_store(self, data_type: DataType) -> bool:
        """Check if data should be stored"""
        pass

class PrivacyControls:
    """
    Privacy validation and warning generation
    """
    
    def is_data_necessary(
        self, 
        data_type: DataType, 
        purpose: str
    ) -> bool:
        """Validate data collection necessity"""
        pass
    
    def generate_warning(
        self, 
        sensitive_data_type: SensitiveDataType
    ) -> SecurityWarning:
        """Generate security warnings"""
        pass
    
    def sanitize_for_logging(self, data: Any) -> Any:
        """Sanitize data for logging"""
        pass
```

### Dashboard Interface

### Dashboard Interface

```python
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
from enum import Enum

class NotificationType(str, Enum):
    ACTION_REQUIRED = "action_required"
    STATUS_UPDATE = "status_update"
    DOCUMENT_EXPIRING = "document_expiring"
    STORAGE_WARNING = "storage_warning"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ServiceStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    DELAYED = "delayed"

class RequiredAction(BaseModel):
    action_type: str
    description: str
    deadline: Optional[datetime] = None
    instructions: List[str]

class ServiceRequestSummary(BaseModel):
    request_id: str
    service_id: str
    service_name: str
    status: ServiceStatus
    last_updated: datetime
    estimated_completion: Optional[datetime] = None
    action_required: Optional[RequiredAction] = None

class DocumentSummary(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    category: str
    upload_date: datetime
    expiration_date: Optional[date] = None
    file_size: int
    version: int

class ServiceHistoryEntry(BaseModel):
    service_id: str
    service_name: str
    completion_date: datetime
    status: ServiceStatus
    confirmation_number: Optional[str] = None

class Notification(BaseModel):
    notification_id: str
    type: NotificationType
    message: str
    action_required: bool
    related_service_id: Optional[str] = None
    created_at: datetime
    priority: Priority

class ServiceLink(BaseModel):
    service_id: str
    service_name: str
    url: str
    usage_count: int

class StorageUsage(BaseModel):
    used_bytes: int
    total_bytes: int
    percentage_used: float
    document_count: int

class DocumentWarning(BaseModel):
    document_id: str
    document_name: str
    expiration_date: date
    days_until_expiration: int

class HistoryFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    service_types: Optional[List[str]] = None
    status_filter: Optional[List[ServiceStatus]] = None

class DashboardData(BaseModel):
    active_service_requests: List[ServiceRequestSummary]
    stored_documents: List[DocumentSummary]
    service_history: List[ServiceHistoryEntry]
    pending_notifications: List[Notification]
    quick_access_links: List[ServiceLink]
    last_login_timestamp: datetime
    storage_usage: StorageUsage
    expiration_warnings: List[DocumentWarning]

class Dashboard:
    """
    Dashboard service for user data aggregation
    """
    
    async def get_dashboard_data(self, user_id: str) -> DashboardData:
        """Get dashboard data for user from PostgreSQL"""
        pass
    
    async def update_service_status(
        self, 
        request_id: str, 
        status: ServiceStatus
    ) -> None:
        """Update service request status in PostgreSQL"""
        pass
    
    async def add_notification(
        self, 
        user_id: str, 
        notification: Notification
    ) -> None:
        """Add notification for pending action"""
        pass
    
    async def get_service_history(
        self, 
        user_id: str, 
        filters: Optional[HistoryFilters] = None
    ) -> List[ServiceHistoryEntry]:
        """Get filtered service history from PostgreSQL"""
        pass
    
    async def get_storage_usage(self, user_id: str) -> StorageUsage:
        """Get storage usage statistics"""
        pass
    
    async def get_expiration_warnings(
        self, 
        user_id: str
    ) -> List[DocumentWarning]:
        """Get document expiration warnings"""
        pass
```

### Browser Automation Agent Interface

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE_UPLOAD = "file_upload"
    TEXTAREA = "textarea"

class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    NAVIGATE = "navigate"
    UPLOAD = "upload"
    SUBMIT = "submit"
    WAIT = "wait"

class PauseReason(str, Enum):
    CAPTCHA_DETECTED = "captcha_detected"
    NAVIGATION_FAILED = "navigation_failed"
    UNEXPECTED_PAGE = "unexpected_page"
    USER_REQUESTED = "user_requested"
    VALIDATION_ERROR = "validation_error"
    OTP_REQUIRED = "otp_required"
    BIOMETRIC_REQUIRED = "biometric_required"

class AutomationSession(BaseModel):
    session_id: str
    user_id: str
    service_id: str
    portal_url: HttpUrl
    start_time: datetime
    status: SessionStatus
    current_url: str
    last_action_index: int

class FormField(BaseModel):
    field_id: str
    field_name: str
    field_type: FieldType
    required: bool
    validation_rules: List[ValidationRule]
    current_value: Optional[Any] = None
    placeholder: Optional[str] = None
    options: Optional[List[str]] = None

class NavigationAction(BaseModel):
    action_type: ActionType
    target_element: str
    value: Optional[Any] = None
    description: str

class NavigationResult(BaseModel):
    success: bool
    current_url: str
    page_title: str
    error: Optional[str] = None

class FieldError(BaseModel):
    field_id: str
    field_name: str
    error: str

class ValidationError(BaseModel):
    field: str
    error_type: str
    message: str
    suggested_correction: Optional[str] = None

class FillResult(BaseModel):
    success: bool
    filled_fields: List[str]
    failed_fields: List[FieldError]
    validation_errors: List[ValidationError]

class ActionResult(BaseModel):
    success: bool
    action_type: ActionType
    timestamp: datetime
    error: Optional[str] = None

class UploadResult(BaseModel):
    success: bool
    document_id: str
    field_id: str
    error: Optional[str] = None

class SessionState(BaseModel):
    session_id: str
    status: SessionStatus
    current_step: int
    total_steps: int
    completed_actions: int
    pause_reason: Optional[PauseReason] = None
    last_error: Optional[str] = None

class ActionLogEntry(BaseModel):
    timestamp: datetime
    action_type: ActionType
    description: str
    success: bool
    url: str
    error: Optional[str] = None

class ConfirmationData(BaseModel):
    confirmation_number: Optional[str] = None
    completion_date: datetime
    service_id: str
    summary: str
    documents: List[str]

class BrowserAutomationAgent:
    """
    Playwright/Selenium-based browser automation agent
    """
    
    async def start_session(
        self, 
        user_id: str, 
        service_id: str, 
        portal_url: str
    ) -> AutomationSession:
        """Start automation session and store state in Redis"""
        pass
    
    async def navigate_to(
        self, 
        session_id: str, 
        url: str
    ) -> NavigationResult:
        """Navigate to URL"""
        pass
    
    async def identify_form_fields(
        self, 
        session_id: str
    ) -> List[FormField]:
        """Identify form fields on current page"""
        pass
    
    async def fill_form_fields(
        self, 
        session_id: str, 
        form_data: Dict[str, Any]
    ) -> FillResult:
        """Fill form fields with user data"""
        pass
    
    async def execute_action(
        self, 
        session_id: str, 
        action: NavigationAction
    ) -> ActionResult:
        """Execute navigation action"""
        pass
    
    async def upload_document(
        self, 
        session_id: str, 
        field_id: str, 
        document_id: str
    ) -> UploadResult:
        """Upload document to form field"""
        pass
    
    async def pause_session(
        self, 
        session_id: str, 
        reason: PauseReason
    ) -> None:
        """Pause automation session"""
        pass
    
    async def resume_session(self, session_id: str) -> None:
        """Resume automation session"""
        pass
    
    async def get_session_state(self, session_id: str) -> SessionState:
        """Get session state from Redis"""
        pass
    
    async def get_action_log(
        self, 
        session_id: str
    ) -> List[ActionLogEntry]:
        """Get action log from PostgreSQL"""
        pass
    
    async def complete_session(
        self, 
        session_id: str, 
        confirmation_data: ConfirmationData
    ) -> None:
        """Complete session and save confirmation"""
        pass
```

### CAPTCHA Handler Interface

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum

class CAPTCHAType(str, Enum):
    IMAGE_SELECTION = "image_selection"
    TEXT_ENTRY = "text_entry"
    CHECKBOX = "checkbox"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"

class CAPTCHADetection(BaseModel):
    detected: bool
    captcha_type: Optional[CAPTCHAType] = None
    element_id: Optional[str] = None
    confidence: float

class RetryInstructions(BaseModel):
    message: str
    steps: List[str]
    attempts_remaining: Optional[int] = None

class TimeoutStatus(BaseModel):
    timed_out: bool
    elapsed_minutes: int
    prompt_user: bool

class CAPTCHAHandler:
    """
    CAPTCHA detection and handling service
    """
    
    async def detect_captcha(self, session_id: str) -> CAPTCHADetection:
        """Detect CAPTCHA on current page"""
        pass
    
    async def get_instructions(self, captcha_type: CAPTCHAType) -> List[str]:
        """Get instructions for CAPTCHA type"""
        pass
    
    async def highlight_captcha(
        self, 
        session_id: str, 
        element_id: str
    ) -> None:
        """Highlight CAPTCHA element"""
        pass
    
    async def check_completion(self, session_id: str) -> bool:
        """Check if CAPTCHA is completed"""
        pass
    
    async def handle_failure(self, session_id: str) -> RetryInstructions:
        """Handle CAPTCHA failure"""
        pass
    
    async def check_timeout(
        self, 
        session_id: str, 
        start_time: datetime
    ) -> TimeoutStatus:
        """Check for timeout"""
        pass
```

### Browser Extension Interface

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class ExtensionMode(str, Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"

class ActivationResult(BaseModel):
    activated: bool
    portal_supported: bool
    service_id: Optional[str] = None
    workflow_id: Optional[str] = None

class StepInstruction(BaseModel):
    step_number: int
    instruction: str
    action_type: str
    target_elements: List[str]
    completed: bool

class PageContext(BaseModel):
    url: str
    title: str
    form_fields: List[str]
    current_step: int

class NavigationCorrection(BaseModel):
    is_wrong_page: bool
    correct_url: str
    correction_steps: List[str]

class AutofillOffer(BaseModel):
    can_autofill: bool
    fields_to_fill: Dict[str, Any]
    missing_data: List[str]

class TooltipContent(BaseModel):
    field_name: str
    guidance: str
    example: Optional[str] = None
    validation_rules: List[str]

class ProgressState(BaseModel):
    workflow_id: str
    current_step: int
    total_steps: int
    percent_complete: float
    completed_steps: List[int]

class DocumentChecklist(BaseModel):
    service_id: str
    required_documents: List[DocumentRequirement]
    optional_documents: List[DocumentRequirement]
    user_has_documents: Dict[str, bool]

class ProgressData(BaseModel):
    workflow_id: str
    current_step: int
    completed_steps: List[int]
    timestamp: datetime

class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    address: 'Address'
    custom_fields: Dict[str, Any]

class Address(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str

class BrowserExtension:
    """
    React-based browser extension API client
    """
    
    async def activate(self, portal_url: str) -> ActivationResult:
        """Activate extension on portal"""
        pass
    
    async def get_step_instructions(
        self, 
        portal_url: str, 
        page_context: PageContext
    ) -> List[StepInstruction]:
        """Get step instructions for current page"""
        pass
    
    async def highlight_fields(self, field_ids: List[str]) -> None:
        """Highlight form fields"""
        pass
    
    async def advance_step(self, current_step: int) -> StepInstruction:
        """Advance to next step"""
        pass
    
    async def detect_wrong_page(
        self, 
        expected_url: str, 
        actual_url: str
    ) -> NavigationCorrection:
        """Detect wrong page navigation"""
        pass
    
    async def offer_autofill(
        self, 
        form_fields: List[FormField], 
        user_data: UserProfile
    ) -> AutofillOffer:
        """Offer autofill"""
        pass
    
    async def show_tooltip(self, field_id: str) -> TooltipContent:
        """Show field tooltip"""
        pass
    
    async def track_progress(
        self, 
        workflow_id: str, 
        current_step: int
    ) -> ProgressState:
        """Track workflow progress"""
        pass
    
    async def toggle_guidance(
        self, 
        portal_url: str, 
        enabled: bool
    ) -> None:
        """Toggle guidance for portal"""
        pass
    
    async def get_document_checklist(
        self, 
        service_id: str
    ) -> DocumentChecklist:
        """Get document checklist"""
        pass
    
    async def sync_with_dashboard(
        self, 
        user_id: str, 
        progress_data: ProgressData
    ) -> None:
        """Synchronize with dashboard"""
        pass
    
    async def switch_mode(self, mode: ExtensionMode) -> None:
        """Switch mode"""
        pass
```

### Document Storage Interface

```python
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional, Dict
from enum import Enum

class AuditAction(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    PREVIEW = "preview"
    DELETE = "delete"
    SHARE = "share"
    CATEGORIZE = "categorize"
    VERSION_UPLOAD = "version_upload"

class Document(BaseModel):
    document_id: Optional[str] = None
    file_name: str
    file_type: str
    file_size: int
    content: bytes

class DocumentMetadata(BaseModel):
    document_type: str
    category: Optional[str] = None
    expiration_date: Optional[date] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class DocumentPreview(BaseModel):
    document_id: str
    preview_url: str
    thumbnail_url: Optional[str] = None
    page_count: Optional[int] = None

class DeletionResult(BaseModel):
    success: bool
    document_id: str
    scheduled_deletion_date: datetime

class DocumentFilters(BaseModel):
    category: Optional[str] = None
    document_type: Optional[str] = None
    upload_date_range: Optional['DateRange'] = None
    expiration_date_range: Optional['DateRange'] = None

class DateRange(BaseModel):
    start: date
    end: date

class ArchivedDocument(BaseModel):
    document_id: str
    document_name: str
    archive_date: datetime
    expiration_date: date

class AuditLogEntry(BaseModel):
    timestamp: datetime
    user_id: str
    document_id: str
    action: AuditAction
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class VersionResult(BaseModel):
    success: bool
    document_id: str
    version_number: int
    previous_version_id: str

class ShareResult(BaseModel):
    success: bool
    document_id: str
    session_id: str
    expires_at: datetime

class ValidationResult(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]

class Threat(BaseModel):
    threat_type: str
    severity: SeverityLevel
    description: str

class ScanResult(BaseModel):
    clean: bool
    threats: List[Threat]
    scan_date: datetime

class DocumentStorage:
    """
    Encrypted document storage service using Python cryptography
    """
    
    async def upload_document(
        self, 
        user_id: str, 
        document: Document, 
        metadata: DocumentMetadata
    ) -> UploadResult:
        """Upload and encrypt document to Docker volume"""
        pass
    
    async def get_document(
        self, 
        user_id: str, 
        document_id: str
    ) -> Document:
        """Retrieve and decrypt document"""
        pass
    
    async def preview_document(
        self, 
        user_id: str, 
        document_id: str
    ) -> DocumentPreview:
        """Preview document without download"""
        pass
    
    async def delete_document(
        self, 
        user_id: str, 
        document_id: str
    ) -> DeletionResult:
        """Delete document permanently"""
        pass
    
    async def categorize_document(
        self, 
        user_id: str, 
        document_id: str, 
        category: str
    ) -> None:
        """Organize documents into categories"""
        pass
    
    async def list_documents(
        self, 
        user_id: str, 
        filters: Optional[DocumentFilters] = None
    ) -> List[DocumentSummary]:
        """Get all documents for user from PostgreSQL"""
        pass
    
    async def get_storage_usage(self, user_id: str) -> StorageUsage:
        """Check storage usage"""
        pass
    
    async def archive_expired_documents(
        self, 
        user_id: str
    ) -> List[ArchivedDocument]:
        """Archive expired documents"""
        pass
    
    async def get_audit_log(
        self, 
        user_id: str, 
        document_id: Optional[str] = None
    ) -> List[AuditLogEntry]:
        """Get audit log from PostgreSQL"""
        pass
    
    async def upload_version(
        self, 
        user_id: str, 
        document_id: str, 
        document: Document
    ) -> VersionResult:
        """Upload new version"""
        pass
    
    async def share_with_agent(
        self, 
        user_id: str, 
        document_id: str, 
        session_id: str
    ) -> ShareResult:
        """Share document with automation agent"""
        pass
    
    async def validate_document(self, document: Document) -> ValidationResult:
        """Validate document"""
        pass
    
    async def scan_document(self, document: Document) -> ScanResult:
        """Scan for malware"""
        pass
```
  
  // Retrieve and decrypt document
  getDocument(userId: string, documentId: string): Promise<Document>;
  
  // Preview document without download
  previewDocument(userId: string, documentId: string): Promise<DocumentPreview>;
  
  // Delete document permanently
  deleteDocument(userId: string, documentId: string): Promise<DeletionResult>;
  
  // Organize documents into categories
  categorizeDocument(userId: string, documentId: string, category: string): Promise<void>;
  
  // Get all documents for user
  listDocuments(userId: string, filters?: DocumentFilters): Promise<DocumentSummary[]>;
  
  // Check storage usage
  getStorageUsage(userId: string): Promise<StorageUsage>;
  
  // Archive expired documents
  archiveExpiredDocuments(userId: string): Promise<ArchivedDocument[]>;
  
  // Get audit log
  getAuditLog(userId: string, documentId?: string): Promise<AuditLogEntry[]>;
  
  // Upload new version
  uploadVersion(userId: string, documentId: string, document: Document): Promise<VersionResult>;
  
  // Share document with automation agent
  shareWithAgent(userId: string, documentId: string, sessionId: string): Promise<ShareResult>;
  
  // Validate document
  validateDocument(document: Document): Promise<ValidationResult>;
  
  // Scan for malware
  scanDocument(document: Document): Promise<ScanResult>;
}

interface Document {
  documentId?: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  content: Buffer;
}

interface DocumentMetadata {
  documentType: string;
  category?: string;
  expirationDate?: Date;
  description?: string;
  tags?: string[];
}

interface DocumentPreview {
  documentId: string;
  previewUrl: string;
  thumbnailUrl?: string;
  pageCount?: number;
}

interface DeletionResult {
  success: boolean;
  documentId: string;
  scheduledDeletionDate: Date;
}

interface DocumentFilters {
  category?: string;
  documentType?: string;
  uploadDateRange?: DateRange;
  expirationDateRange?: DateRange;
}

interface DateRange {
  start: Date;
  end: Date;
}

interface ArchivedDocument {
  documentId: string;
  documentName: string;
  archiveDate: Date;
  expirationDate: Date;
}

interface AuditLogEntry {
  timestamp: Date;
  userId: string;
  documentId: string;
  action: AuditAction;
  ipAddress?: string;
  userAgent?: string;
}

interface VersionResult {
  success: boolean;
  documentId: string;
  versionNumber: number;
  previousVersionId: string;
}

interface ShareResult {
  success: boolean;
  documentId: string;
  sessionId: string;
  expiresAt: Date;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

interface ScanResult {
  clean: boolean;
  threats: Threat[];
  scanDate: Date;
}

interface Threat {
  threatType: string;
  severity: SeverityLevel;
  description: string;
}

enum AuditAction {
  UPLOAD = "upload",
  DOWNLOAD = "download",
  PREVIEW = "preview",
  DELETE = "delete",
  SHARE = "share",
  CATEGORIZE = "categorize",
  VERSION_UPLOAD = "version_upload"
}
```

## Data Models

### Core Domain Models

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum

# Aadhaar-specific models
class AadhaarChangeType(str, Enum):
    MINOR_CORRECTION = "minor_correction"
    MAJOR_NAME_CHANGE = "major_name_change"

class AadhaarNameChangeGuide(ServiceGuide):
    change_type: AadhaarChangeType
    correction_vs_change: str
    proof_documents: List[DocumentRequirement]
    biometric_update_required: bool

# Data access request models
class DataAccessType(str, Enum):
    PERSONAL_DATA_ACCESS = "personal_data_access"
    RECORD_VERIFICATION = "record_verification"
    DATA_CORRECTION = "data_correction"

class AdditionalFee(BaseModel):
    description: str
    amount: float
    condition: str

class FeeStructure(BaseModel):
    base_fee: float
    currency: str
    additional_fees: List[AdditionalFee]
    waiver_conditions: List[str]

class DataAccessRequest(BaseModel):
    request_type: DataAccessType
    data_categories: List[str]
    identity_verification_docs: List[DocumentRequirement]
    processing_time: ProcessingTime
    fees: FeeStructure
    legal_basis: str
    user_rights: List[str]

# Service status models
class StatusValue(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    DELAYED = "delayed"

class ServiceStatusModel(BaseModel):
    reference_number: str
    service_id: str
    status: StatusValue
    last_updated: datetime
    estimated_completion: Optional[datetime] = None
    action_required: Optional[RequiredAction] = None
    tracking_url: HttpUrl

# Error and validation models
class ErrorType(str, Enum):
    INVALID_FORMAT = "invalid_format"
    MISSING_REQUIRED = "missing_required"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INVALID_REFERENCE = "invalid_reference"

class ValidationErrorModel(BaseModel):
    field: str
    error_type: ErrorType
    message: str
    suggested_correction: Optional[str] = None

# Multi-language models
class LocalizedContent(BaseModel):
    content_id: str
    language: str
    content: str
    official_terms: Dict[str, str]
    last_updated: datetime

class LanguagePreference(BaseModel):
    primary_language: str
    fallback_language: str
    script_preference: Optional[str] = None
```

### Service Information Currency Models

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Any
from enum import Enum

class ChangeType(str, Enum):
    PROCEDURE_UPDATE = "procedure_update"
    REQUIREMENT_CHANGE = "requirement_change"
    PORTAL_CHANGE = "portal_change"
    FEE_UPDATE = "fee_update"
    TIMELINE_UPDATE = "timeline_update"

class ChangeLogEntry(BaseModel):
    date: datetime
    change_type: ChangeType
    description: str
    affected_sections: List[str]

class ServiceInformation(BaseModel):
    service_id: str
    content: Any
    last_updated: datetime
    last_verified: datetime
    source: str
    version: str
    change_log: List[ChangeLogEntry]

class CurrencyCheck(BaseModel):
    check_date: datetime
    is_current_procedure: bool
    verification_advice: str
    official_source_url: HttpUrl
```

### Dashboard and User Activity Models

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class ActivityType(str, Enum):
    SERVICE_STARTED = "service_started"
    SERVICE_COMPLETED = "service_completed"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_ACCESSED = "document_accessed"
    AUTOMATION_STARTED = "automation_started"
    AUTOMATION_COMPLETED = "automation_completed"
    LOGIN = "login"
    LOGOUT = "logout"

class UserActivity(BaseModel):
    user_id: str
    activity_type: ActivityType
    timestamp: datetime
    service_id: Optional[str] = None
    document_id: Optional[str] = None
    details: Dict[str, Any]

class LogLevel(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"

class NotificationSettings(BaseModel):
    email_notifications: bool
    push_notifications: bool
    notify_on_status_change: bool
    notify_on_document_expiration: bool
    notify_on_storage_limit: bool

class AutomationPreferences(BaseModel):
    default_mode: ExtensionMode
    auto_resume_on_captcha: bool
    log_detail_level: LogLevel
    confirm_before_submit: bool

class DashboardLayout(BaseModel):
    widget_order: List[str]
    hidden_widgets: List[str]
    refresh_interval: int

class UserPreferences(BaseModel):
    user_id: str
    language: str
    frequent_services: List[str]
    notification_settings: NotificationSettings
    automation_preferences: AutomationPreferences
    dashboard_layout: DashboardLayout
```

### Browser Automation Models

```python
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Any
from enum import Enum

class CheckType(str, Enum):
    ELEMENT_EXISTS = "element_exists"
    VALUE_MATCHES = "value_matches"
    PAGE_LOADED = "page_loaded"
    FORM_VALID = "form_valid"

class ValidationCheck(BaseModel):
    check_type: CheckType
    target_element: str
    expected_value: Optional[Any] = None
    error_message: str

class ErrorHandling(BaseModel):
    retry_attempts: int
    fallback_action: Optional[NavigationAction] = None
    pause_on_error: bool
    notify_user: bool

class WorkflowStep(BaseModel):
    step_number: int
    description: str
    page_url: str
    actions: List[NavigationAction]
    validation_checks: List[ValidationCheck]
    captcha_possible: bool
    error_handling: ErrorHandling

class WorkflowDefinition(BaseModel):
    workflow_id: str
    service_id: str
    portal_url: HttpUrl
    steps: List[WorkflowStep]
    estimated_duration: int
    required_documents: List[str]
    required_data: List[str]

class DataSource(str, Enum):
    USER_PROFILE = "user_profile"
    STORED_DOCUMENT = "stored_document"
    SERVICE_DATA = "service_data"
    MANUAL_INPUT = "manual_input"

class TransformationType(str, Enum):
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    DATE_FORMAT = "date_format"
    PHONE_FORMAT = "phone_format"
    TRIM = "trim"

class FieldMapping(BaseModel):
    form_field_id: str
    form_field_name: str
    data_source: DataSource
    data_field: str
    transformation: Optional[TransformationType] = None
    validation_rule: Optional[ValidationRule] = None

class DocumentMapping(BaseModel):
    form_field_id: str
    document_type: str
    required: bool
    accepted_formats: List[str]

class FormMapping(BaseModel):
    service_id: str
    portal_url: HttpUrl
    field_mappings: List[FieldMapping]
    document_mappings: List[DocumentMapping]
```

### Document Storage Models

```python
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
from enum import Enum

class EncryptedDocumentMetadata(BaseModel):
    document_type: str
    file_name: str
    file_size: int
    file_type: str
    category: str
    upload_date: datetime
    expiration_date: Optional[date] = None
    version: int
    previous_version_id: Optional[str] = None
    checksum: str
    tags: List[str]

class EncryptedDocument(BaseModel):
    document_id: str
    user_id: str
    encrypted_content: bytes
    encryption_algorithm: str
    iv: bytes
    metadata: EncryptedDocumentMetadata

class EncryptionKey(BaseModel):
    user_id: str
    key_id: str
    encrypted_key: bytes
    algorithm: str
    created_at: datetime
    rotated_at: Optional[datetime] = None

class DocumentCategory(BaseModel):
    category_id: str
    category_name: str
    description: str
    icon: Optional[str] = None
    color: Optional[str] = None
    document_count: int

class StorageQuota(BaseModel):
    user_id: str
    total_bytes: int
    used_bytes: int
    document_count: int
    last_updated: datetime
    warning_threshold: int
    limit_reached: bool
```

### Browser Extension Models

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

class GuidanceState(BaseModel):
    portal_url: HttpUrl
    service_id: str
    workflow_id: str
    current_step: int
    total_steps: int
    mode: ExtensionMode
    guidance_enabled: bool
    last_updated: datetime

class FieldGuidance(BaseModel):
    field_id: str
    field_name: str
    guidance: str
    example: Optional[str] = None
    validation_rules: List[str]
    common_errors: List[str]
    help_url: Optional[HttpUrl] = None

class SelectorMap(BaseModel):
    form_fields: Dict[str, str]
    buttons: Dict[str, str]
    navigation_elements: Dict[str, str]
    error_messages: Dict[str, str]

class PortalConfiguration(BaseModel):
    portal_url: HttpUrl
    portal_name: str
    supported: bool
    available_services: List[str]
    selectors: SelectorMap
    guidance_enabled: bool
```
  guidanceEnabled: boolean;
  lastUpdated: Date;
}

interface FieldGuidance {
  fieldId: string;
  fieldName: string;
  guidance: string;
  example?: string;
  validationRules: string[];
  commonErrors: string[];
  helpUrl?: string;
}

interface PortalConfiguration {
  portalUrl: string;
  portalName: string;
  supported: boolean;
  availableServices: string[];
  selectors: SelectorMap;
  guidanceEnabled: boolean;
}

interface SelectorMap {
  formFields: Map<string, string>;
  buttons: Map<string, string>;
  navigationElements: Map<string, string>;
  errorMessages: Map<string, string>;
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Complete Service Guide Provision

*For any* service request (Aadhaar name change, government service modification, or data access), the system SHALL return a complete Service_Guide containing all required elements: steps, document requirements, eligibility criteria, processing time, portal links, and contact information.

**Validates: Requirements 1.1, 2.1, 3.1**

### Property 2: Complete Document Requirements

*For any* service type, when document requirements are requested or provided as part of guidance, the system SHALL return the complete set of required documents with all specifications including: original vs copy requirements, attestation/notarization needs, format requirements, validity periods, obtainment guidance, and acceptable alternatives.

**Validates: Requirements 1.2, 2.2, 3.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7**

### Property 3: Eligibility Criteria Presentation

*For any* service inquiry, the system SHALL present complete eligibility criteria and generate appropriate clarifying questions to assess user eligibility.

**Validates: Requirements 1.3, 4.1, 4.2**

### Property 4: Official Portal Links

*For any* service guidance, the system SHALL include valid URLs to official government portals for service submission, status tracking, and verification.

**Validates: Requirements 1.4, 3.7, 5.3, 9.5**

### Property 5: Processing Timeline Information

*For any* service that has processing time information, when requested or as part of complete guidance, the system SHALL provide estimated timelines including minimum, maximum, and typical processing durations.

**Validates: Requirements 1.5, 3.4**

### Property 6: Service Type Distinctions

*For any* service with multiple types or options (such as minor corrections vs major name changes), the system SHALL explain the differences between the types and their respective requirements.

**Validates: Requirements 1.6, 2.4**

### Property 7: Missing Information Identification

*For any* incomplete request or information set, the system SHALL identify and list the specific missing elements required to proceed.

**Validates: Requirements 1.7, 8.5**

### Property 8: Step-by-Step Process Explanation

*For any* service modification request, the system SHALL provide ordered, sequential steps with clear indication of which steps require in-person visits and which can be completed online.

**Validates: Requirements 2.3, 2.6, 2.7**

### Property 9: Contact Information Provision

*For any* service guidance, the system SHALL include relevant contact information for government offices and support channels.

**Validates: Requirements 2.5, 5.5**

### Property 10: Data Type and Rights Explanation

*For any* data access request, the system SHALL explain available data categories and user rights under data protection and privacy laws.

**Validates: Requirements 3.2, 3.6**

### Property 11: Fee Disclosure

*For any* service that requires fees, the system SHALL inform users of all applicable charges including base fees, additional fees, and waiver conditions.

**Validates: Requirements 3.5**

### Property 12: Eligibility Confirmation and Failure Explanation

*For any* eligibility assessment, when criteria are met the system SHALL confirm eligibility, and when criteria are not met the system SHALL explain which specific criteria failed and why.

**Validates: Requirements 4.3, 4.4**

### Property 13: Alternative Service Suggestions

*For any* situation where a user is ineligible or a service is unavailable or non-existent, the system SHALL suggest relevant alternative services when alternatives exist.

**Validates: Requirements 4.5, 8.4, 8.6**

### Property 14: Appeal Process Guidance

*For any* service with appeal options, when eligibility is denied, the system SHALL provide guidance on how to appeal the decision.

**Validates: Requirements 4.6**

### Property 15: Status Interpretation Guidance

*For any* service status inquiry, the system SHALL provide guidance on checking status and explain the meaning of different status values including reasons for delays when applicable.

**Validates: Requirements 5.1, 5.2, 5.4**

### Property 16: Required Action Identification

*For any* service status that requires additional user action, the system SHALL clearly identify what action is needed and provide instructions.

**Validates: Requirements 5.6**

### Property 17: Language-Specific Response

*For any* user request with a specified language preference, the system SHALL provide the complete response in that language while maintaining consistent terminology and preserving official terms.

**Validates: Requirements 7.1, 7.3, 7.5**

### Property 18: Official Language Support

*For any* official government-recognized language, the system SHALL support providing guidance in that language.

**Validates: Requirements 7.2**

### Property 19: Technical Term Explanation

*For any* technical term that lacks a direct translation in the target language, the system SHALL provide an explanation in the user's preferred language while preserving the official terminology.

**Validates: Requirements 7.4**

### Property 20: Invalid Input Explanation

*For any* invalid user input, the system SHALL generate an error message that explains what is invalid, why it is invalid, and suggests corrections for common errors.

**Validates: Requirements 8.1, 8.2**

### Property 21: Ambiguity Resolution

*For any* ambiguous user request, the system SHALL generate clarifying questions to resolve the ambiguity before proceeding.

**Validates: Requirements 8.3**

### Property 22: Information Currency Indicators

*For any* service information provided, the system SHALL include the last update date and advise users to verify with official portals when appropriate.

**Validates: Requirements 9.3, 9.4**

### Property 23: Session-Bounded Data Storage

*For any* personally identifiable information collected during a session, the system SHALL ensure no PII persists in storage after the session ends.

**Validates: Requirements 10.1**

### Property 24: Sensitive Data Warnings

*For any* user input containing sensitive information (Aadhaar number, personal name, address, etc.), the system SHALL generate and display appropriate security warnings.

**Validates: Requirements 10.2**

### Property 25: Data Minimization

*For any* information request made by the system, the requested information SHALL be necessary for providing the specific guidance being offered.

**Validates: Requirements 10.3**

### Property 26: Portal Direction and Disclaimers

*For any* service guidance provided, the system SHALL include direction to official portals for actual application submission and clearly state that it provides guidance only and does not process actual requests.

**Validates: Requirements 10.4, 10.5**

### Property 27: Link Verification Advice

*For any* response containing URLs or links, the system SHALL include advice to verify link authenticity before entering personal data.

**Validates: Requirements 10.6**

## Error Handling

### Error Categories

The system handles the following error categories:

**Input Validation Errors**
- Invalid format (e.g., malformed reference numbers, invalid dates)
- Missing required information
- Out-of-range values
- Type mismatches

**Request Processing Errors**
- Ambiguous requests requiring clarification
- Non-existent service requests
- Unavailable service requests
- Incomplete information sets

**System Errors**
- Service knowledge base unavailable
- Translation service failures
- Session management errors
- External portal connectivity issues

### Error Handling Strategies

**Validation Errors**
```typescript
interface ValidationErrorHandler {
  // Validate input and generate helpful error messages
  validateInput(input: any, validationRule: ValidationRule): ValidationResult;
  
  // Suggest corrections for common mistakes
  suggestCorrection(error: ValidationError): string[];
  
  // Generate user-friendly error messages
  formatErrorMessage(error: ValidationError, language: string): string;
}

interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}
```

**Ambiguity Resolution**
```typescript
interface AmbiguityHandler {
  // Detect ambiguous requests
  detectAmbiguity(request: UserRequest): AmbiguityDetection;
  
  // Generate clarifying questions
  generateClarifyingQuestions(ambiguity: AmbiguityDetection): Question[];
  
  // Resolve ambiguity based on user responses
  resolveAmbiguity(responses: Map<string, any>): ResolvedRequest;
}

interface AmbiguityDetection {
  isAmbiguous: boolean;
  ambiguityType: AmbiguityType;
  possibleInterpretations: Interpretation[];
  clarificationNeeded: string[];
}

enum AmbiguityType {
  MULTIPLE_SERVICES = "multiple_services",
  UNCLEAR_INTENT = "unclear_intent",
  MISSING_CONTEXT = "missing_context",
  CONFLICTING_INFORMATION = "conflicting_information"
}
```

**Service Unavailability**
```typescript
interface UnavailabilityHandler {
  // Handle unavailable services
  handleUnavailableService(serviceId: string): UnavailabilityResponse;
  
  // Find alternative services
  findAlternatives(serviceId: string, userContext: any): AlternativeService[];
  
  // Explain unavailability reasons
  explainUnavailability(serviceId: string): string;
}

interface UnavailabilityResponse {
  reason: UnavailabilityReason;
  explanation: string;
  alternatives: AlternativeService[];
  estimatedAvailability?: Date;
}

enum UnavailabilityReason {
  TEMPORARILY_OFFLINE = "temporarily_offline",
  PERMANENTLY_DISCONTINUED = "permanently_discontinued",
  REGION_RESTRICTED = "region_restricted",
  MAINTENANCE = "maintenance"
}
```

**Graceful Degradation**

When system components fail, the assistant degrades gracefully:

1. **Translation Service Failure**: Fall back to English with apology message
2. **Knowledge Base Partial Failure**: Provide available information with disclaimer about completeness
3. **Portal Link Unavailability**: Provide service information without links and suggest manual search
4. **Session Storage Failure**: Continue with stateless operation and warn user about limited context

### Error Response Format

All error responses follow a consistent structure:

```typescript
interface ErrorResponse {
  errorType: ErrorType;
  message: string;
  explanation: string;
  suggestedActions: string[];
  alternatives?: AlternativeOption[];
  helpfulLinks?: string[];
  canRetry: boolean;
}
```

## Testing Strategy

### Dual Testing Approach

The Government Services Assistant requires both unit testing and property-based testing to ensure comprehensive correctness:

**Unit Tests** focus on:
- Specific examples of service guidance (e.g., Aadhaar name change with specific documents)
- Edge cases (e.g., services with no alternatives, expired documents)
- Error conditions (e.g., invalid reference numbers, unsupported languages)
- Integration points (e.g., session management, privacy controls)
- Specific data transformations (e.g., terminology translation for specific terms)

**Property-Based Tests** focus on:
- Universal properties that hold across all services and inputs
- Comprehensive input coverage through randomization
- Invariants that must be maintained (e.g., no PII after session end)
- Consistency across languages and service types

### Property-Based Testing Configuration

**Framework Selection**: Use `Hypothesis` for Python property-based testing

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with reference to design document property
- Tag format: `Feature: government-services-assistant, Property {number}: {property_text}`

**Example Property Test Structure**:

```python
from hypothesis import given, strategies as st
import pytest

# Feature: government-services-assistant, Property 1: Complete Service Guide Provision
@pytest.mark.property_test
@given(
    service_type=st.sampled_from(['aadhaar_name_change', 'data_access', 'record_modification']),
    language=st.sampled_from(['en', 'hi', 'ta', 'te'])
)
async def test_complete_service_guide_provision(service_type: str, language: str):
    """
    Property 1: For any service request, the system SHALL return a complete 
    Service_Guide with all required elements
    """
    request = create_service_request(service_type, language)
    response = await agent.process_request(request, session)
    
    # Verify complete service guide
    assert response.service_guide is not None
    assert len(response.service_guide.steps) > 0
    assert response.service_guide.document_requirements is not None
    assert response.service_guide.eligibility_criteria is not None
    assert response.service_guide.processing_time is not None
    assert response.service_guide.official_portal_url.startswith('https://')
    assert response.service_guide.contact_info is not None


# Feature: government-services-assistant, Property 23: Session-Bounded Data Storage
@pytest.mark.property_test
@given(
    pii_data=st.fixed_dictionaries({
        'aadhaar_number': st.text(alphabet=st.characters(whitelist_categories=('Nd',)), min_size=12, max_size=12),
        'name': st.text(min_size=1, max_size=100),
        'address': st.text(min_size=1, max_size=200)
    })
)
async def test_session_bounded_data_storage(pii_data: dict):
    """
    Property 23: For any personally identifiable information collected during 
    a session, the system SHALL ensure no PII persists in storage after the 
    session ends
    """
    session = await session_manager.create_session('user123', 'en')
    
    # Simulate user providing PII during session
    await session_manager.update_context(session.session_id, 'user_info', pii_data)
    
    # End session
    await session_manager.end_session(session.session_id)
    
    # Verify no PII persists in Redis or PostgreSQL
    redis_data = await redis_client.get(f"session:{session.session_id}")
    assert redis_data is None
    
    # Check PostgreSQL for any leaked PII
    db_records = await db.execute(
        "SELECT * FROM sessions WHERE session_id = :sid",
        {"sid": session.session_id}
    )
    assert len(db_records) == 0 or all(
        pii_data['aadhaar_number'] not in str(record) and
        pii_data['name'] not in str(record) and
        pii_data['address'] not in str(record)
        for record in db_records
    )
```

### Test Data Generators

Property-based tests require generators for domain objects:

```python
from hypothesis import strategies as st
from datetime import datetime, timedelta

# Service request generator
service_request_strategy = st.fixed_dictionaries({
    'service_id': st.sampled_from([
        'aadhaar_name_change',
        'passport_renewal',
        'data_access_request'
    ]),
    'language': st.sampled_from(['en', 'hi', 'ta', 'te', 'bn', 'mr']),
    'user_context': st.fixed_dictionaries({
        'has_documents': st.booleans(),
        'eligibility_answers': st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(min_size=1, max_size=100)
        )
    })
})

# Document requirement generator
document_requirement_strategy = st.builds(
    DocumentRequirement,
    document_id=st.uuids().map(str),
    document_name=st.text(min_size=1, max_size=100),
    official_name=st.text(min_size=1, max_size=100),
    required=st.booleans(),
    accepts_copies=st.booleans(),
    requires_attestation=st.booleans(),
    requires_notarization=st.booleans(),
    validity_period=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    alternatives=st.lists(st.builds(AlternativeDocument)),
    obtainment_guidance=st.text(min_size=1, max_size=500)
)

# PII data generator
pii_data_strategy = st.fixed_dictionaries({
    'aadhaar_number': st.text(
        alphabet=st.characters(whitelist_categories=('Nd',)), 
        min_size=12, 
        max_size=12
    ),
    'name': st.text(min_size=1, max_size=100),
    'address': st.text(min_size=1, max_size=200),
    'phone_number': st.text(
        alphabet=st.characters(whitelist_categories=('Nd',)), 
        min_size=10, 
        max_size=10
    )
})
```

### Unit Test Coverage

Unit tests should cover:

1. **Specific Service Examples**
   - Aadhaar name change with gazette notification
   - Data access request with fee waiver
   - Service status check with delayed status

2. **Edge Cases**
   - Service with no alternatives available
   - Document with no acceptable alternatives
   - Language with limited terminology database
   - Service with zero processing time (instant)

3. **Error Conditions**
   - Invalid Aadhaar number format
   - Non-existent service ID
   - Unsupported language code
   - Malformed reference number
   - Session timeout scenarios
   - Database connection failures
   - Redis unavailability

4. **Integration Tests**
   - FastAPI endpoint testing with TestClient
   - PostgreSQL transaction handling
   - Redis session management
   - Gemini API integration
   - WebSocket connections
   - Document encryption/decryption
   - Multi-language consistency
   - Portal link validation

5. **API Tests**
   ```python
   from fastapi.testclient import TestClient
   from app.main import app
   
   client = TestClient(app)
   
   def test_chat_endpoint():
       response = client.post(
           "/api/v1/chat",
           json={
               "message": "How do I change my Aadhaar name?",
               "language": "en",
               "session_id": "test-session-123"
           }
       )
       assert response.status_code == 200
       assert "service_guide" in response.json()
   
   def test_document_upload():
       with open("test_document.pdf", "rb") as f:
           response = client.post(
               "/api/v1/documents/upload",
               files={"file": f},
               data={"document_type": "aadhaar", "category": "identity"}
           )
       assert response.status_code == 200
       assert "document_id" in response.json()
   ```

### Test Coverage Goals

- Unit test coverage: >80% of code paths
- Property test coverage: All 27 correctness properties
- Integration test coverage: All component interfaces
- Error handling coverage: All error types and recovery paths
- API endpoint coverage: 100% of REST endpoints

### Continuous Testing

- Run unit tests on every commit using pytest
- Run property tests (with reduced iterations) on every commit
- Run full property test suite (100+ iterations) nightly
- Monitor test execution time and optimize slow tests
- Track property test failure patterns to identify edge cases
- Use pytest-asyncio for async test support
- Use pytest-cov for coverage reporting

### Docker Test Environment

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  test-db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
  
  test-redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
  
  test-api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://test_user:test_pass@test-db:5432/test_db
      REDIS_URL: redis://test-redis:6379
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    depends_on:
      - test-db
      - test-redis
    command: pytest tests/ -v --cov=app
```

