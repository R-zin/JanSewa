"""
Language Service

Handles multi-language support with translation and terminology preservation.
"""

from typing import Dict, List, Optional
from enum import Enum


class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


class FormalityLevel(str, Enum):
    """Formality levels for responses"""
    FORMAL = "formal"
    NEUTRAL = "neutral"
    CASUAL = "casual"


class LanguageService:
    """
    Manages multi-language support with translation and terminology preservation.
    """
    
    def __init__(self):
        """Initialize language service"""
        self.supported_languages = [lang.value for lang in Language]
        self._init_terminology_database()
    
    def _init_terminology_database(self):
        """Initialize official terminology database"""
        # Official terms that should not be translated
        self.official_terms = {
            "en": {
                "Aadhaar": "Aadhaar",
                "PAN": "PAN",
                "DigiLocker": "DigiLocker",
                "UIDAI": "UIDAI",
                "OBC": "OBC",
                "SC": "SC",
                "ST": "ST",
                "EWS": "EWS",
                "RTI": "RTI",
                "Gazette": "Gazette"
            },
            "hi": {
                "Aadhaar": "आधार",
                "PAN": "पैन",
                "DigiLocker": "डिजीलॉकर",
                "UIDAI": "यूआईडीएआई",
                "OBC": "ओबीसी",
                "SC": "एससी",
                "ST": "एसटी",
                "EWS": "ईडब्ल्यूएस",
                "RTI": "आरटीआई",
                "Gazette": "राजपत्र"
            }
        }
        
        # Common government terms with translations
        self.term_translations = {
            "en": {
                "application": "application",
                "certificate": "certificate",
                "document": "document",
                "verification": "verification",
                "submission": "submission",
                "approval": "approval",
                "rejection": "rejection",
                "pending": "pending",
                "completed": "completed"
            },
            "hi": {
                "application": "आवेदन",
                "certificate": "प्रमाण पत्र",
                "document": "दस्तावेज़",
                "verification": "सत्यापन",
                "submission": "प्रस्तुति",
                "approval": "स्वीकृति",
                "rejection": "अस्वीकृति",
                "pending": "लंबित",
                "completed": "पूर्ण"
            }
        }
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        Check if language is supported
        
        Args:
            language_code: Language code (e.g., 'en', 'hi')
            
        Returns:
            True if supported
        """
        return language_code in self.supported_languages
    
    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        preserve_terms: bool = True
    ) -> str:
        """
        Translate text while preserving official terminology
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            preserve_terms: Whether to preserve official terms
            
        Returns:
            Translated text
        """
        if source_lang == target_lang:
            return text
        
        if not self.is_language_supported(target_lang):
            return text
        
        # In production, integrate with Google Translate API or similar
        # For now, return placeholder
        if preserve_terms:
            # Preserve official terms during translation
            preserved_text = self._preserve_official_terms(text, target_lang)
            return preserved_text
        
        return f"[Translated to {target_lang}]: {text}"
    
    def _preserve_official_terms(self, text: str, target_lang: str) -> str:
        """
        Preserve official terms during translation
        
        Args:
            text: Text to process
            target_lang: Target language
            
        Returns:
            Text with preserved terms
        """
        # Replace official terms with their correct forms
        result = text
        
        if target_lang in self.official_terms:
            for en_term, local_term in self.official_terms[target_lang].items():
                result = result.replace(en_term, local_term)
        
        return result
    
    def get_term_translation(
        self,
        term: str,
        target_lang: str
    ) -> str:
        """
        Get translation for a specific term
        
        Args:
            term: Term to translate
            target_lang: Target language
            
        Returns:
            Translated term
        """
        term_lower = term.lower()
        
        # Check official terms first
        if target_lang in self.official_terms:
            for en_term, local_term in self.official_terms[target_lang].items():
                if en_term.lower() == term_lower:
                    return local_term
        
        # Check common terms
        if target_lang in self.term_translations:
            if term_lower in self.term_translations[target_lang]:
                return self.term_translations[target_lang][term_lower]
        
        return term
    
    def explain_technical_term(
        self,
        term: str,
        language: str = "en"
    ) -> Dict[str, str]:
        """
        Provide explanation for technical terms
        
        Args:
            term: Technical term
            language: Language for explanation
            
        Returns:
            Explanation dictionary
        """
        explanations = {
            "Aadhaar": {
                "en": "A 12-digit unique identification number issued by UIDAI to all Indian residents based on their biometric and demographic data.",
                "hi": "यूआईडीएआई द्वारा सभी भारतीय निवासियों को उनके बायोमेट्रिक और जनसांख्यिकीय डेटा के आधार पर जारी किया गया 12 अंकों का विशिष्ट पहचान नंबर।"
            },
            "PAN": {
                "en": "Permanent Account Number - A 10-character alphanumeric identifier issued by the Income Tax Department for tax purposes.",
                "hi": "स्थायी खाता संख्या - कर उद्देश्यों के लिए आयकर विभाग द्वारा जारी 10 वर्णों का अल्फान्यूमेरिक पहचानकर्ता।"
            },
            "DigiLocker": {
                "en": "A digital locker service by the Government of India to store and access official documents digitally.",
                "hi": "आधिकारिक दस्तावेजों को डिजिटल रूप से संग्रहीत और एक्सेस करने के लिए भारत सरकार की एक डिजिटल लॉकर सेवा।"
            },
            "OBC": {
                "en": "Other Backward Classes - A collective term used by the Government of India to classify castes which are educationally or socially disadvantaged.",
                "hi": "अन्य पिछड़ा वर्ग - भारत सरकार द्वारा शैक्षिक या सामाजिक रूप से वंचित जातियों को वर्गीकृत करने के लिए उपयोग किया जाने वाला सामूहिक शब्द।"
            },
            "RTI": {
                "en": "Right to Information - A fundamental right that allows citizens to request information from public authorities.",
                "hi": "सूचना का अधिकार - एक मौलिक अधिकार जो नागरिकों को सार्वजनिक प्राधिकरणों से जानकारी का अनुरोध करने की अनुमति देता है।"
            }
        }
        
        term_explanations = explanations.get(term, {})
        explanation = term_explanations.get(language, term_explanations.get("en", ""))
        
        return {
            "term": term,
            "language": language,
            "explanation": explanation,
            "local_term": self.get_term_translation(term, language)
        }
    
    def format_response(
        self,
        content: str,
        language: str,
        formality: FormalityLevel = FormalityLevel.NEUTRAL
    ) -> str:
        """
        Format response with appropriate formality level
        
        Args:
            content: Response content
            language: Target language
            formality: Formality level
            
        Returns:
            Formatted response
        """
        # In production, adjust tone and formality based on language and level
        # For now, return content with language-specific formatting
        
        if formality == FormalityLevel.FORMAL:
            # Add formal greeting/closing
            if language == "hi":
                return f"नमस्ते,\n\n{content}\n\nधन्यवाद"
            else:
                return f"Dear User,\n\n{content}\n\nThank you"
        
        return content
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages
        
        Returns:
            List of language information
        """
        language_names = {
            "en": "English",
            "hi": "हिन्दी (Hindi)",
            "ta": "தமிழ் (Tamil)",
            "te": "తెలుగు (Telugu)",
            "bn": "বাংলা (Bengali)",
            "mr": "मराठी (Marathi)",
            "gu": "ગુજરાતી (Gujarati)",
            "kn": "ಕನ್ನಡ (Kannada)",
            "ml": "മലയാളം (Malayalam)",
            "pa": "ਪੰਜਾਬੀ (Punjabi)"
        }
        
        return [
            {
                "code": lang,
                "name": language_names.get(lang, lang),
                "native_name": language_names.get(lang, lang)
            }
            for lang in self.supported_languages
        ]
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language code
        """
        # In production, use language detection library
        # For now, simple heuristic
        
        # Check for Hindi characters
        if any('\u0900' <= char <= '\u097F' for char in text):
            return "hi"
        
        # Check for Tamil characters
        if any('\u0B80' <= char <= '\u0BFF' for char in text):
            return "ta"
        
        # Default to English
        return "en"
