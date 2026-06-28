// CloudSelector: checkboxes AWS/OCI/GCP com badges de latência da última consulta.
import { CLOUDS, CLOUD_META } from "../constants";

export default function CloudSelector({ selected, onChange, latencies }) {
  const toggle = (cloud) => {
    if (selected.includes(cloud)) {
      onChange(selected.filter((c) => c !== cloud));
    } else {
      onChange([...selected, cloud]);
    }
  };

  return (
    <div className="cloud-selector">
      {CLOUDS.map((cloud) => {
        const meta = CLOUD_META[cloud];
        const latency = latencies?.[cloud];
        return (
          <label
            key={cloud}
            className="cloud-chip"
            style={{ borderColor: selected.includes(cloud) ? meta.color : "#444" }}
          >
            <input
              type="checkbox"
              checked={selected.includes(cloud)}
              onChange={() => toggle(cloud)}
            />
            <span className="cloud-dot" style={{ background: meta.color }} />
            <span className="cloud-name">{meta.label}</span>
            {latency != null && (
              <span className="latency-badge">{Math.round(latency)} ms</span>
            )}
          </label>
        );
      })}
    </div>
  );
}
