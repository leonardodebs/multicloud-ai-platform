// LatencyChart: gráfico de barras horizontais (Recharts) comparando os tempos
// de resposta dos clouds da última consulta.
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { CLOUD_META } from "../constants";

export default function LatencyChart({ results }) {
  const data = Object.entries(results || {})
    .filter(([, r]) => r.latency_ms)
    .map(([cloud, r]) => ({
      cloud: CLOUD_META[cloud]?.short || cloud.toUpperCase(),
      color: CLOUD_META[cloud]?.color || "#888",
      latency: Math.round(r.latency_ms),
    }));

  if (data.length === 0) return null;

  return (
    <div className="chart-box">
      <h3>Latência (ms)</h3>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 60)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
          <XAxis type="number" stroke="#aaa" />
          <YAxis type="category" dataKey="cloud" stroke="#aaa" width={50} />
          <Tooltip
            formatter={(v) => [`${v} ms`, "Latência"]}
            contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }}
          />
          <Bar dataKey="latency" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
