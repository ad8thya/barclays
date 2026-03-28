"use client";

import { useAnalysisContext } from "@/context/AnalysisContext";
import ScoreGauge from "@/components/score/ScoreGauge";
import ScoreBreakdown from "@/components/score/ScoreBreakdown";
import ExplanationBox from "@/components/score/ExplanationBox";
import OOBModal from "@/components/score/OOBModal";
import EmptyState from "@/components/shared/EmptyState";
import { BarChart3 } from "lucide-react";

export default function ScorePage() {
  const { scoreResult, explanation, oobTriggered, frs, verdict } = useAnalysisContext();

  const finalScore = frs || scoreResult?.final_risk_score || 0;
  const breakdown = scoreResult?.score_breakdown || {};
  const displayVerdict = verdict || scoreResult?.verdict || "—";

  const verdictColor =
    finalScore >= 0.80 ? "#ef4444" :
    finalScore >= 0.70 ? "#f59e0b" : "#10b981";

  if (!scoreResult) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
        <EmptyState
          icon={BarChart3}
          title="No score data"
          message="Run an analysis from the Input page to see the fused risk score."
        />
      </div>
    );
  }

  return (
    <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
      {/* OOB Banner */}
      {oobTriggered && <OOBModal />}

      {/* Header */}
      <div className="mb-8 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-lg font-medium tracking-tight text-slate-100">
            Fused Risk Score
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Weighted verdict across all layers + graph intelligence
          </p>
        </div>
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded border"
          style={{
            borderColor: verdictColor + "55",
            background: verdictColor + "11",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: verdictColor }}
          />
          <span
            className="text-[11px] font-medium uppercase tracking-[0.08em] font-mono"
            style={{ color: verdictColor }}
          >
            {displayVerdict}
          </span>
        </div>
      </div>

      {/* Two-column: gauge + breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        <ScoreGauge score={finalScore} />
        <ScoreBreakdown breakdown={breakdown} />
      </div>

      {/* Meta stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <MetaTile
          label="FRS"
          value={finalScore > 0 ? `${Math.round(finalScore * 100)}%` : "—"}
          color={finalScore > 0 ? verdictColor : "#475569"}
        />
        <MetaTile
          label="OOB Triggered"
          value={oobTriggered ? "Yes" : "No"}
          color={oobTriggered ? "#ef4444" : "#475569"}
        />
        <MetaTile
          label="Campaign"
          value={scoreResult?.graph?.campaign_detected ? "Detected" : "None"}
          color={scoreResult?.graph?.campaign_detected ? "#ef4444" : "#475569"}
        />
        <MetaTile
          label="Linked Incidents"
          value={scoreResult?.graph?.linked_incidents?.length ?? 0}
          color={(scoreResult?.graph?.linked_incidents?.length || 0) > 0 ? "#f59e0b" : "#475569"}
        />
      </div>

      {/* Explanation */}
      <ExplanationBox explanation={explanation} verdictColor={verdictColor} />
    </div>
  );
}

function MetaTile({ label, value, color }) {
  return (
    <div className="glass-card p-4">
      <div className="text-[10px] text-slate-600 uppercase tracking-[0.08em] mb-2 font-medium">
        {label}
      </div>
      <div
        className="text-[20px] font-medium font-mono"
        style={{ color }}
      >
        {String(value)}
      </div>
    </div>
  );
}
