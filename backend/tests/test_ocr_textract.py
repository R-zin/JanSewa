"""
Tests for AWS Textract OCR Integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.ocr_engine_textract import TextractOCREngine
from app.services.ocr_engine_hybrid import HybridOCREngine, OCREngineType


class TestTextractOCREngine:
    """Test AWS Textract OCR engine"""
    
    @patch('app.services.ocr_engine_textract.boto3.client')
    def test_initialization(self, mock_boto_client):
        """Test Textract engine initialization"""
        engine = TextractOCREngine(region_name="ap-south-1")
        
        assert engine.supported_languages == ['eng', 'hin', 'tam', 'tel', 'auto']
        assert 'eng' in engine.language_map
        mock_boto_client.assert_called()
    
    @patch('app.services.ocr_engine_textract.boto3.client')
    def test_extract_text_sync(self, mock_boto_client):
        """Test synchronous text extraction"""
        # Mock Textract response
        mock_textract = MagicMock()
        mock_textract.detect_document_text.return_value = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Sample text line 1',
                    'Confidence': 98.5
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Sample text line 2',
                    'Confidence': 97.2
                }
            ]
        }
        mock_boto_client.return_value = mock_textract
        
        engine = TextractOCREngine()
        image_data = b'fake_image_data'
        
        text, confidence = engine.extract_text(image_data, language='eng')
        
        assert 'Sample text line 1' in text
        assert 'Sample text line 2' in text
        assert confidence > 0.95
        mock_textract.detect_document_text.assert_called_once()
    
    @patch('app.services.ocr_engine_textract.boto3.client')
    def test_analyze_document(self, mock_boto_client):
        """Test document analysis with forms and tables"""
        # Mock Textract response
        mock_textract = MagicMock()
        mock_textract.analyze_document.return_value = {
            'Blocks': [
                {
                    'Id': 'line1',
                    'BlockType': 'LINE',
                    'Text': 'Form data',
                    'Confidence': 95.0
                },
                {
                    'Id': 'kvset1',
                    'BlockType': 'KEY_VALUE_SET',
                    'EntityTypes': ['KEY'],
                    'Confidence': 98.0,
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word1']
                        }
                    ]
                },
                {
                    'Id': 'word1',
                    'BlockType': 'WORD',
                    'Text': 'Name'
                }
            ]
        }
        mock_boto_client.return_value = mock_textract
        
        engine = TextractOCREngine()
        image_data = b'fake_image_data'
        
        result = engine.analyze_document(image_data, ['FORMS'])
        
        assert 'text' in result
        assert 'forms' in result
        assert 'tables' in result
        assert result['confidence'] > 0
        mock_textract.analyze_document.assert_called_once()
    
    @patch('app.services.ocr_engine_textract.boto3.client')
    def test_extract_identity_document(self, mock_boto_client):
        """Test identity document extraction"""
        # Mock Textract AnalyzeID response
        mock_textract = MagicMock()
        mock_textract.analyze_id.return_value = {
            'IdentityDocuments': [
                {
                    'IdentityDocumentFields': [
                        {
                            'Type': {'Text': 'Name'},
                            'ValueDetection': {
                                'Text': 'John Doe',
                                'Confidence': 99.0
                            }
                        },
                        {
                            'Type': {'Text': 'ID Number'},
                            'ValueDetection': {
                                'Text': '1234567890',
                                'Confidence': 98.5
                            }
                        }
                    ]
                }
            ]
        }
        mock_boto_client.return_value = mock_textract
        
        engine = TextractOCREngine()
        image_data = b'fake_aadhaar_image'
        
        result = engine.extract_identity_document(image_data)
        
        assert 'fields' in result
        assert 'Name' in result['fields']
        assert result['fields']['Name']['value'] == 'John Doe'
        assert result['fields']['Name']['confidence'] > 0.98
        mock_textract.analyze_id.assert_called_once()
    
    @patch('app.services.ocr_engine_textract.boto3.client')
    def test_check_image_quality(self, mock_boto_client):
        """Test image quality check"""
        from PIL import Image
        import io
        
        # Create a test image
        img = Image.new('RGB', (1920, 1080), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        image_data = img_bytes.getvalue()
        
        engine = TextractOCREngine()
        quality = engine.check_image_quality(image_data)
        
        assert 'resolution_ok' in quality
        assert 'size_ok' in quality
        assert 'suitable_for_ocr' in quality
        assert quality['width'] == 1920
        assert quality['height'] == 1080


class TestHybridOCREngine:
    """Test hybrid OCR engine"""
    
    def test_initialization_auto_mode(self):
        """Test initialization in AUTO mode"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.AUTO)
        
        assert engine.preferred_engine == OCREngineType.AUTO
        assert engine.tesseract_engine is not None
        assert engine.supported_languages == ['eng', 'hin', 'tam', 'tel']
    
    def test_initialization_tesseract_mode(self):
        """Test initialization in TESSERACT mode"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.TESSERACT)
        
        assert engine.preferred_engine == OCREngineType.TESSERACT
        assert engine.tesseract_engine is not None
    
    def test_engine_selection_auto(self):
        """Test engine selection in AUTO mode"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.AUTO)
        selected = engine._select_engine()
        
        # Should select textract if available, otherwise tesseract
        assert selected in ['textract', 'tesseract']
    
    def test_engine_selection_tesseract(self):
        """Test engine selection in TESSERACT mode"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.TESSERACT)
        selected = engine._select_engine()
        
        assert selected == 'tesseract'
    
    @patch('app.services.ocr_engine_hybrid.TextractOCREngine')
    def test_extract_text_with_textract(self, mock_textract_class):
        """Test text extraction using Textract"""
        # Mock Textract engine
        mock_textract = MagicMock()
        mock_textract.extract_text.return_value = ('Extracted text', 0.95)
        mock_textract_class.return_value = mock_textract
        
        engine = HybridOCREngine(preferred_engine=OCREngineType.TEXTRACT)
        engine.textract_engine = mock_textract
        engine.textract_available = True
        
        image_data = b'fake_image'
        text, confidence = engine.extract_text(image_data, language='eng')
        
        assert text == 'Extracted text'
        assert confidence == 0.95
        mock_textract.extract_text.assert_called_once()
    
    def test_extract_text_with_tesseract(self):
        """Test text extraction using Tesseract"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.TESSERACT)
        
        # This will use the actual Tesseract engine
        # We just verify it doesn't crash
        image_data = b'fake_image'
        text, confidence = engine.extract_text(image_data, force_engine='tesseract')
        
        # Should return empty or error gracefully
        assert isinstance(text, str)
        assert isinstance(confidence, float)
    
    def test_get_engine_info(self):
        """Test getting engine information"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.AUTO)
        info = engine.get_engine_info()
        
        assert 'preferred_engine' in info
        assert 'active_engine' in info
        assert 'textract_available' in info
        assert 'tesseract_available' in info
        assert 'supported_languages' in info
        assert 'capabilities' in info
        
        # Check capabilities
        assert 'basic_ocr' in info['capabilities']
        assert 'qr_codes' in info['capabilities']
    
    def test_textract_only_features_require_textract(self):
        """Test that Textract-only features fail gracefully without Textract"""
        engine = HybridOCREngine(preferred_engine=OCREngineType.TESSERACT)
        engine.textract_available = False
        
        image_data = b'fake_image'
        
        # These should raise exceptions
        with pytest.raises(Exception, match="requires AWS Textract"):
            engine.analyze_document(image_data)
        
        with pytest.raises(Exception, match="requires AWS Textract"):
            engine.extract_identity_document(image_data)
        
        with pytest.raises(Exception, match="requires AWS Textract"):
            engine.extract_text_from_s3('bucket', 'key')


class TestOCRWorkflowWithTextract:
    """Test OCR workflow with Textract integration"""
    
    @patch('app.services.ocr_workflow.HybridOCREngine')
    def test_workflow_uses_hybrid_engine(self, mock_hybrid_class):
        """Test that workflow uses hybrid OCR engine"""
        from app.services.ocr_workflow import OCRWorkflow
        
        mock_engine = MagicMock()
        mock_hybrid_class.return_value = mock_engine
        
        workflow = OCRWorkflow()
        
        # Verify hybrid engine was initialized
        assert workflow.ocr_engine is not None


@pytest.mark.integration
class TestTextractIntegration:
    """Integration tests for Textract (requires AWS credentials)"""
    
    @pytest.mark.skip(reason="Requires AWS credentials and incurs costs")
    def test_real_textract_extraction(self):
        """Test real Textract extraction (skipped by default)"""
        from PIL import Image
        import io
        
        # Create a simple test image with text
        img = Image.new('RGB', (800, 600), color='white')
        # In real test, would add text to image
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        image_data = img_bytes.getvalue()
        
        engine = TextractOCREngine()
        text, confidence = engine.extract_text(image_data)
        
        assert isinstance(text, str)
        assert 0 <= confidence <= 1
