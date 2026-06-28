// Metadados dos clouds usados em todos os componentes (cores, rótulos).

export const CLOUDS = ["aws", "oci", "gcp"];

export const CLOUD_META = {
  aws: { label: "AWS Bedrock", color: "#FF9900", short: "AWS" },
  oci: { label: "OCI GenAI", color: "#C74634", short: "OCI" },
  gcp: { label: "GCP Vertex AI", color: "#4285F4", short: "GCP" },
};

export const MODES = [
  {
    id: "compare",
    label: "Comparar",
    description:
      "Consulta os clouds selecionados em paralelo e mostra as respostas lado a lado.",
  },
  {
    id: "consensus",
    label: "Consenso",
    description:
      "Consulta todos em paralelo e usa o Claude para sintetizar uma resposta única.",
  },
  {
    id: "fastest",
    label: "Mais rápido",
    description:
      "Retorna apenas a primeira resposta válida e cancela as demais (menor latência).",
  },
];
