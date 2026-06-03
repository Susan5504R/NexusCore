"use client";

import { useState } from "react";

export function IngestPanel() {
  const [path, setPath] = useState("");
  const [namespace, setNamespace] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<{ files: number; chunks: number; time: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!path.trim()) return;

    setStatus("loading");
    setResult(null);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/ingest", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": "Bearer nexus-dev-key"
        },
        body: JSON.stringify({
          directory_path: path.trim(),
          namespace: namespace.trim() || null,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Ingestion failed");
      }

      const data = await response.json();
      setResult({
        files: data.files_processed,
        chunks: data.chunks_indexed,
        time: data.elapsed_ms,
      });
      setStatus("success");
    } catch (err: any) {
      setError(err.message || "An unknown error occurred");
      setStatus("error");
    }
  };

  return (
    <div className="bg-surface p-5 rounded-2xl shadow-lg border border-primary/20 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <h2 className="text-lg font-bold text-text-main">Ingest Project</h2>
      </div>
      
      <form onSubmit={handleIngest} className="space-y-3">
        <div>
          <label className="block text-xs text-text-muted mb-1 font-medium">Local Directory Path</label>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="C:\Users\..."
            className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
            required
          />
        </div>
        <div>
          <label className="block text-xs text-text-muted mb-1 font-medium">Namespace (Optional)</label>
          <input
            type="text"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            placeholder="my-project"
            className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
          />
        </div>
        <button
          type="submit"
          disabled={status === "loading" || !path.trim()}
          className="w-full bg-surface border border-primary/30 hover:border-primary text-text-main py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/10"
        >
          {status === "loading" ? "Ingesting..." : "Run Ingestion"}
        </button>
      </form>

      {status === "success" && result && (
        <div className="p-3 bg-success/10 border border-success/30 rounded-lg text-sm">
          <p className="text-success font-semibold flex items-center gap-2">
            <span>✓</span> Ingestion Complete
          </p>
          <ul className="text-text-muted mt-2 space-y-1 text-xs">
            <li>Files processed: <span className="text-text-main font-mono">{result.files}</span></li>
            <li>Chunks indexed: <span className="text-text-main font-mono">{result.chunks}</span></li>
            <li>Time elapsed: <span className="text-text-main font-mono">{result.time}ms</span></li>
          </ul>
        </div>
      )}

      {status === "error" && error && (
        <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm">
          <p className="text-error font-semibold flex items-center gap-2">
            <span>✗</span> Error
          </p>
          <p className="text-text-muted mt-1 text-xs break-words">{error}</p>
        </div>
      )}
    </div>
  );
}
