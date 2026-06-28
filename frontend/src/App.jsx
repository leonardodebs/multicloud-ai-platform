// App principal: orquestra os componentes e o estado da interface unificada.
import { useEffect, useState, useCallback } from "react";
import { api } from "./api";
import { CLOUDS } from "./constants";
import CloudSelector from "./components/CloudSelector";
import ModeSelector from "./components/ModeSelector";
import QueryInput from "./components/QueryInput";
import ResultCards from "./components/ResultCards";
import LatencyChart from "./components/LatencyChart";
import CostDisplay from "./components/CostDisplay";
import StatsDashboard from "./components/StatsDashboard";
import HealthIndicator from "./components/HealthIndicator";

export default function App() {
  const [selected, setSelected] = useState(CLOUDS);
  const [mode, setMode] = useState("compare");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);

  // Latências da última consulta, por cloud (para os badges do CloudSelector).
  const latencies = {};
  if (response?.results) {
    for (const [cloud, r] of Object.entries(response.results)) {
      latencies[cloud] = r.latency_ms;
    }
  }

  const refreshSideData = useCallback(async () => {
    try {
      const [h, s] = await Promise.all([api.health(), api.stats()]);
      setHealth(h);
      setStats(s);
    } catch {
      // Falha ao buscar saúde/stats não bloqueia a interface.
    }
  }, []);

  // Carrega saúde dos clouds e estatísticas ao iniciar.
  useEffect(() => {
    refreshSideData();
  }, [refreshSideData]);

  const handleSubmit = async (question) => {
    if (selected.length === 0) {
      setError("Selecione ao menos um cloud.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.query(question, selected, mode);
      setResponse(data);
      await refreshSideData(); // atualiza dashboard após a consulta
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>☁️ Multicloud AI Platform</h1>
        <HealthIndicator health={health} />
      </header>

      <p className="subtitle">
        Consulte <strong>AWS Bedrock</strong>, <strong>OCI GenAI</strong> e{" "}
        <strong>GCP Vertex AI</strong> simultaneamente.
      </p>

      <StatsDashboard stats={stats} />

      <section className="controls">
        <CloudSelector selected={selected} onChange={setSelected} latencies={latencies} />
        <ModeSelector mode={mode} onChange={setMode} />
        <QueryInput onSubmit={handleSubmit} loading={loading} />
        {error && <p className="app-error">{error}</p>}
      </section>

      {response?.consensus && (
        <section className="consensus-box">
          <h3>🤝 Resposta de consenso (sintetizada pelo Claude)</h3>
          <p>{response.consensus}</p>
        </section>
      )}

      {response && (
        <section className="results-section">
          <ResultCards results={response.results} />
          <div className="charts-row">
            <LatencyChart results={response.results} />
            <CostDisplay results={response.results} totalCost={response.total_cost_usd} />
          </div>
        </section>
      )}

      <footer className="app-footer">
        Projeto de portfólio — FastAPI async · React · Recharts · Docker · ECS Fargate · Terraform
      </footer>
    </div>
  );
}
