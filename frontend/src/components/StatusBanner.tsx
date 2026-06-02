type StatusType = "idle" | "running" | "success" | "blocked" | "failed";

export function StatusBanner({ status }: { status: StatusType }) {
  if (status === "idle" || status === "running") return null;

  const isSuccess = status === "success";

  return (
    <div className={`p-6 rounded-2xl shadow-xl border transition-all animate-in fade-in zoom-in duration-500 ${
      isSuccess 
      ? "bg-success/10 border-success text-success" 
      : "bg-error/10 border-error text-error"
    }`}>
      <h3 className="text-xl font-bold text-center">
        {isSuccess ? "✔ Fix Deployed & Verified" : "✖ Security Blocked / Failed"}
      </h3>
    </div>
  );
}
