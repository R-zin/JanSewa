import pytesseract
from PIL import Image
import cv2
import numpy as np
import io
import logging
from typing import Dict, Any, List, Optional, Tuple

# Optional QR code support
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pyzbar not available - QR code extraction disabled")

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine for extracting text from documents"""
    
    def __init__(self):
        self.supported_languages = ['eng', 'hin', 'tam', 'tel']
    
    def preprocess_image(self, image_data: bytes) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        # Convert bytes to image
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Deskew (simplified)
        thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        return thresh
    
    def extract_text(
        self,
        image_data: bytes,
        language: str = 'eng'
    ) -> Tuple[str, float]:
        """Extract text from image using OCR"""
        try:
            # Preprocess
            processed_img = self.preprocess_image(image_data)
            
            # Perform OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(
                processed_img,
                lang=language,
                config=custom_config
            )
            
            # Get confidence (simplified)
            data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            logger.info(f"OCR completed with confidence: {avg_confidence}")
            return text, avg_confidence / 100.0
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0
    
    def extract_qr_code(self, image_data: bytes) -> Optional[str]:
        """Extract data from QR code"""
        if not PYZBAR_AVAILABLE:
            logger.warning("QR code extraction requires pyzbar library")
            return None
            
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            decoded_objects = pyzbar.decode(img)
            
            if decoded_objects:
                qr_data = decoded_objects[0].data.decode('utf-8')
                logger.info("QR code extracted successfully")
                return qr_data
            
            return None
        except Exception as e:
            logger.error(f"QR code extraction failed: {e}")
            return None
    
    def check_image_quality(self, image_data: bytes) -> Dict[str, Any]:
        """Check image quality for OCR suitability"""
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Check resolution
            height, width = img.shape[:2]
            resolution_ok = height >= 600 and width >= 800
            
            # Check blur (Laplacian variance)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_ok = blur_score > 100
            
            return {
                "resolution_ok": resolution_ok,
                "blur_ok": blur_ok,
                "quality_score": min(blur_score / 500, 1.0),
                "suitable_for_ocr": resolution_ok and blur_ok
            }
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {"suitable_for_ocr": False, "quality_score": 0.0}


ocr_engine = OCREngine()
