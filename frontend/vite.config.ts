import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    proxy:
      mode !== "test"
        ? {
            "/api": {
              target:
                loadEnv(mode, process.cwd(), "VITE_").VITE_API_BASE ??
                "http://localhost:8000",
              changeOrigin: true,
            },
          }
        : undefined,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
}));
