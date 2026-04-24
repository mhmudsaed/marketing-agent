"""OpenRouter API client with retry, streaming, and multi-model support."""
import json
import time
from typing import AsyncGenerator, Optional, List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import settings
from utils.logger import logger

class OpenRouterError(Exception):
    pass

class OpenRouterClient:
    """Enterprise-grade OpenRouter client."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 120
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": settings.OPENROUTER_SITE_NAME or "MarketingAgent",
        }
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True
        )
        logger.info(f"OpenRouter client initialized | model={self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException))
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format
        if stream:
            payload["stream"] = True
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            start = time.time()
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            elapsed = (time.time() - start) * 1000
            
            data = response.json()
            usage = data.get("usage", {})
            logger.debug(
                f"OpenRouter call | model={model} | "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} | "
                f"completion_tokens={usage.get('completion_tokens', '?')} | "
                f"time_ms={elapsed:.0f}"
            )
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")
            raise OpenRouterError(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise OpenRouterError(str(e))
    
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response_format = {"type": "json_object"}
        
        data = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        
        content = data["choices"][0]["message"]["content"]
        
        # Handle JSON parsing with fallback
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                json_part = content.split("```json")[1].split("```")[0]
                return json.loads(json_part.strip())
            elif "```" in content:
                json_part = content.split("```")[1].split("```")[0]
                return json.loads(json_part.strip())
            else:
                raise OpenRouterError(f"Could not parse JSON from response: {content[:200]}")
    
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate plain text output."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        data = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return data["choices"][0]["message"]["content"].strip()
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
