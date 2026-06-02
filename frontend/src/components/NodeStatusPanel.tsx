export function NodeStatusPanel({ activeNode }: { activeNode: string | null }) {
  const nodes = [
    "Evaluation", 
    "Context Retrieval", 
    "Code Modification", 
    "Security Arbitration", 
    "Docker Sandbox"
  ];

  // Map backend node names to the UI labels
  const mapping: Record<string, string> = {
    "evaluation_node": "Evaluation",
    "context_node": "Context Retrieval",
    "modification_node": "Code Modification",
    "arbitration_node": "Security Arbitration",
    "sandbox_node": "Docker Sandbox",
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
        {nodes.map((node) => (
          <div 
            key={node} 
            className={`p-3 rounded-lg border transition-all duration-500 ${
              uiNode === node 
              ? "border-primary bg-primary/20 glow-active translate-x-2 shadow-md" 
              : "border-primary/20 bg-base/80 shadow-sm"
            }`}
          >
            <p className={`font-semibold ${uiNode === node ? "text-primary drop-shadow-[0_0_5px_var(--primary)]" : "text-text-main/80"}`}>
              {node}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
