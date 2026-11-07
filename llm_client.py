"""Groq/Gemini LLM client with provider fallback."""
import requests

GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.5-flash-lite"
PRIMARY_PROVIDER = "groq"
FALLBACK_PROVIDER = "gemini"

import requests


class LLMClient:

    def __init__(self, api_keys):
        self.api_keys = api_keys

        self.models = {
            "groq": GROQ_MODEL,
            "gemini": GEMINI_MODEL
        }

    def generate(self, prompt, system_prompt=None, provider="groq"):

        print("LLM prompt length:", len(prompt))
        print("LLM prompt size (KB):", len(prompt.encode("utf-8")) / 1024)
        print("System prompt length:", len(system_prompt or ""))
        
        if provider not in self.models:
            raise ValueError(f"Unsupported provider: {provider}")

        api_key = self.api_keys.get(provider)

        if not api_key:
            raise ValueError(f"Missing API key for {provider}")

        model = self.models[provider]

        if provider == "groq":
            return self._generate_groq(
                prompt, system_prompt, api_key, model
            )

        return self._generate_gemini(
            prompt, system_prompt, api_key, model
        )

    def _generate_groq(self, prompt, system_prompt, api_key, model):

        url = "https://api.groq.com/openai/v1/chat/completions"

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1200
            },
            timeout=60
        )

        if not response.ok:
            raise RuntimeError(
                f"HTTP {response.status_code}: {response.text[:1000]}"
            )

        result = response.json()

        return {
            "text": result["choices"][0]["message"]["content"],
            "provider": "groq",
            "model": model,
            "usage": result.get("usage", {})
        }

    def _generate_gemini(self, prompt, system_prompt, api_key, model):

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
        )

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1200
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        candidates = result.get("candidates", [])

        if not candidates:
            raise RuntimeError("Gemini returned no response candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = "\n".join(
            part["text"] for part in parts if "text" in part
        )

        if not answer:
            raise RuntimeError("Gemini returned an empty response.")

        return {
            "text": answer,
            "provider": "gemini",
            "model": model,
            "usage": result.get("usageMetadata", {})
        }

    def generate_with_fallback(self, prompt, system_prompt=None):

        try:
            return self.generate(
                prompt,
                system_prompt,
                provider="groq"
            )

        except Exception as primary_error:
            print(f"Groq failed: {repr(primary_error)}")

            try:
                return self.generate(
                    prompt,
                    system_prompt,
                    provider="gemini"
                )
            except Exception as fallback_error:
                print(f"Gemini failed: {repr(fallback_error)}")

                raise RuntimeError(
                    f"Both LLM providers failed.\n"
                    f"Groq: {primary_error}\n"
                    f"Gemini: {fallback_error}"
                )
        
            try:
                result = self.generate(
                    prompt,
                    system_prompt,
                    provider=FALLBACK_PROVIDER
                )

                result["fallback_used"] = True
                return result

            except Exception as fallback_error:
                raise RuntimeError(
                    "Both LLM providers failed. "
                    f"Primary: {type(primary_error).__name__}; "
                    f"Fallback: {type(fallback_error).__name__}"
                ) from fallback_error




# Latest validated provider implementations from the notebook.
import requests
from types import MethodType


def _generate_groq(self, prompt, system_prompt, api_key, model):

    url = "https://api.groq.com/openai/v1/chat/completions"

    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1200
        },
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError("Groq returned no response choices.")

    choice = choices[0]
    answer = choice.get("message", {}).get("content", "")

    if not answer:
        raise RuntimeError("Groq returned an empty response.")

    finish_reason = choice.get("finish_reason")

    if finish_reason == "length":
        raise RuntimeError(
            "Groq response was truncated because of the token limit."
        )

    return {
        "text": answer,
        "provider": "groq",
        "model": model,
        "finish_reason": finish_reason,
        "usage": result.get("usage", {})
    }


def _generate_gemini(self, prompt, system_prompt, api_key, model):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1200,
            "responseMimeType": "application/json"
        }
    }

    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=60
    )

    if not response.ok:
        raise RuntimeError(
            f"HTTP {response.status_code}: {response.text[:1000]}"
        )

    result = response.json()

    candidates = result.get("candidates", [])

    if not candidates:
        raise RuntimeError("Gemini returned no response candidates.")

    candidate = candidates[0]

    parts = candidate.get("content", {}).get("parts", [])

    answer = "\n".join(
        part["text"]
        for part in parts
        if "text" in part
    )

    if not answer:
        raise RuntimeError("Gemini returned an empty response.")

    finish_reason = candidate.get("finishReason")

    if finish_reason == "MAX_TOKENS":
        raise RuntimeError(
            "Gemini response was truncated because of the token limit."
        )

    return {
        "text": answer,
        "provider": "gemini",
        "model": model,
        "finish_reason": finish_reason,
        "usage": result.get("usageMetadata", {})
    }

LLMClient._generate_groq = _generate_groq
LLMClient._generate_gemini = _generate_gemini
