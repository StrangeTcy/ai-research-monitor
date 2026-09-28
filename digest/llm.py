from __future__ import annotations

import json
import os
from typing import Any

import requests


def synthesize(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an exacting research editor. Do not invent facts, citations, experiments, or career openings. Preserve source URLs and distinguish source claims from your synthesis."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = requests.post(
        base_url + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
