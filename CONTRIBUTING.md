# Contributing to CamWatcher

Thanks for your interest in CamWatcher! Bug reports, feature ideas, and pull requests are all welcome.

## Ground rules

- **Open an issue first** for anything non-trivial (new features, architectural changes, anything touching the stream pipeline). It saves both of us time.
- **One PR, one concern.** Small, focused PRs are easier to review and ship.
- **Be kind.** This is a hobby project — assume good intent.

## Local setup

Follow the [Quickstart in the README](README.md#quickstart) to get all three processes running (MediaMTX, backend, frontend).

You'll need:

- Python 3.11+
- Node.js 20+
- An RTSP-capable camera (any Tapo C-series works); a public test stream also works for UI-only changes

## Project layout

```
backend/   FastAPI + SQLAlchemy + OpenCV worker
frontend/  Next.js (App Router) + Tailwind
mediamtx/  RTSP -> HLS gateway (single binary + config)
media/     Local snapshot storage (gitignored)
```

See [README → Project structure](README.md#project-structure) for the detailed file map.

## Style

### Python (backend)

- Type hints everywhere. Pydantic v2 for I/O DTOs, SQLAlchemy 2.x typed models for ORM.
- Format with [Black](https://black.readthedocs.io/) defaults (line length 88).
- Prefer `async def` for route handlers; only drop into threads for blocking OpenCV work.
- Keep route handlers thin — push logic into `app/services/` or `app/ai/`.

### TypeScript (frontend)

- Strict TypeScript. No `any` without a comment explaining why.
- Components stay small and composable; colocate hooks in `src/hooks/`.
- Tailwind utility classes only — no inline styles, no CSS modules.
- Mirror backend Pydantic schemas in `src/types/` and keep them in sync.

## Commits

Use clear, conventional-ish messages:

```
feat(events): add semantic search over event embeddings
fix(streaming): retry RTSP connect with exponential backoff
docs(readme): clarify Tapo stream1 vs stream2
```

## Pull requests

Your PR description should answer:

1. **What** did you change?
2. **Why** is the change needed?
3. **How** did you test it? (manual steps are fine — attach a screenshot or screen recording if the UI changed)

Run linters before opening the PR:

```bash
cd frontend && npm run lint
```

## Security

If you find a security issue, **do not** open a public issue. Email the maintainer or open a private security advisory on GitHub instead.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
