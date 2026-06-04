"use client";

import { useState, useEffect } from "react";
import { useGraphStream } from "../hooks/useGraphStream";
import { NodeStatusPanel } from "../components/NodeStatusPanel";
import { TerminalLog } from "../components/TerminalLog";
import { StatusBanner } from "../components/StatusBanner";
import { IngestPanel } from "../components/IngestPanel";
import { RunForm } from "../components/RunForm";
import { TelemetryChart } from "../components/TelemetryChart";
import { SreScorecard } from "../components/SreScorecard";
import { IncidentPanel } from "../components/IncidentPanel";
import { ContextPanel } from "../components/ContextPanel";
import { HealthStrip } from "../components/HealthStrip";
import { LedgerHistory } from "../components/LedgerHistory";
import type { IncidentData, ScorecardData, SystemMode, TelemetryPoint } from "../lib/dashboardTypes";

export default function Dashboard() {
  const { run, isRunning, activeNode, logs, status, finalState } = useGraphStream();
  const [systemMode, setSystemMode] = useState<SystemMode>("MANUAL");
  const [telemetryData, setTelemetryData] = useState<TelemetryPoint[]>([]);
  const [features, setFeatures] = useState<{ local_ingest?: boolean, api_keys?: boolean }>({});

  // Apply default theme to HTML tag
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "palette1");
    import("../lib/systemClient").then(({ fetchSystemMode }) => {
      fetchSystemMode()
        .then(data => setFeatures(data.features || {}))
        .catch(console.error);
    });
  }, []);

  const handleRun = (targetFile: string, logsArray: string[], projectPath: string, reproCommand: string) => {
    run(targetFile, logsArray, projectPath, reproCommand);
  };

  // Scorecard and incident are pure functions of the completed run, so we derive
  // them during render rather than mirroring finalState into extra state.
  const cleared = Boolean(finalState?.security_clearance);
  const scorecardMetrics: ScorecardData | null = finalState
    ? {
        tokensUsed: finalState.token_consumption ?? 0,
        latencyMs: finalState.latency_ms ?? 0,
        retryCount: finalState.retry_count ?? 0,
        outcome: !cleared
          ? "blocked"
          : (finalState.execution_exit_code ?? -1) === 0
          ? "success"
          : "failed",
      }
    : null;

  const activeIncident: IncidentData | null = finalState?.proposed_patch
    ? {
        originalCode: finalState.original_code ?? "",
        proposedPatch: finalState.proposed_patch,
        securityPassed: cleared,
        regexPassed: cleared,
      }
    : null;

  const handleSimulateOutlier = async () => {
    // 1. Generate local mock telemetry showing the spike
    const now = new Date();
    const mockTelemetry = [];
    for (let i = 0; i < 10; i++) {
      const t = new Date(now.getTime() - (10 - i) * 60000);
      mockTelemetry.push({
        timestamp: t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        cpu: 30 + (i % 3) * 5,
        errorRate: 1 + (i % 2),
        isAnomaly: false
      });
    }
    // Add anomaly
    mockTelemetry.push({
      timestamp: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      cpu: 98,
      errorRate: 85,
      isAnomaly: true
    });
    
    setTelemetryData(mockTelemetry);

    // 2. Trigger the ACTUAL LangGraph agent to handle the anomaly
    const mockLogs = ["SYSTEM ANOMALY TRIPPED: Elevated resource usage detected.", "CPU=98.0%, Mem=84.2%, ErrRate=85.0"];
    const mockTarget = "system_metrics";
    const mockPath = "workspaces/default/codebase";
    const mockCmd = "python main.py";

    // Wait a brief moment to let the user see the telemetry spike before the agent takes over
    setTimeout(() => {
      run(mockTarget, mockLogs, mockPath, mockCmd);
    }, 1500);
  };

  return (
    <main className="min-h-screen p-8 transition-colors duration-500">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center bg-surface p-6 rounded-2xl shadow-xl border border-primary/30">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-error drop-shadow-md">
              NexusCore SRE
            </h1>
            <p className="text-text-main/90 font-medium mt-1">Autonomous Infrastructure Self-Healing</p>
          </div>
          <div className="flex items-center gap-6">
            {features.api_keys && (
              <a href="/settings" className="text-sm font-semibold text-primary hover:underline">
                Settings / API Keys
              </a>
            )}
            <HealthStrip />
          </div>
        </div>

        {/* Component A */}
        <SreScorecard metrics={scorecardMetrics} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-1 space-y-6">
            <IngestPanel />
            <NodeStatusPanel activeNode={activeNode} />
            <StatusBanner status={status} />
          </div>

          {/* Center & Right Column (Span 2) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TelemetryChart data={telemetryData} />
              <RunForm
                onRun={handleRun}
                isRunning={isRunning}
                systemMode={systemMode}
                onSystemModeChange={setSystemMode}
                onSimulateOutlier={handleSimulateOutlier}
              />
            </div>
            <TerminalLog logs={logs} />
          </div>
        </div>

        {/* Bottom Row */}
        {activeIncident && <IncidentPanel incident={activeIncident} />}

        <ContextPanel />

        <LedgerHistory reloadKey={finalState} />

      </div>
    </main>
  );
}
