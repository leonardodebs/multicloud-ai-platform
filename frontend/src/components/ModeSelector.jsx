// ModeSelector: escolhe comparar/consenso/mais rápido com tooltip de descrição.
import { MODES } from "../constants";

export default function ModeSelector({ mode, onChange }) {
  return (
    <div className="mode-selector">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          title={m.description}
          className={`mode-btn ${mode === m.id ? "active" : ""}`}
          onClick={() => onChange(m.id)}
        >
          {m.label}
        </button>
      ))}
      <p className="mode-description">
        {MODES.find((m) => m.id === mode)?.description}
      </p>
    </div>
  );
}
