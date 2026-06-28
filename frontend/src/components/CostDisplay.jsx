// CostDisplay: custo total acumulado com detalhamento por cloud.
import { CLOUD_META } from "../constants";

export default function CostDisplay({ results, totalCost }) {
  const entries = Object.entries(results || {});
  if (entries.length === 0) return null;

  return (
    <div className="cost-display">
      <h3>Custo desta consulta</h3>
      <div className="cost-total">${Number(totalCost || 0).toFixed(6)}</div>
      <ul className="cost-breakdown">
        {entries.map(([cloud, r]) => {
          const meta = CLOUD_META[cloud] || { label: cloud, color: "#888" };
          return (
            <li key={cloud}>
              <span className="cloud-dot" style={{ background: meta.color }} />
              {meta.label}
              <span className="cost-value">${Number(r.cost_usd || 0).toFixed(6)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
