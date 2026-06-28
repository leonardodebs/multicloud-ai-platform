// Configuração do Vite + plugin React + ambiente de testes (vitest).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // escuta em 0.0.0.0 (necessário dentro do container dev)
    // Em desenvolvimento, encaminha chamadas /api para o backend FastAPI.
    // O alvo é configurável para funcionar tanto localmente quanto no
    // docker-compose.dev (onde o backend é alcançado pelo nome do serviço).
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.js",
  },
});
