"use client";

import { useState } from "react";
import { API_BASE_URL } from "../lib/config";

export function IngestPanel() {
  const [activeTab, setActiveTab] = useState<"github" | "zip">("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [namespace, setNamespace] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<{ files: number; chunks: number; time: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setResult(null);
    setError(null);

    try {
      let response;
      if (activeTab === "github") {
        if (!githubUrl.trim()) throw new Error("URL required");
        response = await fetch(`${API_BASE_URL}/api/v1/ingest/github`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer nexus-dev-key" },
          body: JSON.stringify({ github_url: githubUrl.trim(), namespace: namespace.trim() || null }),
        });
      } else if (activeTab === "zip") {
        if (!file) throw new Error("File required");
        const formData = new FormData();
        formData.append("file", file);
        if (namespace.trim()) formData.append("namespace", namespace.trim());
        response = await fetch(`${API_BASE_URL}/api/v1/ingest/upload`, {
          method: "POST",
          headers: { "Authorization": "Bearer nexus-dev-key" },
          body: formData,
        });
      }

      if (!response || !response.ok) {
        const errData = await response?.json().catch(() => ({}));
        throw new Error(errData?.detail || "Ingestion failed");
      }

      const data = await response.json();
      setResult({ files: data.files_processed, chunks: data.chunks_indexed, time: data.elapsed_ms });
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

      <div className="flex gap-2 border-b border-surface pb-2">
        {(["github", "zip"] as const).map(tab => (
          <button
            key={tab}
            type="button"
            onClick={() => { setActiveTab(tab); setStatus("idle"); }}
            className={`px-3 py-1 text-sm rounded-lg font-medium transition-colors ${
              activeTab === tab ? "bg-primary text-surface" : "text-text-muted hover:text-text-main hover:bg-surface"
            }`}
          >
            {tab === "github" ? "GitHub URL" : "ZIP Upload"}
          </button>
        ))}
      </div>
      
      <form onSubmit={handleIngest} className="space-y-3">

        {activeTab === "github" && (
          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">GitHub Repository URL</label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
              className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors placeholder:text-text-muted/50"
              required={activeTab === "github"}
            />
          </div>
        )}

        {activeTab === "zip" && (
          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Upload ZIP File</label>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full bg-base border border-surface rounded-lg px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary transition-colors file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
              required={activeTab === "zip"}
            />
          </div>
        )}

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
          disabled={status === "loading" || (activeTab === "github" && !githubUrl) || (activeTab === "zip" && !file)}
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
