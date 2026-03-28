"use client";

export default function LayerCard({ icon, title, status, score, weight, index = 0, children }) {
  const isComplete = status === "complete";
  const isRunning = status === "running";
  const isHighRisk = score != null && score >= 0.7;
  const isCritical = score != null && score >= 0.8;

  const scoreColor = isCritical
    ? "text-red-400"
    : isHighRisk
    ? "text-amber-400"
    : score != null
    ? "text-emerald-400"
    : "text-slate-600";

  const barColor = isCritical
    ? "bg-red-500"
    : isHighRisk
    ? "bg-amber-400"
    : "bg-emerald-500";

  const borderColor = isCritical
    ? "border-red-500/30"
    : isHighRisk
    ? "border-amber-500/20"
    : isComplete
    ? "border-accent/20"
    : "border-white/[0.04]";

  const pct = score != null ? Math.round(score * 100) : 0;
  const delay = `stagger-${index + 1}`;

  return (
    <div
      className={`glass-card ${borderColor} p-5 transition-all duration-300 opacity-0 animate-slide-up ${delay} ${
        isComplete ? "hover:border-white/10" : ""
      }`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-white/[0.04] flex items-center justify-center text-base">
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white leading-none">{title}</h3>
            {weight && (
              <span className="text-[10px] text-slate-600 font-mono mt-0.5 block">
                Weight: {weight}
              </span>
            )}
          </div>
        </div>

        {/* Status pill */}
        <StatusPill status={status} score={score} />
      </div>

      {/* Score display */}
      {status === "pending" && !isRunning ? (
        <div className="mb-4">
          <div className="text-3xl font-bold tabular-nums text-slate-700">—</div>
          <div className="h-1.5 bg-white/[0.03] rounded-full mt-3" />
        </div>
      ) : isRunning ? (
        <div className="mb-4">
          <div className="skeleton h-9 w-24 mb-3" />
          <div className="skeleton h-1.5 w-full" />
        </div>
      ) : (
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold tabular-nums ${scoreColor}`}>
              {pct}
            </span>
            <span className="text-sm text-slate-600 font-medium">/ 100</span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 bg-white/[0.04] rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Detail slot */}
      <div className="text-[13px] text-slate-400 leading-relaxed">{children}</div>
    </div>
  );
}

function StatusPill({ status, score }) {
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
        Analysing
      </span>
    );
  }

  if (status === "complete") {
    const color =
      score >= 0.8
        ? "bg-red-500/10 text-red-400"
        : score >= 0.7
        ? "bg-amber-500/10 text-amber-400"
        : "bg-emerald-500/10 text-emerald-400";

    const label = score >= 0.8 ? "High Risk" : score >= 0.7 ? "Suspicious" : "Complete";

    return (
      <span className={`inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full ${color}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-current" />
        {label}
      </span>
    );
  }

  return (
    <span className="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-white/[0.03] text-slate-600">
      Pending
    </span>
  );
}
