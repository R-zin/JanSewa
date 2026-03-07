"""
Browser Automation with Playwright

Modern, fast, and reliable browser automation using Playwright.
Replaces Selenium with better performance and stability.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import asyncio
from contextlib import asynccontextmanager

from app.models.automation import (
    FormField, NavigationAction, SessionState, WorkflowDefinition
)
from app.services.form_filler import form_filler, FormSummary


class AutomationStatus(str, Enum):
    """Automation session status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, Enum):
    """Types of automation actions"""
    NAVIGATE = "navigate"
    FILL_FIELD = "fill_field"
    CLICK = "click"
    UPLOAD_FILE = "upload_file"
    WAIT = "wait"
    SUBMIT = "submit"


class ActionLog(BaseModel):
    """Log entry for automation action"""
    action_id: str
    action_type: ActionType
    timestamp: datetime
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class PlaywrightSession:
    """Manages a Playwright browser session"""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_initialized = False
    
    async def initialize(self, headless: bool = True):
        """Initialize Playwright browser"""
        if self.is_initialized:
            return
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        self.is_initialized = True
    
    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.is_initialized = False


class AutomationSession(BaseModel):
    """Represents a browser automation session"""
    session_id: str
    user_id: str
    service_id: str
    portal_url: str
    status: AutomationStatus
    current_step: int
    total_steps: int
    workflow: WorkflowDefinition
    session_state: SessionState
    action_logs: List[ActionLog]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PlaywrightBrowserAutomation:
    """
    Modern browser automation using Playwright.
    
    Features:
    - Faster and more reliable than Selenium
    - Better handling of modern web apps
    - Built-in waiting and retry logic
    - Network interception capabilities
    - Better debugging tools
    """
    
    def __init__(self, credential_store=None):
        """Initialize Playwright automation agent"""
        self.sessions: Dict[str, AutomationSession] = {}
        self.playwright_sessions: Dict[str, PlaywrightSession] = {}
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.credential_store = credential_store
        self.pending_otp_sessions: Dict[str, str] = {}
        self.pending_biometric_sessions: Dict[str, str] = {}
        self.form_summaries: Dict[str, FormSummary] = {}
    
    def create_session(
        self,
        user_id: str,
        service_id: str,
        portal_url: str,
        workflow: WorkflowDefinition
    ) -> str:
        """Create a new automation session"""
        session_id = f"pw_{user_id}_{service_id}_{datetime.now().timestamp()}"
        
        session = AutomationSession(
            session_id=session_id,
            user_id=user_id,
            service_id=service_id,
            portal_url=portal_url,
            status=AutomationStatus.IDLE,
            current_step=0,
            total_steps=len(workflow.steps),
            workflow=workflow,
            session_state=SessionState(
                current_url=portal_url,
                current_step=0,
                total_steps=len(workflow.steps),
                form_fields_filled=0,
                total_form_fields=0,
                is_authenticated=False,
                requires_user_action=False,
                user_action_type=None
            ),
            action_logs=[],
            created_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        self.playwright_sessions[session_id] = PlaywrightSession()
        
        return session_id
    
    async def start_session(self, session_id: str, headless: bool = True) -> bool:
        """Start automation session with Playwright"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        pw_session = self.playwright_sessions[session_id]
        
        try:
            # Initialize Playwright
            await pw_session.initialize(headless=headless)
            
            # Navigate to portal
            await pw_session.page.goto(session.portal_url, wait_until='networkidle')
            
            session.status = AutomationStatus.RUNNING
            session.started_at = datetime.now()
            session.session_state.current_url = pw_session.page.url
            
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": session.portal_url},
                True
            )
            
            return True
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": session.portal_url},
                False,
                str(e)
            )
            return False
    
    async def navigate_to(self, session_id: str, url: str, wait_until: str = 'networkidle') -> bool:
        """Navigate to URL using Playwright"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        session = self.sessions[session_id]
        
        try:
            await pw_session.page.goto(url, wait_until=wait_until, timeout=30000)
            session.session_state.current_url = pw_session.page.url
            
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": url, "final_url": pw_session.page.url},
                True
            )
            return True
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.NAVIGATE,
                {"url": url},
                False,
                str(e)
            )
            return False
    
    async def fill_field(
        self,
        session_id: str,
        selector: str,
        value: str,
        field_name: str = ""
    ) -> bool:
        """Fill form field using Playwright"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            # Wait for element to be visible
            await pw_session.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Fill the field
            await pw_session.page.fill(selector, value)
            
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {
                    "selector": selector,
                    "field_name": field_name,
                    "value_length": len(value)
                },
                True
            )
            return True
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.FILL_FIELD,
                {"selector": selector, "field_name": field_name},
                False,
                str(e)
            )
            return False
    
    async def click_element(
        self,
        session_id: str,
        selector: str,
        wait_for_navigation: bool = False
    ) -> bool:
        """Click element using Playwright"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            # Wait for element to be clickable
            await pw_session.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            if wait_for_navigation:
                # Click and wait for navigation
                async with pw_session.page.expect_navigation(wait_until='networkidle'):
                    await pw_session.page.click(selector)
            else:
                await pw_session.page.click(selector)
            
            self._log_action(
                session_id,
                ActionType.CLICK,
                {"selector": selector},
                True
            )
            return True
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.CLICK,
                {"selector": selector},
                False,
                str(e)
            )
            return False
    
    async def upload_file(
        self,
        session_id: str,
        selector: str,
        file_path: str
    ) -> bool:
        """Upload file using Playwright"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            # Wait for file input
            await pw_session.page.wait_for_selector(selector, state='attached', timeout=10000)
            
            # Set input files
            await pw_session.page.set_input_files(selector, file_path)
            
            self._log_action(
                session_id,
                ActionType.UPLOAD_FILE,
                {"selector": selector, "file_path": file_path},
                True
            )
            return True
            
        except Exception as e:
            self._log_action(
                session_id,
                ActionType.UPLOAD_FILE,
                {"selector": selector},
                False,
                str(e)
            )
            return False
    
    async def wait_for_element(
        self,
        session_id: str,
        selector: str,
        state: str = 'visible',
        timeout: int = 30000
    ) -> bool:
        """Wait for element to reach specified state"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            await pw_session.page.wait_for_selector(selector, state=state, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def get_text(self, session_id: str, selector: str) -> Optional[str]:
        """Get text content of element"""
        if session_id not in self.playwright_sessions:
            return None
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            element = await pw_session.page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except Exception:
            return None
    
    async def take_screenshot(
        self,
        session_id: str,
        path: str,
        full_page: bool = False
    ) -> bool:
        """Take screenshot of current page"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            await pw_session.page.screenshot(path=path, full_page=full_page)
            return True
        except Exception:
            return False
    
    async def get_cookies(self, session_id: str) -> List[Dict]:
        """Get all cookies from current context"""
        if session_id not in self.playwright_sessions:
            return []
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            cookies = await pw_session.context.cookies()
            return cookies
        except Exception:
            return []
    
    async def set_cookies(self, session_id: str, cookies: List[Dict]) -> bool:
        """Set cookies in current context"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            await pw_session.context.add_cookies(cookies)
            return True
        except Exception:
            return False
    
    async def evaluate_javascript(
        self,
        session_id: str,
        script: str
    ) -> Any:
        """Execute JavaScript in page context"""
        if session_id not in self.playwright_sessions:
            return None
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            result = await pw_session.page.evaluate(script)
            return result
        except Exception:
            return None
    
    async def close_session(self, session_id: str) -> bool:
        """Close Playwright session and cleanup"""
        if session_id not in self.playwright_sessions:
            return False
        
        pw_session = self.playwright_sessions[session_id]
        
        try:
            await pw_session.close()
            del self.playwright_sessions[session_id]
            
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.status = AutomationStatus.COMPLETED
                session.completed_at = datetime.now()
            
            return True
        except Exception:
            return False
    
    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get current session state"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        pw_session = self.playwright_sessions.get(session_id)
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "current_step": session.current_step,
            "total_steps": session.total_steps,
            "progress_percentage": (session.current_step / session.total_steps * 100) if session.total_steps > 0 else 0,
            "current_url": session.session_state.current_url,
            "browser_initialized": pw_session.is_initialized if pw_session else False,
            "pending_otp": session_id in self.pending_otp_sessions,
            "pending_biometric": session_id in self.pending_biometric_sessions
        }
    
    def _log_action(
        self,
        session_id: str,
        action_type: ActionType,
        details: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log an automation action"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        action_log = ActionLog(
            action_id=f"action_{len(session.action_logs)}",
            action_type=action_type,
            timestamp=datetime.now(),
            details=details,
            success=success,
            error_message=error_message
        )
        
        session.action_logs.append(action_log)
    
    def get_action_logs(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get action logs for session"""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        logs = session.action_logs[-limit:]
        
        return [
            {
                "action_id": log.action_id,
                "action_type": log.action_type,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
                "success": log.success,
                "error": log.error_message
            }
            for log in logs
        ]


# Global instance
playwright_automation = PlaywrightBrowserAutomation()
