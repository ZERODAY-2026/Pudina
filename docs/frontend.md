# DataMind – Frontend Documentation

## Stack

| Tool | Version | Purpose |
|------|---------|---------|
| React | 18.3.1 | UI library |
| Vite | 5.4.8 | Dev server & bundler |
| TypeScript | 5.6.2 | Type safety |
| Vitest | 2.1.1 | Test runner |
| React Testing Library | 16.0.1 | Component tests |
| jest-axe | 9.0.0 | Accessibility tests |

CSS: plain CSS with CSS custom properties (no Tailwind, no MUI, no Bootstrap).

## Project layout

```
frontend/
├── index.html
├── package.json          # pinned deps + npm scripts
├── vite.config.ts        # dev proxy + Vitest config
├── tsconfig*.json
├── eslint.config.js
├── .env.example
└── src/
    ├── main.tsx           # entry point
    ├── App.tsx            # root component (shell)
    ├── App.test.tsx       # smoke + a11y tests for shell
    ├── index.css          # design system (CSS variables)
    ├── vite-env.d.ts      # typed env vars
    ├── types.ts           # all types mirroring api_contract.md
    ├── api/
    │   ├── client.ts      # getHealth, getDatasets, ask()
    │   ├── contract.ts    # Runtime validators for every API response
    │   ├── mock.ts        # fixture-based mock (VITE_USE_MOCK=true)
    │   └── __tests__/
    │   └── mock.test.ts, contract.test.ts
    ├── components/
    │   ├── AnswerCard.tsx
    │   ├── AppHeader.tsx
    │   ├── AppSidebar.tsx
    │   ├── ChatComposer.tsx
    │   ├── ChatTranscript.tsx
    │   ├── EmptyState.tsx
    │   ├── ErrorMessage.tsx
    │   ├── HealthIndicator.tsx
    │   ├── LoadingMessage.tsx
    │   └── UserBubble.tsx
    ├── hooks/
    │   ├── useChat.ts
    │   ├── useDatasets.ts
    │   └── useHealth.ts
    ├── __tests__/
    │   └── chat.test.tsx
    └── test/
        └── setup.ts       # jest-dom + jest-axe global setup
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_USE_MOCK` | `false` | Opt in to serving `docs/fixtures/` instead of the real API |
| `VITE_API_BASE` | `http://localhost:8000` | Backend base URL |

Copy `.env.example` to `.env.local` and set values. Never commit `.env.local`.

## npm scripts

| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `vite` | Dev server with HMR |
| `build` | `tsc -b && vite build` | Production bundle |
| `preview` | `vite preview` | Preview production bundle |
| `test` | `vitest run` | Run all tests once |
| `test:watch` | `vitest` | Watch mode |
| `lint` | `eslint src` | Lint TypeScript & TSX |

## Mock mode

Set `VITE_USE_MOCK=true` (or `VITE_USE_MOCK=true npm run dev`) to run entirely
against `docs/fixtures/*.json` — no backend required.

Fixture routing for `POST /api/ask` (case-insensitive, first match wins):

| Question contains | Fixture |
|---|---|
| `clarify` | `ask_clarify.json` |
| `refuse` | `ask_unsupported.json` |
| `empty` | `ask_empty.json` |
| `error` | `ask_error.json` |
| `large` | `ask_answered_large.json` |
| *(anything else)* | `ask_answered.json` |

## API contract

The single source of truth is `docs/api_contract.md`.
`src/types.ts` mirrors it, and `src/api/contract.ts` validates each successful
API response at runtime — **never change response shapes** without updating
the contract, the fixtures, and the frontend types/validators in the same
commit.

## Dev proxy

Vite proxies `/api/*` → `VITE_API_BASE` (default `http://localhost:8000`).
No API URLs are hard-coded in components — all calls go through `src/api/client.ts`.
Run `..\scripts\dev.ps1` from the repository root to start both dev servers.
For a production-style single port, build with `npm ci` and `npm run build`,
then run `..\scripts\build_and_serve.ps1`; FastAPI serves `frontend/dist` at
`http://localhost:8000`.

The hamburger drawer is a fixed overlay and does not reserve a permanent
sidebar grid column. When the drawer is closed, the chat area uses the full
available viewport width.

## Phase log

| Phase | Status | Description |
|-------|--------|-------------|
| F1 | ✅ Done | Scaffold: Vite + React + TS, types, client, mock, app shell |
| F2 | ✅ Done | Core chat experience in mock mode (sidebar, composer, transcript, cards, badges, tests) |
| F3 | ✅ Done | Evidence panels – SQL panel, data table, assumptions, chart, CSV download |
| F4 | ✅ Done | Visual polish, responsiveness (360px+), light/dark themes, full a11y (WCAG AA, axe) |
| F5 | ✅ Done | UI/UX Overhaul – Obsidian/Forest-Green aesthetic, Hamburger navigation drawer with multi-chat history, read-only dataset access information, unified "All Details" evidence container |
