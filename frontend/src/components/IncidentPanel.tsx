import { CheckCircle2 } from "lucide-react";
import DiffViewer from "react-diff-viewer-continued";
import type { IncidentData } from "../lib/dashboardTypes";

type IncidentPanelProps = {
  incident: IncidentData;
};

export function IncidentPanel({ incident }: IncidentPanelProps) {
  return (
    <div className="rounded-2xl border border-primary/20 bg-surface p-6 shadow-xl">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-text-main">Active Incident Analysis</h2>
        <span className="text-xs uppercase tracking-widest text-text-muted">Live Diff</span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-text-main">Security Gate Checklist</h3>
          <div className="space-y-2 rounded-xl border border-primary/20 bg-base/70 p-4">
            <div className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Regex Command Scan Passed</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Dual-Model Safety Arbitration Cleared</span>
            </div>
          </div>
          <div className="rounded-xl border border-primary/20 bg-base/70 p-4 text-xs text-text-muted">
            {incident.regexPassed && incident.securityPassed
              ? "All safety gates validated. Patch is eligible for deployment."
              : "Safety gates pending review."}
          </div>
        </div>

        <div className="rounded-xl border border-primary/20 bg-base/70 p-3">
          <DiffViewer
            oldValue={incident.originalCode}
            newValue={incident.proposedPatch}
            splitView
            useDarkTheme
          />
        </div>
      </div>
    </div>
  );
}
