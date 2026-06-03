export type SystemMode = "MANUAL" | "PROACTIVE";

export type TelemetryPoint = {
  timestamp: string;
  cpu: number;
  errorRate: number;
  isAnomaly: boolean;
};

export type ScorecardData = {
  faithfulness: number;
  contextRecall: number;
  tokenCost: number;
  latency: string;
};

export type IncidentData = {
  originalCode: string;
  proposedPatch: string;
  securityPassed: boolean;
  regexPassed: boolean;
};
