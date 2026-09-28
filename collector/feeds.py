from __future__ import annotations

import argparse
import hashlib
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import feedparser
import requests
import yaml


@dataclass
class Candidate:
    id: str
    title: str
    url: str
    summary: str
    published: str
    source_id: str
    source_label: str
    source_quality: float
    authors: list[str]
    tags: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date(entry: Any) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass
        stamp = entry.get(f"{key}_parsed")
        if stamp:
            return datetime(*stamp[:6], tzinfo=timezone.utc)
    return None


def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def _stable_id(source_id: str, title: str, url: str) -> str:
    raw = f"{source_id}|{title.strip().lower()}|{url.strip()}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _from_feed(source: dict[str, Any], cutoff: datetime) -> list[Candidate]:
    parsed = feedparser.parse(source["url"])
    if getattr(parsed, "bozo", False) and not parsed.entries:
        raise RuntimeError(f"feed parse failed for {source['url']}: {parsed.bozo_exception}")
    out: list[Candidate] = []
    for entry in parsed.entries:
        published = _parse_date(entry)
        if published and published < cutoff:
            continue
        title = _clean_html(entry.get("title", "Untitled"))
        url = entry.get("link", "").strip()
        if not url:
            continue
        summary = _clean_html(entry.get("summary", entry.get("description", "")))
        authors = []
        for author in entry.get("authors", []) or []:
            name = author.get("name") if isinstance(author, dict) else str(author)
            if name:
                authors.append(name)
        if not authors and entry.get("author"):
            authors.append(str(entry.author))
        when = (published or _now()).isoformat()
        out.append(Candidate(
            id=_stable_id(source["id"], title, url),
            title=title,
            url=url,
            summary=summary,
            published=when,
            source_id=source["id"],
            source_label=source.get("label", source["id"]),
            source_quality=float(source.get("quality", 0.5)),
            authors=authors,
            tags=[],
        ))
    return out


def _from_arxiv(source: dict[str, Any], cutoff: datetime) -> list[Candidate]:
    query = quote(source["query"])
    url = (
        "https://export.arxiv.org/api/query?search_query=" + query
        + "&start=0&max_results=" + str(int(source.get("max_results", 50)))
        + "&sortBy=submittedDate&sortOrder=descending"
    )
    response = requests.get(url, timeout=45, headers={"User-Agent": "ai-research-monitor/0.1"})
    response.raise_for_status()
    parsed = feedparser.parse(response.text)
    out: list[Candidate] = []
    for entry in parsed.entries:
        published = _parse_date(entry)
        if published and published < cutoff:
            continue
        title = _clean_html(entry.get("title", "Untitled"))
        link = entry.get("link", "").strip()
        if not link:
            link = str(entry.get("id", "")).strip()
        summary = _clean_html(entry.get("summary", ""))
        authors = [a.name for a in entry.get("authors", []) if getattr(a, "name", None)]
        when = (published or _now()).isoformat()
        out.append(Candidate(
            id=_stable_id(source["id"], title, link),
            title=title,
            url=link,
            summary=summary,
            published=when,
            source_id=source["id"],
            source_label=source.get("label", source["id"]),
            source_quality=float(source.get("quality", 0.5)),
            authors=authors,
            tags=[],
        ))
        time.sleep(0.02)
    return out


def collect(config_path: str = "config/sources.yaml", profile_path: str = "config/profile.yaml") -> list[dict[str, Any]]:
    sources = yaml.safe_load(Path(config_path).read_text()) ["sources"]
    profile = yaml.safe_load(Path(profile_path).read_text())
    cutoff = _now() - timedelta(days=int(profile.get("lookback_days", 14)))
    candidates: dict[str, Candidate] = {}
    for source in sources:
        if not source.get("enabled", True):
            continue
        try:
            kind = source["type"]
            batch = _from_arxiv(source, cutoff) if kind == "arxiv" else _from_feed(source, cutoff)
            for candidate in batch:
                candidates[candidate.id] = candidate
        except Exception as exc:
            print(f"WARN: source {source.get('id')} failed: {exc}")
    limit = int(profile.get("candidate_limit", 120))
    ordered = sorted(candidates.values(), key=lambda c: c.published, reverse=True)[:limit]
    return [c.as_dict() for c in ordered]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="archive/candidates.json")
    args = parser.parse_args()
    data = collect()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    print(f"Collected {len(data)} candidates")


if __name__ == "__main__":
    main()
