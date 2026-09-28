from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from collector.feeds import collect
from digest.llm import synthesize
from digest.render import build_prompt, fallback
from filter.rank import rank


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    profile_path = root / "config/profile.yaml"
    queries_path = root / "config/queries.yaml"
    sources_path = root / "config/sources.yaml"
    candidates_path = root / "archive/candidates.jsonl"
    digest_dir = root / "archive/digests"
    digest_dir.mkdir(parents=True, exist_ok=True)

    raw = collect(str(sources_path), str(profile_path))
    ranked = rank(raw, str(profile_path), str(queries_path))

    timestamp = datetime.now(timezone.utc)
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    with candidates_path.open("a", encoding="utf-8") as fh:
        for item in ranked:
            record = dict(item)
            record["collected_at"] = timestamp.isoformat()
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    profile = yaml.safe_load(profile_path.read_text())
    prompt = build_prompt(ranked, profile)
    digest = synthesize(prompt) or fallback(ranked)
    if not digest.endswith("\n"):
        digest += "\n"

    output = digest_dir / f"{timestamp.date().isoformat()}.md"
    output.write_text(digest, encoding="utf-8")
    latest = root / "LATEST.md"
    latest.write_text(digest, encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Candidates: {len(raw)}; ranked: {len(ranked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
