"use client";

import { useState, useEffect } from "react";

interface RunFormProps {
  onRun: (targetFile: string, logs: string[], projectPath: string, reproCommand: string) => void;
  isRunning: boolean;
}

export function RunForm({ onRun, isRunning }: RunFormProps) {
  const [namespace, setNamespace] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [targetFile, setTargetFile] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [reproCommand, setReproCommand] = useState("");
  const [logs, setLogs] = useState("");
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  const fetchFiles = async () => {
    setLoadingFiles(true);
    setFetchError(false);
    try {
      const url = namespace ? `http://127.0.0.1:8000/api/v1/ingest/files?namespace=${encodeURIComponent(namespace)}` : "http://127.0.0.1:8000/api/v1/ingest/files";
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
    if (!targetFile || !projectPath || !reproCommand || !logs) return;
    
    const logsArray = logs.split("\n").filter(l => l.trim() !== "");
    onRun(targetFile, logsArray, projectPath, reproCommand);
  };

  return (
    <div className="bg-surface p-5 rounded-2xl shadow-lg border border-primary/20 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-error animate-pulse" />
        <h2 className="text-lg font-bold text-text-main">Trigger Anomaly</h2>
      </div>

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
              <label className="block text-xs text-text-muted font-medium">Target File</label>
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
              required
              className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors"
            >
              <option value="" disabled>
                {loadingFiles ? "Loading files..." : fetchError ? "Error loading files" : files.length === 0 ? "No files ingested" : "Select target file"}
              </option>
              {files.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-text-muted mb-1 font-medium">Project Root Path</label>
          <input
            type="text"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            placeholder="C:\Users\...\MyProject"
            required
            className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
          />
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
          disabled={isRunning || !targetFile}
          className={`w-full py-2 rounded-lg font-semibold transition-all duration-300 ${
            isRunning || !targetFile
            ? "bg-surface text-text-muted cursor-not-allowed border border-surface" 
            : "bg-error text-white hover:opacity-90 hover:scale-[1.02] shadow-[0_0_15px_var(--error)]"
          }`}
        >
          {isRunning ? "Cycle Active..." : "Run Repair Graph"}
        </button>
      </form>
    </div>
  );
}
