// ResultCards: respostas dos clouds lado a lado com modelo, latência, custo
// e uma avaliação de "qualidade" em estrelas (heurística simples).
import { CLOUD_META } from "../constants";

// Heurística de qualidade: combina tamanho da resposta (mais detalhe) e
// latência (mais rápido é melhor). Retorna 1..5 estrelas.
function qualityStars(result, allResults) {
  if (!result || result.error || !result.answer) return 0;
  const lengths = allResults.filter((r) => r.answer).map((r) => r.answer.length);
  const latencies = allResults.filter((r) => r.latency_ms).map((r) => r.latency_ms);
  const maxLen = Math.max(...lengths, 1);
  const minLat = Math.min(...latencies, result.latency_ms || 1);

  const lenScore = (result.answer.length / maxLen) * 3; // 0..3
  const latScore = (minLat / (result.latency_ms || minLat)) * 2; // 0..2
  return Math.max(1, Math.min(5, Math.round(lenScore + latScore)));
}

function Stars({ count }) {
  return (
    <span className="stars" title={`${count} de 5`}>
      {"★".repeat(count)}
      {"☆".repeat(5 - count)}
    </span>
  );
}

export default function ResultCards({ results }) {
  const entries = Object.entries(results || {});
  if (entries.length === 0) return null;

  const allResults = entries.map(([, r]) => r);

  return (
    <div className="result-cards">
      {entries.map(([cloud, r]) => {
        const meta = CLOUD_META[cloud] || { label: cloud, color: "#888" };
        return (
          <div key={cloud} className="result-card" style={{ borderTopColor: meta.color }}>
            <div className="result-header">
              <span className="cloud-dot" style={{ background: meta.color }} />
              <strong>{meta.label}</strong>
              {!r.error && <Stars count={qualityStars(r, allResults)} />}
            </div>

            {r.error ? (
              <p className="result-error">⚠️ {r.error}</p>
            ) : (
              <p className="result-answer">{r.answer}</p>
            )}

            <div className="result-meta">
              <span>🧠 {r.model}</span>
              <span>⚡ {Math.round(r.latency_ms)} ms</span>
              <span>🪙 {r.tokens} tokens</span>
              <span>💲 ${Number(r.cost_usd).toFixed(6)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
