"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchLedgerLogs } from "../lib/systemClient";
import type { LedgerEntry } from "../lib/dashboardTypes";

type LedgerHistoryProps = {
  /** Change this value (e.g. the latest finalState) to trigger a reload. */
  reloadKey?: unknown;
};

function statusBadge(status?: string | null): string {
  switch (status) {
    case "success":
      return "bg-success/15 text-success border-success/30";
    case "blocked_security":
      return "bg-error/15 text-error border-error/30";
    case "failed":
      return "bg-error/15 text-error border-error/30";
    default:
      return "bg-text-muted/10 text-text-muted border-text-muted/20";
  }
}

function formatTime(ts?: string | null): string {
  if (!ts) return "--";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function LedgerHistory({ reloadKey }: LedgerHistoryProps) {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Manual refresh (button) — setState in an event handler is fine.
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEntries(await fetchLedgerLogs(20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load on mount and whenever a run completes. setState happens only after
  // the await so we don't synchronously re-render from inside the effect.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchLedgerLogs(20);
        if (!cancelled) {
          setEntries(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load history");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <div className="rounded-2xl border border-primary/20 bg-surface p-6 shadow-xl space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <h2 className="text-xl font-semibold text-text-main">Operational Ledger</h2>
        <span className="text-xs uppercase tracking-widest text-text-muted ml-auto mr-2">Audit Trail</span>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          title="Refresh"
          className="p-1.5 rounded-lg text-text-muted hover:text-primary hover:bg-base/70 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error ? (
        <p className="text-sm text-error">{error}</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-text-muted italic">
          {loading ? "Loading history…" : "No runs recorded yet (or ledger not configured)."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-text-muted border-b border-primary/10">
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium">Action</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium text-right">Tokens</th>
                <th className="py-2 pr-4 font-medium text-right">Latency</th>
                <th className="py-2 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.id ?? i} className="border-b border-primary/5 last:border-0">
                  <td className="py-2 pr-4 text-text-muted whitespace-nowrap">{formatTime(e.timestamp)}</td>
                  <td className="py-2 pr-4 text-text-main whitespace-nowrap">{e.agent_action ?? "--"}</td>
                  <td className="py-2 pr-4">
                    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs ${statusBadge(e.execution_status)}`}>
                      {e.execution_status ?? "unknown"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-text-main/80">
                    {e.token_consumption.toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-text-main/80">{e.compute_latency_ms}ms</td>
                  <td className="py-2 text-text-muted max-w-[280px] truncate" title={e.execution_payload ?? ""}>
                    {e.execution_payload ?? "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
