import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class PromptInjectionDetector:
    """
    Heuristic and pattern-based prompt injection detection.
    Prevents attackers from feeding malicious instructions to the RAIC agents.
    """
    
    # Common attack vectors for LLMs
    DANGEROUS_PATTERNS = [
        r"(?i)ignore previous instructions",
        r"(?i)disregard previous",
        r"(?i)you are now",
        r"(?i)system prompt",
        r"(?i)output the following",
        r"(?i)system override",
        r"(?i)bypass restrictions",
        r"(?i)do not follow",
        r"(?i)forget everything",
        r"(?i)echo \\\"",
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p) for p in self.DANGEROUS_PATTERNS]

    def check_for_injection(self, text: str) -> Tuple[bool, str]:
        """
        Returns (is_injected, reason).
        If is_injected is True, the text contains a suspected prompt injection attack.
        """
        if not text:
            return False, ""
            
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                logger.warning(f"Prompt injection detected! Matched pattern: {pattern.pattern}")
                return True, f"Injection pattern detected: {pattern.pattern}"
                
        return False, ""
