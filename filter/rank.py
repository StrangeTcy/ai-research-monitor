from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _tokens(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _contains(text: str, term: str) -> bool:
    return term.lower() in text


def _recency_score(published: str, half_life_days: float) -> float:
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    age = max((datetime.now(timezone.utc) - dt).total_seconds() / 86400, 0.0)
    return math.exp(-math.log(2) * age / max(half_life_days, 0.1))


def rank(candidates: list[dict[str, Any]], profile_path: str = "config/profile.yaml", queries_path: str = "config/queries.yaml") -> list[dict[str, Any]]:
    profile = yaml.safe_load(Path(profile_path).read_text())
    queries = yaml.safe_load(Path(queries_path).read_text())
    topics = queries.get("topics", {})
    rl_terms = queries.get("rl_eval_generator", [])
    career_terms = queries.get("career", [])
    scoring = profile.get("scoring", {})
    all_primary = profile.get("profile", {}).get("primary_themes", [])
    half_life = float(scoring.get("recency_half_life_days", 5))

    ranked: list[dict[str, Any]] = []
    for item in candidates:
        text = _tokens(" ".join([item.get("title", ""), item.get("summary", ""), " ".join(item.get("authors", []))]))
        theme_hits: list[str] = []
        topic_hit_count = 0
        for topic, terms in topics.items():
            if any(_contains(text, term) for term in terms):
                theme_hits.append(topic)
                topic_hit_count += sum(1 for term in terms if _contains(text, term))
        primary_hits = sum(1 for theme in all_primary if _contains(text, theme))
        rl_hits = [term for term in rl_terms if _contains(text, term)]
        career_hits = [term for term in career_terms if _contains(text, term)]
        recency = _recency_score(item.get("published", ""), half_life)
        score = (
            recency
            + float(scoring.get("theme_match", 2.0)) * min(topic_hit_count, 4) / 4
            + float(scoring.get("primary_theme_match", 1.5)) * min(primary_hits, 2) / 2
            + float(scoring.get("eval_match", 2.5)) * (1 if "evaluation" in theme_hits else 0)
            + float(scoring.get("rl_eval_match", 2.5)) * min(len(rl_hits), 3) / 3
            + float(scoring.get("career_match", 1.75)) * min(len(career_hits), 3) / 3
            + float(scoring.get("source_quality", 1.0)) * float(item.get("source_quality", 0.5))
        )
        if len(item.get("title", "")) > 180:
            score -= 0.15
        enriched = dict(item)
        enriched.update({
            "score": round(score, 4),
            "recency_score": round(recency, 4),
            "themes": theme_hits,
            "rl_eval_hits": rl_hits,
            "career_hits": career_hits,
        })
        ranked.append(enriched)

    ranked.sort(key=lambda x: (x["score"], x.get("published", "")), reverse=True)
    return ranked
