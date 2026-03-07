"""
Hybrid OCR Engine

Provides OCR capabilities using both AWS Textract (production) and
Tesseract (fallback/development). Automatically selects the best engine
based on configuration and availability.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from .ocr_engine import OCREngine as TesseractEngine
from .ocr_engine_textract import TextractOCREngine

logger = logging.getLogger(__name__)


class OCREngineType(str, Enum):
    """OCR engine types"""
    TEXTRACT = "textract"
    TESSERACT = "tesseract"
    AUTO = "auto"


class HybridOCREngine:
    """
    Hybrid OCR engine that uses AWS Textract for production
    and falls back to Tesseract for development/testing
    """
    
    def __init__(
        self,
        preferred_engine: OCREngineType = OCREngineType.AUTO,
        aws_region: str = "ap-south-1"
    ):
        """
        Initialize hybrid OCR engine
        
        Args:
            preferred_engine: Preferred engine (textract, tesseract, auto)
            aws_region: AWS region for Textract
        """
        self.preferred_engine = preferred_engine
        self.tesseract_engine = TesseractEngine()
        
        # Try to initialize Textract
        self.textract_available = False
        try:
            self.textract_engine = TextractOCREngine(region_name=aws_region)
            self.textract_available = True
            logger.info("AWS Textract initialized successfully")
        except Exception as e:
            logger.warning(f"AWS Textract not available: {e}. Falling back to Tesseract.")
            self.textract_engine = None
        
        self.supported_languages = ['eng', 'hin', 'tam', 'tel']
    
    def _select_engine(self) -> str:
        """
        Select the appropriate OCR engine
        
        Returns:
            Engine type to use
        """
        if self.preferred_engine == OCREngineType.TESSERACT:
            return "tesseract"
        
        if self.preferred_engine == OCREngineType.TEXTRACT:
            if self.textract_available:
                return "textract"
            else:
                logger.warning("Textract requested but not available, using Tesseract")
                return "tesseract"
        
        # AUTO mode: prefer Textract if available
        if self.textract_available:
            return "textract"
        else:
            return "tesseract"
    
    def extract_text(
        self,
        image_data: bytes,
        language: str = 'eng',
        force_engine: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Extract text from image using the best available engine
        
        Args:
            image_data: Image bytes
            language: Language code (eng, hin, tam, tel)
            force_engine: Force specific engine (textract or tesseract)
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        engine = force_engine if force_engine else self._select_engine()
        
        try:
            if engine == "textract" and self.textract_available:
                logger.info("Using AWS Textract for OCR")
                return self.textract_engine.extract_text(image_data, language)
            else:
                logger.info("Using Tesseract for OCR")
                return self.tesseract_engine.extract_text(image_data, language)
                
        except Exception as e:
            logger.error(f"OCR extraction failed with {engine}: {e}")
            
            # Fallback to alternative engine
            if engine == "textract" and self.tesseract_engine:
                logger.info("Falling back to Tesseract")
                try:
                    return self.tesseract_engine.extract_text(image_data, language)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
            
            return "", 0.0
    
    def extract_text_from_s3(
        self,
        bucket_name: str,
        object_key: str,
        language: str = 'eng'
    ) -> Tuple[str, float]:
        """
        Extract text from document in S3 (Textract only)
        
        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            language: Language code
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self.textract_available:
            raise Exception("S3 extraction requires AWS Textract")
        
        return self.textract_engine.extract_text_from_s3(
            bucket_name, object_key, language
        )
    
    def analyze_document(
        self,
        image_data: bytes,
        feature_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document with advanced features (Textract only)
        
        Args:
            image_data: Image bytes
            feature_types: Features to extract (FORMS, TABLES, QUERIES)
            
        Returns:
            Structured analysis result
        """
        if not self.textract_available:
            raise Exception("Document analysis requires AWS Textract")
        
        return self.textract_engine.analyze_document(image_data, feature_types)
    
    def extract_identity_document(
        self,
        image_data: bytes
    ) -> Dict[str, Any]:
        """
        Extract data from identity documents (Textract only)
        
        Args:
            image_data: Image bytes
            
        Returns:
            Structured identity document data
        """
        if not self.textract_available:
            raise Exception("Identity document extraction requires AWS Textract")
        
        return self.textract_engine.extract_identity_document(image_data)
    
    def extract_qr_code(self, image_data: bytes) -> Optional[str]:
        """
        Extract data from QR code (uses Tesseract engine)
        
        Args:
            image_data: Image bytes
            
        Returns:
            QR code data or None
        """
        return self.tesseract_engine.extract_qr_code(image_data)
    
    def check_image_quality(self, image_data: bytes) -> Dict[str, Any]:
        """
        Check image quality for OCR suitability
        
        Args:
            image_data: Image bytes
            
        Returns:
            Quality assessment
        """
        engine = self._select_engine()
        
        if engine == "textract" and self.textract_available:
            return self.textract_engine.check_image_quality(image_data)
        else:
            return self.tesseract_engine.check_image_quality(image_data)
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about available engines
        
        Returns:
            Engine availability and configuration
        """
        return {
            "preferred_engine": self.preferred_engine,
            "active_engine": self._select_engine(),
            "textract_available": self.textract_available,
            "tesseract_available": True,
            "supported_languages": self.supported_languages,
            "capabilities": {
                "basic_ocr": True,
                "forms_extraction": self.textract_available,
                "tables_extraction": self.textract_available,
                "identity_documents": self.textract_available,
                "s3_integration": self.textract_available,
                "qr_codes": True
            }
        }


# Create singleton instance with AUTO mode
hybrid_ocr_engine = HybridOCREngine(preferred_engine=OCREngineType.AUTO)
