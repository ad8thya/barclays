"use client";

import StatusPill from "@/components/shared/StatusPill";
import SkeletonBlock from "@/components/shared/SkeletonBlock";

export default function LayerCard({ icon: Icon, title, weight, status, score, flags, reason, error, children }) {
  const scorePercent = score != null ? Math.round(score * 100) : null;
  const verdictColor =
    scorePercent === null ? "#475569" :
    scorePercent >= 80 ? "#ef4444" :
    scorePercent >= 60 ? "#f59e0b" : "#10b981";

  return (
    <div
      className={`glass-card p-5 transition-all ${
        status === "error" ? "border-red-500/20" : ""
      }`}
      style={status === "error" ? { boxShadow: "inset 0 0 30px rgba(239,68,68,0.03)" } : {}}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            {Icon && <Icon size={16} className="text-accent" strokeWidth={1.5} />}
          </div>
          <div>
            <h3 className="text-[13px] font-medium text-slate-200">{title}</h3>
            <span className="text-[10px] text-slate-600">{weight}% weight</span>
          </div>
        </div>
        <StatusPill status={status} />
      </div>

      {/* Content */}
      {status === "analysing" ? (
        <div className="space-y-3">
          <SkeletonBlock width="60%" height="28px" />
          <SkeletonBlock width="100%" height="6px" />
          <SkeletonBlock width="80%" height="14px" />
        </div>
      ) : status === "error" ? (
        <p className="text-sm text-red-400">{error || "Analysis failed"}</p>
      ) : (
        <>
          {/* Score */}
          {scorePercent !== null && (
            <div className="mb-3">
              <span
                className="text-[28px] font-medium tabular-nums"
                style={{ color: verdictColor }}
              >
                {scorePercent}%
              </span>
            </div>
          )}

          {/* Progress bar */}
          {scorePercent !== null && (
            <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden mb-4">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${scorePercent}%`,
                  background: verdictColor,
                }}
              />
            </div>
          )}

          {/* Flags */}
          {flags && flags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {flags.map((flag, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-white/[0.04] text-slate-400 border border-white/[0.06] font-mono">
                  {flag}
                </span>
              ))}
            </div>
          )}

          {/* Reason */}
          {reason && (
            <p className="text-[11px] text-slate-500 leading-relaxed">{reason}</p>
          )}

          {/* Custom slot content */}
          {children}
        </>
      )}
    </div>
  );
}
