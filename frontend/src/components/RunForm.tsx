"use client";

import { useState, useEffect } from "react";
import { ShieldAlert, Info } from "lucide-react";
import { API_BASE_URL } from "../lib/config";

interface RunFormProps {
  onRun: (targetFile: string, logs: string[], projectPath: string, reproCommand: string, namespace?: string) => void;
  isRunning: boolean;
  systemMode: "MANUAL" | "PROACTIVE";
  onSystemModeChange: (mode: "MANUAL" | "PROACTIVE") => void;
  onSimulateOutlier: () => Promise<void>;
}

export function RunForm({ onRun, isRunning, systemMode, onSystemModeChange, onSimulateOutlier }: RunFormProps) {
  const [namespace, setNamespace] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [targetFile, setTargetFile] = useState("");
  const [reproCommand, setReproCommand] = useState("");
  const [logs, setLogs] = useState("");
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [simulateStatus, setSimulateStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [simulateError, setSimulateError] = useState<string | null>(null);

  const fetchFiles = async () => {
    setLoadingFiles(true);
    setFetchError(false);
    try {
      const url = namespace ? `${API_BASE_URL}/api/v1/ingest/files?namespace=${encodeURIComponent(namespace)}` : `${API_BASE_URL}/api/v1/ingest/files`;
      const res = await fetch(url, {
        headers: {
          "Authorization": "Bearer nexus-dev-key"
        }
      });
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
        if (data.files?.length > 0 && !targetFile) {
          setTargetFile(data.files[0]);
        }
      } else {
        setFetchError(true);
      }
    } catch (e) {
      console.error("Failed to fetch ingested files", e);
      setFetchError(true);
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [namespace]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reproCommand || !logs) return;
    
    const logsArray = logs.split("\n").filter(l => l.trim() !== "");
    const safeNamespace = namespace.trim() || "default";
    const resolvedProjectPath = `workspaces/${safeNamespace}/codebase`;
    
    onRun(targetFile || "AUTO_DETECT", logsArray, resolvedProjectPath, reproCommand, safeNamespace);
  };

  const handleSimulate = async () => {
    setSimulateStatus("loading");
    setSimulateError(null);
    try {
      await onSimulateOutlier();
      setSimulateStatus("success");
    } catch (error: any) {
      setSimulateStatus("error");
      setSimulateError(error?.message || "Failed to simulate outlier");
    }
  };

  return (
    <div className="bg-surface p-5 rounded-2xl shadow-lg border border-primary/20 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-error animate-pulse" />
          <h2 className="text-lg font-bold text-text-main">Anomaly Control</h2>
        </div>
        <div className="flex bg-base/70 border border-primary/20 rounded-full p-1 text-xs">
          <button
            type="button"
            onClick={() => onSystemModeChange("MANUAL")}
            className={`px-3 py-1 rounded-full transition-colors ${
              systemMode === "MANUAL"
                ? "bg-primary text-base"
                : "text-text-muted hover:text-text-main"
            }`}
          >
              Manual Triage
          </button>
          <button
            type="button"
            onClick={() => onSystemModeChange("PROACTIVE")}
            className={`px-3 py-1 rounded-full transition-colors ${
              systemMode === "PROACTIVE"
                ? "bg-primary text-base"
                : "text-text-muted hover:text-text-main"
            }`}
          >
              Proactive Sentinel
          </button>
        </div>
      </div>

      {systemMode === "MANUAL" ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-text-muted mb-1 font-medium">Namespace (Filter)</label>
              <input
                type="text"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                placeholder="Leave empty for all"
                className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs text-text-muted font-medium">Target File (Optional - Auto-Detect)</label>
                <button
                  type="button"
                  onClick={fetchFiles}
                  className="text-[10px] text-primary hover:underline focus:outline-none"
                >
                  {loadingFiles ? "Loading..." : "Refresh"}
                </button>
              </div>
              <select
                value={targetFile}
                onChange={(e) => setTargetFile(e.target.value)}
                className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors"
              >
                <option value="">
                  {loadingFiles ? "Loading files..." : fetchError ? "Error loading files" : files.length === 0 ? "No files ingested (Auto-Detect)" : "Select target file or leave blank"}
                </option>
                {files.map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Reproduction Command</label>
            <input
              type="text"
              value={reproCommand}
              onChange={(e) => setReproCommand(e.target.value)}
              placeholder="python main.py"
              required
              className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main font-mono focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Crash Logs</label>
            <textarea
              value={logs}
              onChange={(e) => setLogs(e.target.value)}
              placeholder="Paste stack trace or error logs here..."
              required
              rows={4}
              className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main font-mono focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50 resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={isRunning}
            className={`w-full py-2 rounded-lg font-semibold transition-all duration-300 ${
              isRunning
              ? "bg-surface text-text-muted cursor-not-allowed border border-surface"
              : "bg-error text-white hover:opacity-90 hover:scale-[1.02] shadow-[0_0_15px_var(--error)]"
            }`}
          >
            {isRunning ? "Cycle Active..." : "Run Repair Graph"}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-xl border border-primary/30 bg-base/60 px-4 py-5">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-primary/30 blur-xl animate-pulse" />
                <ShieldAlert className="relative h-8 w-8 text-primary" />
              </div>
              <div>
                <p className="text-sm text-text-muted flex items-center gap-2">
                  Proactive Sentinel
                </p>
                <p className="text-lg font-semibold text-text-main">
                  {simulateStatus === "loading" ? "Simulating..." : "Monitoring active..."}
                </p>
              </div>
            </div>
            
            <button
              type="button"
              onClick={handleSimulate}
              disabled={simulateStatus === "loading"}
              title="Simulate Outlier"
              className="p-2 rounded-full text-text-muted hover:text-primary hover:bg-surface transition-colors focus:outline-none"
            >
              <Info className="w-5 h-5" />
            </button>
          </div>

          {simulateStatus === "error" && simulateError && (
            <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm">
              <p className="text-error font-semibold">Simulation failed</p>
              <p className="text-text-muted mt-1 text-xs break-words">{simulateError}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
