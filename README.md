# AI Research Monitor

A reproducible weekly monitor for AI research, evaluation, agents, reasoning, and career-relevant developments.

The system has four stages: collect candidates from public RSS/Atom feeds and APIs; score them with an inspectable config-driven relevance model; synthesize the five-section digest with an OpenAI-compatible model when configured; and archive both candidates and digests in the repository.

It deliberately does not depend on a proprietary web-search agent inside GitHub Actions.

## Layout

```text
config/                 profile, queries, and sources
collector/              RSS/Atom and arXiv collection
filter/                 deterministic scoring
digest/                 synthesis, fallback rendering, pipeline entry point
archive/                generated candidate and digest history
.github/workflows/      Monday scheduled workflow
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m digest.run
```

Set `OPENAI_API_KEY` to enable model-written synthesis. `OPENAI_MODEL` and `OPENAI_BASE_URL` are optional. Without a model key, the pipeline still collects, scores, and renders a deterministic digest.

## GitHub Actions

The workflow runs Mondays at 07:00 UTC and is also manually dispatchable. Give the repository these optional Actions secrets:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`

The workflow requests `contents: write` and commits generated digest/archive files back to the default branch.

## Digest contract

Every digest has five sections:

1. Important developments
2. Research leads
3. 2–3 things worth reading
4. `rl_eval_generator` relevance
5. Career-relevant developments

The numerical score is only a transparent prioritization aid; it is not an objective measure of research importance.
