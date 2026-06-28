// Cliente HTTP para o backend. Todas as rotas passam por /api, que é
// encaminhado ao FastAPI pelo proxy do Vite (dev) ou pelo nginx (produção).

const BASE = "/api";

async function request(path, options = {}) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    throw new Error(`Erro ${resp.status} ao chamar ${path}`);
  }
  return resp.json();
}

export const api = {
  // Consulta multicloud nos modos compare/consensus/fastest.
  query: (question, clouds, mode) =>
    request("/query", {
      method: "POST",
      body: JSON.stringify({ question, clouds, mode }),
    }),

  // Saúde por cloud (para o HealthIndicator).
  health: () => request("/health"),

  // Estatísticas agregadas (para o StatsDashboard).
  stats: () => request("/stats"),

  // Modelos disponíveis por cloud.
  models: () => request("/models"),
};
