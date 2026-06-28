// StatsDashboard: total de consultas, latência média, custo total e cloud
// mais usado. Atualiza a cada consulta.
import { CLOUD_META } from "../constants";

function mostUsedCloud(byCloud) {
  const entries = Object.entries(byCloud || {});
  if (entries.length === 0) return "—";
  const [cloud] = entries.sort((a, b) => b[1] - a[1])[0];
  return CLOUD_META[cloud]?.label || cloud.toUpperCase();
}

export default function StatsDashboard({ stats }) {
  if (!stats) return null;
  return (
    <div className="stats-dashboard">
      <div className="stat-card">
        <span className="stat-value">{stats.total_queries}</span>
        <span className="stat-label">Consultas totais</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{Math.round(stats.avg_latency_ms)} ms</span>
        <span className="stat-label">Latência média</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">${Number(stats.total_cost_usd).toFixed(4)}</span>
        <span className="stat-label">Custo total</span>
      </div>
      <div className="stat-card">
        <span className="stat-value">{mostUsedCloud(stats.by_cloud)}</span>
        <span className="stat-label">Cloud mais usado</span>
      </div>
    </div>
  );
}
