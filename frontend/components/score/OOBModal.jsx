"use client";

import { useAnalysisContext } from "@/context/AnalysisContext";
import { oobRespond } from "@/lib/api";
import { useState } from "react";

export default function OOBModal() {
  const { oobTriggered, incidentId } = useAnalysisContext();
  const [responded, setResponded] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!oobTriggered) return null;

  async function handleRespond(action) {
    setLoading(true);
    try {
      await oobRespond(incidentId, action);
      setResponded(action);
    } catch {
      setResponded("error");
    }
    setLoading(false);
  }

  return (
    <div
      className="w-full py-4 px-6 sticky top-14 z-40 animate-fade-in"
      style={{
        background: "linear-gradient(90deg, rgba(239,68,68,0.15) 0%, rgba(239,68,68,0.08) 100%)",
        borderBottom: "1px solid rgba(239,68,68,0.2)",
      }}
    >
      <div className="max-w-[1280px] mx-auto flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          {/* Pulsing ring */}
          <div className="relative">
            <span className="absolute inset-0 rounded-full bg-red-500/30 animate-ping" style={{ animationDuration: "1.5s" }} />
            <span className="relative block w-3 h-3 rounded-full bg-red-500" />
          </div>
          <div>
            <p className="text-[13px] font-medium text-white">
              ⚠ OUT-OF-BAND VERIFICATION TRIGGERED
            </p>
            <p className="text-[11px] text-red-300/70">
              Contacting user via trusted secondary channel.
            </p>
          </div>
        </div>

        {responded ? (
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-[0.06em]">
            {responded === "error" ? "Failed to respond" : `Response: ${responded}`}
          </span>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleRespond("approve")}
              disabled={loading}
              className="px-4 py-1.5 text-[11px] font-medium uppercase tracking-[0.06em] rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
            >
              Approve
            </button>
            <button
              onClick={() => handleRespond("deny")}
              disabled={loading}
              className="px-4 py-1.5 text-[11px] font-medium uppercase tracking-[0.06em] rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors disabled:opacity-50"
            >
              Deny
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
