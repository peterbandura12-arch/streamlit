from __future__ import annotations

import json
import re

import requests

DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_MODEL = "mistral-small-latest"

PRESET = {
    "Mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
    "OpenAI": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "Vlastný (OpenAI-compatible)": ("", ""),
}


def llm_sentiment(news: list[dict], api_key: str, base_url: str, model: str) -> list[dict]:
    if not news:
        return []
    lines = []
    for i, item in enumerate(news):
        text = item["title"]
        if item.get("summary"):
            text += f" — {item['summary'][:220]}"
        lines.append(f"{i}. {text}")
    prompt = (
        "Si finančný analytik. Pre každú správu nižšie ohodnoť jej vplyv na kurz akcie "
        "skóre od -2 (veľmi negatívny) do +2 (veľmi pozitívny), 0 = neutrálna. "
        "Odpovedz IBA vo formáte JSON zoznamu: "
        '[{"index": 0, "score": 1, "reason": "krátke vysvetlenie v slovenčine"}].\n\n'
        + "\n".join(lines)
    )
    url = base_url.rstrip("/") + "/chat/completions"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        raise ValueError("LLM nevrátilo očakávaný JSON zoznam.")
    parsed = json.loads(match.group(0))

    out = []
    for item in news:
        out.append({**item, "llm_score": None, "llm_reason": None})
    for entry in parsed:
        try:
            idx = int(entry["index"])
            score = float(entry["score"])
            out[idx]["llm_score"] = max(-2.0, min(2.0, score))
            out[idx]["llm_reason"] = str(entry.get("reason", "")).strip()
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    return out


def apply_llm_overrides(results: list[dict]) -> list[dict]:
    for r in results:
        if r.get("llm_score") is not None:
            r["raw"] = r["llm_score"]
            r["sentiment"] = round(r["llm_score"] * 25, 1)
            r["positive"] = []
            r["negative"] = []
    return results
