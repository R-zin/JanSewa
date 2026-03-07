"""
Scheduled task for checking document expirations and archiving expired documents
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.services.document_storage import document_storage

logger = logging.getLogger(__name__)


class ExpirationScheduler:
    """Scheduler for document expiration checks and archival"""
    
    def __init__(self):
        self.check_interval_hours = 24  # Check daily
        self.is_running = False
    
    async def check_and_process_expirations(self, get_all_documents_func) -> Dict[str, Any]:
        """
        Check all documents for expiration and process archival
        
        Args:
            get_all_documents_func: Function to retrieve all documents from database
                                   Should return List[Dict[str, Any]] with document data
        
        Returns:
            Dict with processing results
        """
        try:
            logger.info("Starting document expiration check")
            
            # Get all documents from database
            documents = await get_all_documents_func()
            
            # Process expired documents for archival
            result = await document_storage.process_expired_documents(documents)
            
            # Generate warnings for expiring documents
            warnings = document_storage.get_expiration_warnings(documents)
            
            logger.info(
                f"Expiration check complete: {result['archived_count']} archived, "
                f"{len(warnings)} warnings generated"
            )
            
            return {
                **result,
                "warnings_count": len(warnings),
                "warnings": [w.to_dict() for w in warnings],
                "check_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during expiration check: {str(e)}")
            return {
                "error": str(e),
                "archived_count": 0,
                "failed_count": 0,
                "warnings_count": 0
            }
    
    async def run_scheduled_checks(self, get_all_documents_func):
        """
        Run scheduled expiration checks in a loop
        
        Args:
            get_all_documents_func: Function to retrieve all documents from database
        """
        self.is_running = True
        logger.info(f"Starting expiration scheduler (interval: {self.check_interval_hours}h)")
        
        while self.is_running:
            try:
                await self.check_and_process_expirations(get_all_documents_func)
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in scheduled expiration check: {str(e)}")
                # Wait before retrying
                await asyncio.sleep(3600)  # Retry after 1 hour on error
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping expiration scheduler")
        self.is_running = False
    
    async def check_user_document_expirations(
        self,
        user_id: int,
        user_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check expirations for a specific user's documents
        
        Args:
            user_id: User ID
            user_documents: List of user's documents
        
        Returns:
            Dict with expiration status and warnings
        """
        warnings = document_storage.get_expiration_warnings(user_documents)
        
        expired_docs = []
        expiring_soon_docs = []
        
        for doc in user_documents:
            expiration_date = doc.get("expiration_date")
            if not expiration_date:
                continue
            
            status = document_storage.get_document_expiration_status(expiration_date)
            
            if status == "expired":
                expired_docs.append({
                    "document_id": doc.get("id"),
                    "document_name": doc.get("file_name"),
                    "expiration_date": expiration_date.isoformat()
                })
            elif status == "expiring_soon":
                expiring_soon_docs.append({
                    "document_id": doc.get("id"),
                    "document_name": doc.get("file_name"),
                    "expiration_date": expiration_date.isoformat(),
                    "days_until_expiration": document_storage.get_days_until_expiration(expiration_date)
                })
        
        return {
            "user_id": user_id,
            "warnings": [w.to_dict() for w in warnings],
            "expired_documents": expired_docs,
            "expiring_soon_documents": expiring_soon_docs,
            "total_warnings": len(warnings)
        }


# Global scheduler instance
expiration_scheduler = ExpirationScheduler()
