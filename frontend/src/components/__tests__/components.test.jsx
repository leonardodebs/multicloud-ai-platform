// Testes de componentes (vitest + testing-library).
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CloudSelector from "../CloudSelector";
import ModeSelector from "../ModeSelector";
import ResultCards from "../ResultCards";
import HealthIndicator from "../HealthIndicator";
import StatsDashboard from "../StatsDashboard";

describe("CloudSelector", () => {
  it("alterna a seleção de um cloud ao clicar", () => {
    const onChange = vi.fn();
    render(<CloudSelector selected={["aws"]} onChange={onChange} latencies={{}} />);
    fireEvent.click(screen.getByText("OCI GenAI"));
    expect(onChange).toHaveBeenCalledWith(["aws", "oci"]);
  });

  it("mostra o badge de latência quando disponível", () => {
    render(
      <CloudSelector selected={["aws"]} onChange={() => {}} latencies={{ aws: 420 }} />
    );
    expect(screen.getByText("420 ms")).toBeInTheDocument();
  });
});

describe("ModeSelector", () => {
  it("dispara onChange ao trocar de modo", () => {
    const onChange = vi.fn();
    render(<ModeSelector mode="compare" onChange={onChange} />);
    fireEvent.click(screen.getByText("Consenso"));
    expect(onChange).toHaveBeenCalledWith("consensus");
  });
});

describe("ResultCards", () => {
  it("renderiza resposta e metadados de cada cloud", () => {
    const results = {
      aws: { answer: "resposta aws", model: "claude", latency_ms: 300, tokens: 50, cost_usd: 0.0001 },
      gcp: { error: "falhou", latency_ms: 0, model: "gemini" },
    };
    render(<ResultCards results={results} />);
    expect(screen.getByText("resposta aws")).toBeInTheDocument();
    expect(screen.getByText("⚠️ falhou")).toBeInTheDocument();
  });
});

describe("HealthIndicator", () => {
  it("renderiza os três clouds", () => {
    render(<HealthIndicator health={{ clouds: { aws: "ok", oci: "error", gcp: "ok" } }} />);
    expect(screen.getByText("AWS")).toBeInTheDocument();
    expect(screen.getByText("OCI")).toBeInTheDocument();
    expect(screen.getByText("GCP")).toBeInTheDocument();
  });
});

describe("StatsDashboard", () => {
  it("mostra o total de consultas", () => {
    render(
      <StatsDashboard
        stats={{ total_queries: 7, avg_latency_ms: 420, total_cost_usd: 0.01, by_cloud: { aws: 5, gcp: 2 } }}
      />
    );
    expect(screen.getByText("7")).toBeInTheDocument();
  });
});
