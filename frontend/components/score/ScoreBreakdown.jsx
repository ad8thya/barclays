"use client";

const BAR_DEFS = [
  { key: "email_contribution", label: "Email", weight: 0.40 },
  { key: "website_contribution", label: "Website", weight: 0.30 },
  { key: "attachment_contribution", label: "Attachment", weight: 0.20 },
  { key: "graph_contribution", label: "Graph", weight: 0.10 },
];

function barColor(val, weight) {
  if (val > weight * 0.8) return "#ef4444";
  if (val > weight * 0.5) return "#f59e0b";
  return "#3b82f6";
}

export default function ScoreBreakdown({ breakdown }) {
  const bd = breakdown || {};

  return (
    <div className="glass-card p-6 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 mb-5 pb-3 border-b border-white/[0.04]">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
        <span className="text-[11px] font-medium text-slate-500 uppercase tracking-[0.08em]">
          Score Breakdown
        </span>
      </div>

      {/* Bars */}
      <div className="flex-1 space-y-5">
        {BAR_DEFS.map(({ key, label, weight }) => {
          const val = bd[key] || 0;
          const pct = Math.min(100, (val / weight) * 100);
          const bc = barColor(val, weight);

          return (
            <div key={key}>
              <div className="flex justify-between items-baseline mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-400 uppercase tracking-[0.06em] font-medium">
                    {label}
                  </span>
                  <span className="text-[9px] text-slate-700 font-mono">
                    {(weight * 100).toFixed(0)}%
                  </span>
                </div>
                <span
                  className="text-[12px] font-medium font-mono"
                  style={{ color: val > 0 ? bc : "#334155" }}
                >
                  {val.toFixed(3)}
                </span>
              </div>
              <div className="h-1 bg-white/[0.04] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, background: bc }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
