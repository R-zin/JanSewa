"""
AWS Textract OCR Engine

Provides OCR capabilities using AWS Textract for production-grade
document text extraction with higher accuracy than Tesseract.
"""

import boto3
import logging
from typing import Dict, Any, List, Optional, Tuple
from botocore.exceptions import ClientError
import time
from PIL import Image
import io

logger = logging.getLogger(__name__)


class TextractOCREngine:
    """OCR engine using AWS Textract for document text extraction"""
    
    def __init__(self, region_name: str = "ap-south-1"):
        """
        Initialize Textract OCR engine
        
        Args:
            region_name: AWS region (default: ap-south-1 for Mumbai)
        """
        self.textract_client = boto3.client('textract', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.supported_languages = ['eng', 'hin', 'tam', 'tel', 'auto']
        
        # Textract supports these languages natively
        self.language_map = {
            'eng': 'en',
            'hin': 'hi',
            'tam': 'ta',
            'tel': 'te',
            'auto': None  # Auto-detect
        }
    
    def extract_text(
        self,
        image_data: bytes,
        language: str = 'eng',
        use_async: bool = False
    ) -> Tuple[str, float]:
        """
        Extract text from image using AWS Textract
        
        Args:
            image_data: Image bytes
            language: Language code (eng, hin, tam, tel, auto)
            use_async: Use asynchronous processing for large documents
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            if use_async:
                return self._extract_text_async(image_data, language)
            else:
                return self._extract_text_sync(image_data, language)
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Textract API error: {error_code} - {e}")
            
            if error_code == 'ProvisionedThroughputExceededException':
                # Retry with exponential backoff
                time.sleep(2)
                return self.extract_text(image_data, language, use_async)
            
            raise Exception(f"Textract extraction failed: {error_code}")
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0
    
    def _extract_text_sync(
        self,
        image_data: bytes,
        language: str
    ) -> Tuple[str, float]:
        """
        Synchronous text extraction (for documents < 5MB)
        
        Args:
            image_data: Image bytes
            language: Language code
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        # Prepare request
        request_params = {
            'Document': {'Bytes': image_data}
        }
        
        # Add language hint if specified
        if language != 'auto' and language in self.language_map:
            lang_code = self.language_map[language]
            if lang_code:
                request_params['QueriesConfig'] = {
                    'Queries': []  # Can add specific queries if needed
                }
        
        # Call Textract DetectDocumentText API
        response = self.textract_client.detect_document_text(**request_params)
        
        # Extract text and confidence
        text_blocks = []
        confidences = []
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append(block.get('Text', ''))
                confidences.append(block.get('Confidence', 0))
        
        # Combine text
        full_text = '\n'.join(text_blocks)
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        logger.info(f"Textract sync extraction completed with confidence: {avg_confidence}")
        return full_text, avg_confidence / 100.0
    
    def _extract_text_async(
        self,
        image_data: bytes,
        language: str
    ) -> Tuple[str, float]:
        """
        Asynchronous text extraction (for large documents)
        
        Args:
            image_data: Image bytes
            language: Language code
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        # For async processing, document must be in S3
        # This is a simplified implementation
        raise NotImplementedError("Async processing requires S3 integration")
    
    def extract_text_from_s3(
        self,
        bucket_name: str,
        object_key: str,
        language: str = 'eng'
    ) -> Tuple[str, float]:
        """
        Extract text from document stored in S3 (supports async processing)
        
        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            language: Language code
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            # Start async job
            response = self.textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")
            
            # Poll for completion
            max_attempts = 60  # 5 minutes max
            attempt = 0
            
            while attempt < max_attempts:
                time.sleep(5)  # Wait 5 seconds between polls
                
                result = self.textract_client.get_document_text_detection(
                    JobId=job_id
                )
                
                status = result['JobStatus']
                
                if status == 'SUCCEEDED':
                    # Extract text from result
                    text_blocks = []
                    confidences = []
                    
                    for block in result.get('Blocks', []):
                        if block['BlockType'] == 'LINE':
                            text_blocks.append(block.get('Text', ''))
                            confidences.append(block.get('Confidence', 0))
                    
                    # Handle pagination if needed
                    next_token = result.get('NextToken')
                    while next_token:
                        result = self.textract_client.get_document_text_detection(
                            JobId=job_id,
                            NextToken=next_token
                        )
                        
                        for block in result.get('Blocks', []):
                            if block['BlockType'] == 'LINE':
                                text_blocks.append(block.get('Text', ''))
                                confidences.append(block.get('Confidence', 0))
                        
                        next_token = result.get('NextToken')
                    
                    full_text = '\n'.join(text_blocks)
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    logger.info(f"Textract async extraction completed with confidence: {avg_confidence}")
                    return full_text, avg_confidence / 100.0
                
                elif status == 'FAILED':
                    error_msg = result.get('StatusMessage', 'Unknown error')
                    raise Exception(f"Textract job failed: {error_msg}")
                
                attempt += 1
            
            raise Exception("Textract job timed out")
            
        except Exception as e:
            logger.error(f"Textract S3 extraction failed: {e}")
            raise
    
    def analyze_document(
        self,
        image_data: bytes,
        feature_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document with advanced features (forms, tables, etc.)
        
        Args:
            image_data: Image bytes
            feature_types: List of features to extract (FORMS, TABLES, QUERIES)
            
        Returns:
            Structured analysis result
        """
        if feature_types is None:
            feature_types = ['FORMS', 'TABLES']
        
        try:
            response = self.textract_client.analyze_document(
                Document={'Bytes': image_data},
                FeatureTypes=feature_types
            )
            
            result = {
                'text': '',
                'forms': [],
                'tables': [],
                'confidence': 0.0
            }
            
            text_blocks = []
            confidences = []
            key_value_pairs = {}
            current_key = None
            
            for block in response.get('Blocks', []):
                block_type = block['BlockType']
                
                # Extract text
                if block_type == 'LINE':
                    text_blocks.append(block.get('Text', ''))
                    confidences.append(block.get('Confidence', 0))
                
                # Extract form fields (key-value pairs)
                elif block_type == 'KEY_VALUE_SET':
                    entity_types = block.get('EntityTypes', [])
                    
                    if 'KEY' in entity_types:
                        # Extract key text
                        key_text = self._get_text_from_relationships(
                            block, response.get('Blocks', [])
                        )
                        current_key = key_text
                    
                    elif 'VALUE' in entity_types and current_key:
                        # Extract value text
                        value_text = self._get_text_from_relationships(
                            block, response.get('Blocks', [])
                        )
                        key_value_pairs[current_key] = value_text
                        result['forms'].append({
                            'key': current_key,
                            'value': value_text,
                            'confidence': block.get('Confidence', 0) / 100.0
                        })
                        current_key = None
                
                # Extract tables
                elif block_type == 'TABLE':
                    table_data = self._extract_table(block, response.get('Blocks', []))
                    result['tables'].append(table_data)
            
            result['text'] = '\n'.join(text_blocks)
            result['confidence'] = sum(confidences) / len(confidences) / 100.0 if confidences else 0
            
            logger.info(f"Document analysis completed with {len(result['forms'])} forms and {len(result['tables'])} tables")
            return result
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise
    
    def _get_text_from_relationships(
        self,
        block: Dict,
        all_blocks: List[Dict]
    ) -> str:
        """
        Extract text from block relationships
        
        Args:
            block: Current block
            all_blocks: All blocks in response
            
        Returns:
            Extracted text
        """
        text_parts = []
        
        relationships = block.get('Relationships', [])
        for relationship in relationships:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship.get('Ids', []):
                    # Find child block
                    child_block = next(
                        (b for b in all_blocks if b['Id'] == child_id),
                        None
                    )
                    if child_block and child_block['BlockType'] == 'WORD':
                        text_parts.append(child_block.get('Text', ''))
        
        return ' '.join(text_parts)
    
    def _extract_table(
        self,
        table_block: Dict,
        all_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """
        Extract table structure from Textract response
        
        Args:
            table_block: Table block
            all_blocks: All blocks in response
            
        Returns:
            Structured table data
        """
        rows = {}
        
        relationships = table_block.get('Relationships', [])
        for relationship in relationships:
            if relationship['Type'] == 'CHILD':
                for cell_id in relationship.get('Ids', []):
                    cell_block = next(
                        (b for b in all_blocks if b['Id'] == cell_id),
                        None
                    )
                    
                    if cell_block and cell_block['BlockType'] == 'CELL':
                        row_index = cell_block.get('RowIndex', 0)
                        col_index = cell_block.get('ColumnIndex', 0)
                        
                        if row_index not in rows:
                            rows[row_index] = {}
                        
                        cell_text = self._get_text_from_relationships(cell_block, all_blocks)
                        rows[row_index][col_index] = cell_text
        
        # Convert to list of lists
        table_data = []
        for row_idx in sorted(rows.keys()):
            row = rows[row_idx]
            row_data = [row.get(col_idx, '') for col_idx in sorted(row.keys())]
            table_data.append(row_data)
        
        return {
            'rows': len(table_data),
            'columns': len(table_data[0]) if table_data else 0,
            'data': table_data,
            'confidence': table_block.get('Confidence', 0) / 100.0
        }
    
    def extract_identity_document(
        self,
        image_data: bytes
    ) -> Dict[str, Any]:
        """
        Extract data from identity documents (Aadhaar, PAN, etc.)
        Uses Textract's AnalyzeID API
        
        Args:
            image_data: Image bytes
            
        Returns:
            Structured identity document data
        """
        try:
            response = self.textract_client.analyze_id(
                DocumentPages=[
                    {'Bytes': image_data}
                ]
            )
            
            result = {
                'document_type': '',
                'fields': {},
                'confidence': 0.0
            }
            
            confidences = []
            
            for document in response.get('IdentityDocuments', []):
                # Get document type
                doc_type = document.get('IdentityDocumentFields', [])
                
                for field in doc_type:
                    field_type = field.get('Type', {}).get('Text', '')
                    field_value = field.get('ValueDetection', {}).get('Text', '')
                    field_confidence = field.get('ValueDetection', {}).get('Confidence', 0)
                    
                    result['fields'][field_type] = {
                        'value': field_value,
                        'confidence': field_confidence / 100.0
                    }
                    confidences.append(field_confidence)
            
            result['confidence'] = sum(confidences) / len(confidences) / 100.0 if confidences else 0
            
            logger.info(f"Identity document extraction completed with {len(result['fields'])} fields")
            return result
            
        except Exception as e:
            logger.error(f"Identity document extraction failed: {e}")
            raise
    
    def check_image_quality(self, image_data: bytes) -> Dict[str, Any]:
        """
        Check image quality for OCR suitability
        
        Args:
            image_data: Image bytes
            
        Returns:
            Quality assessment
        """
        try:
            # Open image to check basic properties
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            
            # Check resolution
            resolution_ok = height >= 600 and width >= 800
            
            # Check file size (Textract limits)
            size_mb = len(image_data) / (1024 * 1024)
            size_ok = size_mb <= 5  # 5MB limit for sync API
            
            # Estimate quality score
            quality_score = min((width * height) / (1920 * 1080), 1.0)
            
            return {
                "resolution_ok": resolution_ok,
                "size_ok": size_ok,
                "quality_score": quality_score,
                "suitable_for_ocr": resolution_ok and size_ok,
                "width": width,
                "height": height,
                "size_mb": round(size_mb, 2),
                "recommendation": "Use async processing" if size_mb > 5 else "Use sync processing"
            }
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {"suitable_for_ocr": False, "quality_score": 0.0}


# Create singleton instance
textract_ocr_engine = TextractOCREngine()
