import { useEffect, useRef } from "react";

export function TerminalLog({ logs }: { logs: string[] }) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="lg:col-span-2 bg-base rounded-2xl shadow-2xl border border-surface overflow-hidden flex flex-col h-[600px]">
      <div className="bg-surface px-4 py-3 flex items-center gap-2 border-b border-base/50">
        <div className="w-3 h-3 rounded-full bg-error"></div>
        <div className="w-3 h-3 rounded-full bg-primary/50"></div>
        <div className="w-3 h-3 rounded-full bg-success"></div>
        <span className="ml-2 text-sm text-text-muted font-mono">nexus-core@agent:~/logs</span>
      </div>
      
      <div className="p-6 flex-1 overflow-y-auto font-mono text-sm space-y-2">
        {logs.length === 0 ? (
          <p className="text-text-muted italic">Waiting for incoming telemetry anomalies...</p>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="animate-in fade-in slide-in-from-bottom-2">
              <span className={log.includes("[PATCH]") ? "text-success whitespace-pre-wrap block mt-4 p-4 bg-surface rounded-lg" : "text-text-main"}>
                <span className="text-primary mr-2">➜</span>
                {log}
              </span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
