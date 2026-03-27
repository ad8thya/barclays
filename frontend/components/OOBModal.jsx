"use client";

import { useAnalysis } from "@/context/AnalysisContext";

export default function OOBModal() {
  const { oobTriggered, setOobTriggered, incidentId, scoreResult } = useAnalysis();

  if (!oobTriggered) return null;

  const frs = scoreResult?.final_risk_score || 0;
  const verdict = scoreResult?.threshold_breached || "OOB";

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in">
      <div className="glass-card border-2 border-red-500/40 p-0 max-w-lg w-[92%] overflow-hidden">
        {/* Pulsing red header bar */}
        <div className="bg-red-500/10 border-b border-red-500/20 px-8 py-4 oob-banner">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold text-red-400">
                Out-of-Band Verification Triggered
              </h2>
              <p className="text-[11px] text-red-400/60 mt-0.5">Threat level exceeded intervention threshold</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-8 py-6">
          <p className="text-sm text-slate-400 mb-5 leading-relaxed">
            FRS has exceeded the <strong className="text-white font-semibold">0.80 threshold</strong> during
            an active transaction. A push notification has been sent to the customer&apos;s
            registered device via a <strong className="text-white font-semibold">trusted secondary channel</strong>.
          </p>

          {/* Detail rows */}
          <div className="bg-white/[0.02] rounded-lg border border-white/[0.04] p-4 mb-6 space-y-2.5">
            <DetailRow label="Incident" value={incidentId} />
            <DetailRow label="Final Risk Score" value={`${(frs * 100).toFixed(0)}%`} valueColor="text-red-400" />
            <DetailRow label="Threshold" value={verdict} />
            <DetailRow label="Action Taken" value="FREEZE & OOB Verification" valueColor="text-red-400" />
            <DetailRow label="Channel" value="Barclays Mobile App (Biometric)" />
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setOobTriggered(false)}
              className="flex-1 bg-red-500/15 hover:bg-red-500/25 border border-red-500/20 text-red-400 px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors"
            >
              Transaction Frozen
            </button>
            <button
              onClick={() => setOobTriggered(false)}
              className="flex-1 border border-white/[0.06] text-slate-500 hover:text-slate-300 hover:bg-white/[0.03] px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, valueColor = "text-slate-200" }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-[12px] text-slate-600">{label}</span>
      <span className={`text-[12px] font-semibold font-mono ${valueColor}`}>{value}</span>
    </div>
  );
}
