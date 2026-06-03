"use client";

import { useState, useEffect } from "react";
import { useGraphStream } from "../hooks/useGraphStream";
import { NodeStatusPanel } from "../components/NodeStatusPanel";
import { TerminalLog } from "../components/TerminalLog";
import { StatusBanner } from "../components/StatusBanner";
import { IngestPanel } from "../components/IngestPanel";
import { RunForm } from "../components/RunForm";

export default function Dashboard() {
  const [theme, setTheme] = useState("palette1");
  const { run, isRunning, activeNode, logs, status } = useGraphStream();

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

        {/* Configuration Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <IngestPanel />
          <RunForm onRun={handleRun} isRunning={isRunning} />
        </div>

        {/* Execution & Status Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1 space-y-6">
            <NodeStatusPanel activeNode={activeNode} />
            <StatusBanner status={status} />
          </div>
          <TerminalLog logs={logs} />
        </div>

      </div>
    </main>
  );
}
