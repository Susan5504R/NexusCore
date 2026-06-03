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
import { API_BASE_URL } from "../lib/config";
import type { IncidentData, ScorecardData, SystemMode, TelemetryPoint } from "../lib/dashboardTypes";

export default function Dashboard() {
  const [theme, setTheme] = useState("palette1");
  const { run, isRunning, activeNode, logs, status, finalState } = useGraphStream();
  const [systemMode, setSystemMode] = useState<SystemMode>("MANUAL");
  const [telemetryData, setTelemetryData] = useState<TelemetryPoint[]>([]);
  const [scorecardMetrics, setScorecardMetrics] = useState<ScorecardData | null>(null);
  const [activeIncident, setActiveIncident] = useState<IncidentData | null>(null);

  // Apply theme to HTML tag
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "palette1" ? "palette2" : "palette1"));
  };

  const handleRun = (targetFile: string, logsArray: string[], projectPath: string, reproCommand: string) => {
    run(targetFile, logsArray, projectPath, reproCommand);
  };

  useEffect(() => {
    if (!finalState?.proposed_patch) return;

    setActiveIncident({
      originalCode: "// Original code unavailable in stream payload",
      proposedPatch: finalState.proposed_patch,
      securityPassed: Boolean(finalState.security_clearance),
      regexPassed: Boolean(finalState.security_clearance),
    });
  }, [finalState]);

  const handleSimulateOutlier = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/anomaly/simulate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer nexus-dev-key",
      },
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "Simulate outlier failed");
    }

    const data = await response.json().catch(() => ({}));

    if (Array.isArray(data.telemetry)) {
      setTelemetryData(data.telemetry);
    }

    if (data.scorecard) {
      setScorecardMetrics(data.scorecard);
    }

    if (data.incident) {
      setActiveIncident(data.incident);
    }
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
          <div className="flex gap-4">
            <button 
              onClick={toggleTheme}
              className="px-4 py-2 rounded-lg bg-base border border-surface hover:border-primary transition-all text-text-muted hover:text-text-main"
            >
              Swap to {theme === "palette1" ? "Palette 2" : "Palette 1"}
            </button>
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
            <TelemetryChart data={telemetryData} />
            <RunForm
              onRun={handleRun}
              isRunning={isRunning}
              systemMode={systemMode}
              onSystemModeChange={setSystemMode}
              onSimulateOutlier={handleSimulateOutlier}
            />
            <TerminalLog logs={logs} />
          </div>
        </div>

        {/* Bottom Row */}
        {activeIncident && <IncidentPanel incident={activeIncident} />}

      </div>
    </main>
  );
}
