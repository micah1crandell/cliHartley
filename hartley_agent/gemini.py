"""Modern Gemini API client for Gemini 2.5 Flash and 2.0 Flash."""

import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAPIError(Exception):
    """Exception raised for Gemini API failures."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class GeminiClient:
    """Client for Google Gemini API optimized for Free Tier."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        fallback_model: str = "gemini-2.0-flash",
        temperature: float = 0.2,
    ):
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self._ssl_ctx = ssl.create_default_context()

    def _build_request_url(self, model: str, action: str, stream: bool = False) -> str:
        url = f"{BASE_URL}/{model}:{action}"
        params = []
        clean_key = (self.api_key or "").strip()
        # Legacy AIza keys can be in query params, but modern AQ. auth keys must authenticate via header
        if clean_key and clean_key.startswith("AIza"):
            params.append(f"key={clean_key}")
        if stream:
            params.append("alt=sse")
        if params:
            url += "?" + "&".join(params)
        return url

    def _execute_http(
        self,
        url: str,
        payload: Dict[str, Any],
        stream: bool = False,
        retry_count: int = 0,
        current_model: Optional[str] = None,
    ) -> Any:
        """Execute HTTP request with automatic Free Tier rate-limit backoff and fallback."""
        model = current_model or self.model
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Hartley-Agent/2.0",
        }
        clean_key = (self.api_key or "").strip()
        if clean_key:
            headers["x-goog-api-key"] = clean_key

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")

        try:
            return urllib.request.urlopen(req, context=self._ssl_ctx, timeout=60)
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="replace")
            err_data = {}
            err_message = raw_err
            try:
                err_data = json.loads(raw_err)
                err_message = err_data.get("error", {}).get("message", raw_err)
            except Exception:
                pass

            # Handle 401 (Authentication failure)
            if e.code == 401:
                from .config import get_api_key_source_description
                source_desc = get_api_key_source_description()
                raise GeminiAPIError(
                    f"Gemini API authentication failed (401): {err_message}\n"
                    f"  Key Source: {source_desc}\n"
                    "  Tip: Verify that your API key is active in Google AI Studio: https://aistudio.google.com/app/apikey\n"
                    "  To update your saved key, run: hartley key <your_key>\n"
                    "  Or run 'hartley key' interactively.",
                    status_code=401,
                    details=err_data,
                )

            # Handle 429 (Resource Exhausted / Rate limit on Free Tier)
            if e.code == 429:
                if retry_count < 3:
                    wait_sec = (retry_count + 1) * 3
                    sys.stderr.write(
                        f"\n\033[93m[Gemini Free Tier rate limit reached. Waiting {wait_sec}s before retry...]\033[0m\n"
                    )
                    time.sleep(wait_sec)
                    return self._execute_http(
                        url, payload, stream=stream, retry_count=retry_count + 1, current_model=model
                    )
                raise GeminiAPIError(
                    f"Gemini Free Tier rate limit exceeded (429): {err_message}\n"
                    "Tip: Google AI Studio Free Tier has a requests-per-minute limit. Please wait a moment and try again.",
                    status_code=429,
                    details=err_data,
                )

            # Handle 404 (Model version changed or not found) -> Attempt fallback model
            if e.code == 404 and model != self.fallback_model:
                sys.stderr.write(
                    f"\n\033[90m[Model {model} unavailable, falling back to {self.fallback_model}...]\033[0m\n"
                )
                action = "streamGenerateContent" if stream else "generateContent"
                fallback_url = self._build_request_url(self.fallback_model, action, stream=stream)
                return self._execute_http(
                    fallback_url, payload, stream=stream, retry_count=retry_count, current_model=self.fallback_model
                )

            raise GeminiAPIError(f"Gemini API error ({e.code}): {err_message}", status_code=e.code, details=err_data)
        except urllib.error.URLError as e:
            raise GeminiAPIError(f"Network error connecting to Gemini: {str(e.reason)}")

    def generate_content(
        self,
        contents: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Call generateContent synchronously."""
        url = self._build_request_url(self.model, "generateContent", stream=False)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if tools:
            payload["tools"] = [{"functionDeclarations": tools}]

        response = self._execute_http(url, payload, stream=False)
        data = json.loads(response.read().decode("utf-8"))
        return data

    def stream_generate_content(
        self,
        contents: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream tokens via Server-Sent Events (SSE).
        Yields candidate chunk dictionaries as they arrive.
        """
        url = self._build_request_url(self.model, "streamGenerateContent", stream=True)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if tools:
            payload["tools"] = [{"functionDeclarations": tools}]

        response = self._execute_http(url, payload, stream=True)

        buffer = ""
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace")
            buffer += line
            while "\n" in buffer:
                line_str, buffer = buffer.split("\n", 1)
                line_str = line_str.strip()
                if not line_str or not line_str.startswith("data:"):
                    continue
                json_str = line_str[5:].strip()
                if not json_str:
                    continue
                try:
                    chunk = json.loads(json_str)
                    yield chunk
                except json.JSONDecodeError:
                    continue


def extract_text_from_response(response: Dict[str, Any]) -> str:
    """Extract plain text from a Gemini response dict."""
    candidates = response.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    return "".join(text_parts).strip()


def extract_function_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract functionCall items from a Gemini response dict."""
    candidates = response.get("candidates", [])
    if not candidates:
        return []
    parts = candidates[0].get("content", {}).get("parts", [])
    return [p.get("functionCall") for p in parts if "functionCall" in p]
