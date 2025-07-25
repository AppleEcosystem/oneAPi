import importlib
from typing import Dict, Any

class LanguageManager:
    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang
        self.languages = {}
        self.load_language(default_lang)
    
    def load_language(self, lang_code: str):
        """Load language file"""
        try:
            module = importlib.import_module(f"languages.{lang_code}")
            self.languages[lang_code] = module.TEXTS
        except ImportError:
            if lang_code != self.default_lang:
                self.load_language(self.default_lang)
    
    def get_text(self, key: str, lang: str = None, **kwargs) -> str:
        """Get text by key"""
        lang = lang or self.default_lang
        
        if lang not in self.languages:
            self.load_language(lang)
        
        texts = self.languages.get(lang, self.languages[self.default_lang])
        text = texts.get(key, key)
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

# Global instance
lang_manager = LanguageManager()
