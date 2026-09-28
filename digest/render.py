from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_prompt(ranked: list[dict[str, Any]], profile: dict[str, Any]) -> str:
    blocks = []
    for i, item in enumerate(ranked[:40], 1):
        blocks.append(
            f"[{i}] {item['title']}\n"
            f"Source: {item['source_label']}\n"
            f"Published: {item['published']}\n"
            f"URL: {item['url']}\n"
            f"Themes: {', '.join(item.get('themes', [])) or 'none'}\n"
            f"RL-eval hits: {', '.join(item.get('rl_eval_hits', [])) or 'none'}\n"
            f"Career hits: {', '.join(item.get('career_hits', [])) or 'none'}\n"
            f"Summary: {item.get('summary', '')[:1800]}"
        )
    return f"""Produce a weekly AI research digest from the candidate set below.

Research profile:
{profile.get('profile', {}).get('summary', '')}

Write exactly five top-level sections:
1. Important developments — up to 5 items that look genuinely consequential or technically informative.
2. Research leads — up to 5 concrete questions, experiments, papers, implementation ideas, or lines of investigation worth following.
3. 2–3 things worth reading — choose only 2 or 3 and explain why each deserves the time.
4. `rl_eval_generator` relevance — identify concrete connections to evaluation environments, task generation, long-horizon reasoning, adversarial evaluation, epistemic-game ideas, or related infrastructure.
5. Career-relevant developments — identify concrete hiring, research, fellowship, or project signals when present. Do not invent openings.

Rules:
- Use only the supplied candidates.
- Link every item to its source URL.
- Prefer specific technical information over generic announcements.
- Treat arXiv papers as preprints, not established results.
- Separate observed facts from your interpretation.
- Do not rank people, companies, or career choices.
- If a section lacks good evidence, say so briefly rather than filling it with weak items.
- Keep the finished digest below roughly 2200 words.

Candidates:

""" + "\n\n".join(blocks)


def fallback(ranked: list[dict[str, Any]]) -> str:
    now = datetime.now(timezone.utc).date().isoformat()
    top = ranked[:5]
    rl = [x for x in ranked if x.get("rl_eval_hits")][:4]
    career = [x for x in ranked if x.get("career_hits")][:4]
    reading = ranked[:3]
    lines = [f"# Weekly AI Research Digest — {now}", "", "## Important developments"]
    for item in top:
        lines.append(f"- **{item['title']}** — {item['source_label']}. {item.get('summary','')[:500]} [source]({item['url']})")
    lines += ["", "## Research leads"]
    for item in ranked[:5]:
        leads = ", ".join(item.get("themes", [])) or "research relevance"
        lines.append(f"- Follow up on **{item['title']}** ({leads}). [source]({item['url']})")
    lines += ["", "## 2–3 things worth reading"]
    for item in reading:
        lines.append(f"- **{item['title']}** — {item.get('summary','')[:360]} [read]({item['url']})")
    lines += ["", "## `rl_eval_generator` relevance"]
    if rl:
        for item in rl:
            lines.append(f"- **{item['title']}** — matched: {', '.join(item.get('rl_eval_hits', []))}. [source]({item['url']})")
    else:
        lines.append("- No strong RL/evaluation-generator matches in this week's candidate set.")
    lines += ["", "## Career-relevant developments"]
    if career:
        for item in career:
            lines.append(f"- **{item['title']}** — matched: {', '.join(item.get('career_hits', []))}. [source]({item['url']})")
    else:
        lines.append("- No strong career-related developments were detected in the collected sources.")
    lines += ["", "_This digest used deterministic filtering because no model API key was configured._"]
    return "\n".join(lines) + "\n"
