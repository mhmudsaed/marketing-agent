"""Validation and utility functions."""
import re
from typing import List, Optional
import tiktoken

class ContentValidator:
    """Enterprise content validation utilities."""
    
    CHANNEL_LIMITS = {
        "LinkedIn": 3000,
        "X": 280,
        "Twitter": 280,
        "Instagram": 2200,
        "Blog": 50000,
    }
    
    @classmethod
    def count_chars(cls, text: str) -> int:
        return len(text)
    
    @classmethod
    def count_words(cls, text: str) -> int:
        return len(text.split())
    
    @classmethod
    def estimate_tokens(cls, text: str, model: str = "gpt-4") -> int:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except:
            # Fallback estimation
            return len(text.split()) * 1.3
    
    @classmethod
    def check_char_limit(cls, text: str, channel: str) -> tuple[bool, int, int]:
        limit = cls.CHANNEL_LIMITS.get(channel, 5000)
        chars = cls.count_chars(text)
        return chars <= limit, chars, limit
    
    @classmethod
    def extract_hashtags(cls, text: str) -> List[str]:
        return re.findall(r'#\w+', text)
    
    @classmethod
    def check_hashtag_count(cls, text: str, channel: str) -> tuple[bool, int, int]:
        hashtags = cls.extract_hashtags(text)
        max_hashtags = {
            "LinkedIn": 5,
            "X": 2,
            "Twitter": 2,
            "Instagram": 10,
            "Blog": 0,
        }.get(channel, 5)
        return len(hashtags) <= max_hashtags, len(hashtags), max_hashtags
    
    @classmethod
    def check_cta_present(cls, text: str, cta: str) -> bool:
        """Check if CTA is present in content."""
        text_lower = text.lower()
        cta_lower = cta.lower()
        # Check exact or partial match
        return cta_lower in text_lower or any(
            word in text_lower for word in cta_lower.split() if len(word) > 4
        )
    
    @classmethod
    def calculate_readability(cls, text: str) -> dict:
        """Calculate Flesch Reading Ease score."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        words = text.split()
        syllables = sum(cls._count_syllables(w) for w in words)
        
        if not sentences or not words:
            return {"flesch_score": 0, "grade_level": "N/A"}
        
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllables / len(words)
        
        flesch = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        # Grade level approximation
        if flesch >= 90:
            grade = "5th grade"
        elif flesch >= 80:
            grade = "6th grade"
        elif flesch >= 70:
            grade = "7th grade"
        elif flesch >= 60:
            grade = "8th-9th grade"
        elif flesch >= 50:
            grade = "10th-12th grade"
        elif flesch >= 30:
            grade = "College"
        else:
            grade = "Graduate"
        
        return {
            "flesch_score": round(flesch, 1),
            "grade_level": grade,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2)
        }
    
    @classmethod
    def _count_syllables(cls, word: str) -> int:
        word = word.lower()
        vowels = "aeiouy"
        count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count = 1
        
        return count
    
    @classmethod
    def calculate_brand_similarity(
        cls,
        content: str,
        brand_keywords: List[str],
        brand_examples: List[str]
    ) -> float:
        """Simple keyword-based brand similarity score."""
        content_lower = content.lower()
        
        # Keyword presence
        keyword_hits = sum(1 for kw in brand_keywords if kw.lower() in content_lower)
        keyword_score = keyword_hits / max(len(brand_keywords), 1)
        
        # Example similarity (simple n-gram overlap)
        example_score = 0.0
        if brand_examples:
            example_text = " ".join(brand_examples).lower()
            content_words = set(content_lower.split())
            example_words = set(example_text.split())
            overlap = len(content_words & example_words)
            example_score = overlap / max(len(content_words), 1)
        
        return round((keyword_score * 0.6 + example_score * 0.4), 2)
    
    @classmethod
    def check_hook_strength(cls, text: str) -> dict:
        """Evaluate the strength of the opening hook."""
        lines = text.strip().split('\n')
        first_line = lines[0] if lines else text[:100]
        
        indicators = {
            "has_question": "?" in first_line,
            "has_number": bool(re.search(r'\d', first_line)),
            "has_you": "you" in first_line.lower(),
            "has_how": "how" in first_line.lower(),
            "has_why": "why" in first_line.lower(),
            "under_100_chars": len(first_line) <= 100,
            "starts_with_action": bool(re.match(r'^(Stop|Start|Never|Always|Don\'t|Do)', first_line)),
        }
        
        score = sum(indicators.values()) / len(indicators)
        
        return {
            "score": round(score, 2),
            "first_line": first_line[:120],
            "indicators": indicators
        }
