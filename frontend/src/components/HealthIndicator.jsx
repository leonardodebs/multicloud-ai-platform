// HealthIndicator: bolinhas verde/amarelo/vermelho por cloud no cabeçalho.
import { CLOUDS, CLOUD_META } from "../constants";

const STATUS_COLOR = { ok: "#22c55e", error: "#ef4444", unknown: "#eab308" };

export default function HealthIndicator({ health }) {
  return (
    <div className="health-indicator">
      {CLOUDS.map((cloud) => {
        const status = health?.clouds?.[cloud] || "unknown";
        return (
          <span key={cloud} className="health-item" title={`${CLOUD_META[cloud].label}: ${status}`}>
            <span
              className="health-dot"
              style={{ background: STATUS_COLOR[status] || STATUS_COLOR.unknown }}
            />
            {CLOUD_META[cloud].short}
          </span>
        );
      })}
    </div>
  );
}
