import { ScorecardData } from "../lib/dashboardTypes";

type ScorecardProps = {
  metrics: ScorecardData | null;
};

const formatTokens = (value?: number) => {
  if (value === undefined || value === null) return "--";
  return value.toLocaleString();
};

const formatLatency = (value?: number) => {
  if (value === undefined || value === null) return "--";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(1)}s`;
};

const formatRetries = (value?: number) => {
  if (value === undefined || value === null) return "--";
  return `${value}`;
};

const OUTCOME_LABEL: Record<ScorecardData["outcome"], string> = {
  success: "Verified",
  blocked: "Blocked",
  failed: "Failed",
};

export function SreScorecard({ metrics }: ScorecardProps) {
  const outcome = metrics?.outcome;
  const outcomeColor =
    outcome === "success"
      ? "text-success drop-shadow-[0_0_10px_rgba(74,222,128,0.35)]"
      : outcome
      ? "text-error drop-shadow-[0_0_10px_rgba(239,68,68,0.35)]"
      : "text-[#f3d6c7] drop-shadow-[0_0_10px_rgba(243,214,199,0.35)]";

  const cards = [
    { label: "Tokens Used", value: formatTokens(metrics?.tokensUsed), color: null },
    { label: "Execution Latency", value: formatLatency(metrics?.latencyMs), color: null },
    { label: "Retry Cycles", value: formatRetries(metrics?.retryCount), color: null },
    { label: "Outcome", value: outcome ? OUTCOME_LABEL[outcome] : "--", color: outcomeColor },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-2xl border border-primary/20 bg-[#2c130d] px-5 py-4 shadow-lg"
        >
          <p className="text-xs uppercase tracking-wide text-text-muted">{card.label}</p>
          <p
            className={`mt-2 text-2xl font-semibold ${
              card.color ?? "text-[#f3d6c7] drop-shadow-[0_0_10px_rgba(243,214,199,0.35)]"
            }`}
          >
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
}
