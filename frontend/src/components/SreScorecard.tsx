import { ScorecardData } from "../lib/dashboardTypes";

type ScorecardProps = {
  metrics: ScorecardData | null;
};

const formatPercent = (value?: number) => {
  if (value === undefined || value === null) return "--";
  return `${Math.round(value * 100)}%`;
};

const formatCost = (value?: number) => {
  if (value === undefined || value === null) return "--";
  return `$${value.toFixed(3)}`;
};

const formatLatency = (value?: string) => {
  if (!value) return "--";
  return value;
};

export function SreScorecard({ metrics }: ScorecardProps) {
  const cards = [
    { label: "Faithfulness", value: formatPercent(metrics?.faithfulness) },
    { label: "Context Recall", value: formatPercent(metrics?.contextRecall) },
    { label: "Token Cost", value: formatCost(metrics?.tokenCost) },
    { label: "Execution Latency", value: formatLatency(metrics?.latency) },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-2xl border border-primary/20 bg-[#2c130d] px-5 py-4 shadow-lg"
        >
          <p className="text-xs uppercase tracking-wide text-text-muted">{card.label}</p>
          <p className="mt-2 text-2xl font-semibold text-[#f3d6c7] drop-shadow-[0_0_10px_rgba(243,214,199,0.35)]">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
}
