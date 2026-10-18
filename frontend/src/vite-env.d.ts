/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Set to "true" to serve fixture data instead of hitting the real API. */
  readonly VITE_USE_MOCK: string;
  /** Override the backend base URL (default: http://localhost:8000). */
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
