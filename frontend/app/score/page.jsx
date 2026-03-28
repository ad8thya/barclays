"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import ScoreGauge from "@/components/ScoreGauge";
import OOBModal from "@/components/OOBModal";

export default function ScorePage() {
  const { scoreResult, explanation, oobTriggered } = useAnalysis();
  const frs = scoreResult?.final_risk_score || 0;
  const breakdown = scoreResult?.score_breakdown || {};
  const verdict = scoreResult?.verdict || "—";

  const barDefs = [
    { key: "email_contribution",      label: "Email",      weight: 0.35 },
    { key: "website_contribution",    label: "Website",    weight: 0.25 },
    { key: "attachment_contribution", label: "Attachment", weight: 0.15 },
    { key: "audio_contribution",      label: "Audio",      weight: 0.15 },
    { key: "graph_contribution",      label: "Graph",      weight: 0.10 },
  ];

  const verdictColor = frs >= 0.8 ? "text-red-400" : frs >= 0.7 ? "text-amber-400" : "text-emerald-400";
  const verdictBorder = frs >= 0.8 ? "border-red-500/30" : frs >= 0.7 ? "border-amber-500/30" : "border-emerald-500/30";

  return (
    <>
      {/* OOB Banner */}
      {oobTriggered && (
        <div className="mb-6 animate-fade-in">
          <OOBModal />
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-semibold tracking-tight">Fused Risk Score</h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Weighted verdict synthesizing all layers and graph correlation
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Gauge */}
        <div className="animate-fade-in">
          <ScoreGauge score={frs} />
        </div>

        {/* Breakdown */}
        <div className="glass-card p-6 animate-slide-up">
          <h3 className="text-[13px] font-semibold text-slate-300 mb-5 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
              <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
            Score Breakdown
          </h3>

          {barDefs.map(({ key, label, weight }) => {
            const val = breakdown[key] || 0;
            const pct = Math.min(100, (val / weight) * 100);
            const cls =
              val > weight * 0.8
                ? "bg-red-500"
                : val > weight * 0.5
                ? "bg-amber-400"
                : "bg-accent";

            return (
              <div key={key} className="mb-4">
                <div className="flex justify-between text-[12px] mb-1.5">
                  <span className="text-slate-500">
                    {label} <span className="text-slate-700">({(weight * 100).toFixed(0)}%)</span>
                  </span>
                  <span className="font-semibold tabular-nums font-mono text-[11px] text-slate-300">{val.toFixed(3)}</span>
                </div>
                <div className="h-1.5 bg-white/[0.03] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${cls}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}

          {/* Verdict badge */}
          <div className={`mt-5 pt-4 border-t border-white/[0.04] flex items-center justify-between`}>
            <span className="text-[10px] uppercase tracking-widest text-slate-600 font-medium">Verdict</span>
            <span className={`text-sm font-bold ${verdictColor}`}>{verdict}</span>
          </div>
        </div>
      </div>

      {/* Explanation */}
      <div className={`glass-card p-6 ${verdictBorder} animate-slide-up`} style={{ animationDelay: "150ms" }}>
        <h3 className="text-[13px] font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          Human-Readable Explanation
        </h3>
        {explanation ? (
          <div className={`text-sm leading-relaxed text-slate-400 font-mono text-[12px] pl-4 border-l-2 ${verdictBorder} whitespace-pre-wrap`}>
            {explanation}
          </div>
        ) : (
          <p className="text-sm text-slate-600">Run analysis to generate explanation.</p>
        )}
      </div>
    </>
  );
}
