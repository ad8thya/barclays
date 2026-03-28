"use client";

import SkeletonBlock from "@/components/shared/SkeletonBlock";

export default function ExplanationBox({ explanation, verdictColor }) {
  const borderColor = verdictColor || "#334155";

  return (
    <div
      className="mt-5"
      style={{
        background: "rgba(255,255,255,0.02)",
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 0,
        padding: "16px 20px",
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <span className="text-[11px] font-medium text-slate-500 uppercase tracking-[0.08em]">
          LLM Explanation
        </span>
      </div>

      {explanation ? (
        <p className="text-[13px] text-slate-300 font-mono leading-[1.8] whitespace-pre-wrap">
          {explanation}
        </p>
      ) : (
        <div className="space-y-2">
          <SkeletonBlock width="100%" height="14px" />
          <SkeletonBlock width="90%" height="14px" />
          <SkeletonBlock width="75%" height="14px" />
        </div>
      )}
    </div>
  );
}
