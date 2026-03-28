"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import FraudGraph from "@/components/FraudGraph";
import SignalTag from "@/components/SignalTag";

export default function GraphPage() {
  const { graphData, scoreResult } = useAnalysis();
  const graphInfo = scoreResult?.graph || {};
  const campaignDetected = graphInfo.campaign_detected;

  return (
    <>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-semibold tracking-tight">Graph Intelligence</h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Campaign correlation across incidents — shared infrastructure and signals
        </p>
      </div>

      {/* Campaign alert banner */}
      {campaignDetected && (
        <div className="glass-card mb-5 p-4 border-red-500/30 animate-fade-in"
          style={{ boxShadow: "0 0 20px rgba(239,68,68,0.08), inset 0 0 20px rgba(239,68,68,0.03)" }}>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm font-semibold text-red-400">Coordinated Campaign Detected</span>
            <span className="text-[11px] text-red-400/60 ml-auto font-mono">
              {graphInfo.victim_count || 0} victims — {(graphInfo.linked_incidents || []).length} linked incidents
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5 min-h-[480px]">
        {/* Graph visualization */}
        <FraudGraph graphData={graphData} />

        {/* Sidebar */}
        <div className="glass-card p-5 flex flex-col">
          <h3 className="text-[13px] font-semibold text-slate-300 mb-5 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Campaign Summary
          </h3>

          {graphData ? (
            <div className="flex-1 space-y-0">
              <StatRow label="Campaign Detected" value={campaignDetected ? "Yes" : "No"} highlight={campaignDetected} />
              <StatRow label="Campaign ID" value={graphInfo.campaign_id || "—"} mono />
              <StatRow label="Linked Incidents" value={(graphInfo.linked_incidents || []).length} />
              <StatRow label="Victim Count" value={graphInfo.victim_count || 1} />
              <StatRow label="Total Nodes" value={(graphData.nodes || []).length} />
              <StatRow label="Total Edges" value={(graphData.edges || []).length} />

              {(graphInfo.shared_signals || []).length > 0 && (
                <div className="pt-4 mt-3 border-t border-white/[0.04]">
                  <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-2.5 font-medium">
                    Shared Signals
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {graphInfo.shared_signals.map((s, i) => (
                      <SignalTag key={i} label={s} danger />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-sm text-slate-600">Run analysis to populate graph</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function StatRow({ label, value, highlight, mono }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-white/[0.04] text-sm">
      <span className="text-slate-500 text-[12px]">{label}</span>
      <span className={`text-[13px] font-semibold ${
        highlight ? "text-red-400" : "text-slate-300"
      } ${mono ? "font-mono text-[11px]" : ""}`}>
        {String(value)}
      </span>
    </div>
  );
}
