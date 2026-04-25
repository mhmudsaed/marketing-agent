"""Probe the configured LLM endpoint for Qwen-style <think> output.

Usage:
    python scripts/test_llm_thinking.py
"""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def strip_thinking(content: str) -> str:
    return re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()


def main() -> int:
    env = load_env(Path(".env"))
    base_url = env.get("LLM_BASE_URL", "http://localhost:8082/v1").rstrip("/")
    model = env.get("LLM_MODEL", "qwen-3.6")
    api_key = env.get("LLM_API_KEY", "")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Thinking output is disabled. Do not include <think> blocks. "
                    "Return only the final answer."
                ),
            },
            {"role": "user", "content": "Reply with exactly: pong"},
        ],
        "temperature": 0,
        "max_tokens": 128,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    print(f"endpoint={base_url}")
    print(f"model={model}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"HTTP_ERROR {exc.code}")
        print(exc.read().decode("utf-8")[:1000])
        return 1
    except Exception as exc:
        print(f"CONNECTION_ERROR {type(exc).__name__}: {exc}")
        return 1

    content = data["choices"][0]["message"].get("content", "")
    raw_has_think = "<think" in content.lower() or "</think>" in content.lower()
    stripped = strip_thinking(content)
    stripped_has_think = "<think" in stripped.lower() or "</think>" in stripped.lower()

    print(f"raw_has_think_tags={raw_has_think}")
    print(f"stripped_has_think_tags={stripped_has_think}")
    print("raw_content_start=")
    print(content[:1000])
    print("stripped_content_start=")
    print(stripped[:1000])

    return 0 if not stripped_has_think else 2


if __name__ == "__main__":
    raise SystemExit(main())
