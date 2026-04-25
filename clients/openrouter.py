"""OpenAI-compatible LLM client with retry, streaming, and multi-model support."""
import json
import re
import time
from typing import AsyncGenerator, Optional, List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import settings
from utils.logger import logger

class OpenRouterError(Exception):
    pass

class OpenRouterClient:
    """Enterprise-grade OpenAI-compatible chat client.

    The class name is kept for backwards compatibility with the rest of the
    project, but it can target OpenRouter, llama.cpp, vLLM, or any server that
    exposes `/chat/completions`.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.LLM_TIMEOUT
        self.disable_thinking = settings.LLM_DISABLE_THINKING
        self.is_local_backend = any(host in self.base_url for host in ("localhost", "127.0.0.1", "0.0.0.0"))
        self.extra_body = settings.LLM_EXTRA_BODY.copy()
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True
        )
        logger.info(
            f"LLM client initialized | model={self.model} | "
            f"base_url={self.base_url} | disable_thinking={self.disable_thinking}"
        )
    
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
        
        prepared_messages = self._prepare_messages(messages)
        payload = {
            "model": model,
            "messages": prepared_messages,
            "temperature": temperature,
        }
        payload.update(self.extra_body)
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format
        if stream:
            payload["stream"] = True
        if self.disable_thinking and self.is_local_backend:
            payload.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            start = time.time()
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            elapsed = (time.time() - start) * 1000
            
            data = response.json()
            usage = data.get("usage", {})
            logger.debug(
                f"LLM call | model={model} | "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} | "
                f"completion_tokens={usage.get('completion_tokens', '?')} | "
                f"time_ms={elapsed:.0f}"
            )
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            raise OpenRouterError(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"LLM error: {e}")
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
        
        content = self._strip_thinking(data["choices"][0]["message"]["content"])
        
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
        
        return self._strip_thinking(data["choices"][0]["message"]["content"]).strip()
    
    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Inject a no-thinking instruction for thinking models when requested."""
        if not self.disable_thinking:
            return messages
        
        instruction = (
            "Reasoning/thinking output is disabled. Do not include <think> blocks, "
            "chain-of-thought, hidden reasoning, or explanations unless explicitly requested. "
            "Return only the requested final answer."
        )
        prepared = [m.copy() for m in messages]
        for message in prepared:
            if message.get("role") == "system":
                message["content"] = f"{message.get('content', '')}\n\n{instruction}"
                return prepared
        return [{"role": "system", "content": instruction}, *prepared]
    
    def _strip_thinking(self, content: str) -> str:
        """Remove thinking traces from Qwen-style responses if a backend still emits them."""
        if not content:
            return content
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL)
        return content.strip()
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
