export function NodeStatusPanel({ activeNode, deploymentStatus }: { activeNode: string | null, deploymentStatus?: string | null }) {
  const nodes = [
    "Evaluation", 
    "Context Retrieval", 
    "Code Modification", 
    "Security Arbitration", 
    "Docker Sandbox",
    "Deployment"
  ];

  // Map backend node names to the UI labels
  const mapping: Record<string, string> = {
    "evaluation_node": "Evaluation",
    "context_node": "Context Retrieval",
    "modification_node": "Code Modification",
    "arbitration_node": "Security Arbitration",
    "sandbox_node": "Docker Sandbox",
    "deployment_node": "Deployment",
    "END": "END"
  };

  const uiNode = mapping[activeNode || ""] || activeNode;

  return (
    <div className="bg-surface p-6 rounded-2xl shadow-xl border border-primary/10">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        Node Status
      </h2>
      <div className="space-y-4">
        {nodes.map((node) => {
          const isPendingDaemon = node === "Deployment" && deploymentStatus === "pending_daemon";
          const isActive = uiNode === node || isPendingDaemon;
          
          let borderBgColor = "border-primary bg-primary/20 glow-active translate-x-2 shadow-md";
          let textColor = "text-primary drop-shadow-[0_0_5px_var(--primary)]";
          
          if (isPendingDaemon) {
            borderBgColor = "border-yellow-500 bg-yellow-500/20 translate-x-2 shadow-md";
            textColor = "text-yellow-500 drop-shadow-[0_0_5px_var(--color-yellow-500)]";
          }
          
          return (
            <div 
              key={node} 
              className={`p-3 rounded-lg border transition-all duration-500 ${
                isActive ? borderBgColor : "border-primary/20 bg-base/80 shadow-sm"
              }`}
            >
              <p className={`font-semibold ${isActive ? textColor : "text-text-main/80"}`}>
                {node} {isPendingDaemon && "(Awaiting Daemon...)"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
