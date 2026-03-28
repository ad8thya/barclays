"use client";

export default function CampaignSummary({ graphData, scoreResult }) {
  const graphInfo = scoreResult?.graph || {};
  const campaignDetected = graphInfo.campaign_detected;
  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Derive stats
  const nodeTypes = {};
  nodes.forEach((n) => { nodeTypes[n.type] = (nodeTypes[n.type] || 0) + 1; });

  const edgeTypes = {};
  edges.forEach((e) => { edgeTypes[e.relation] = (edgeTypes[e.relation] || 0) + 1; });

  const domains = nodes.filter((n) => n.type === "domain").map((n) => n.label || n.id);
  const incidents = nodes.filter((n) => n.type === "incident").map((n) => n.id);
  const highestRisk = nodes.length > 0
    ? Math.max(...nodes.map((n) => n.risk_score || 0))
    : 0;

  return (
    <div className="glass-card p-5 flex flex-col h-full">
      <h3 className="text-[13px] font-medium text-slate-300 mb-5 flex items-center gap-2 uppercase tracking-[0.06em]">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        Campaign Summary
      </h3>

      {nodes.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-slate-600">No graph data available</p>
        </div>
      ) : (
        <div className="flex-1 space-y-0">
          <StatRow label="Total Nodes" value={nodes.length} />
          <StatRow label="Incidents" value={nodeTypes.incident || 0} />
          <StatRow label="Domains" value={nodeTypes.domain || 0} />
          <StatRow label="IPs" value={nodeTypes.ip || 0} />
          <StatRow label="Total Edges" value={edges.length} />
          <StatRow
            label="Highest Risk"
            value={`${Math.round(highestRisk * 100)}%`}
            highlight={highestRisk >= 0.7}
          />

          {campaignDetected && (
            <>
              <div className="pt-3 mt-3 border-t border-white/[0.04]">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-[11px] font-medium text-red-400 uppercase tracking-[0.06em]">
                    Campaign Detected
                  </span>
                </div>
                <StatRow label="Campaign ID" value={graphInfo.campaign_id || "—"} mono />
                <StatRow label="Victim Count" value={graphInfo.victim_count || 0} />
              </div>
            </>
          )}

          {/* Shared domains list */}
          {domains.length > 0 && (
            <div className="pt-3 mt-3 border-t border-white/[0.04]">
              <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600 mb-2 font-medium">
                Shared Domains
              </p>
              <div className="space-y-1">
                {domains.map((d) => (
                  <div key={d} className="text-[11px] text-slate-400 font-mono px-2 py-1 rounded bg-white/[0.02]">
                    {d}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Incident IDs */}
          {incidents.length > 0 && (
            <div className="pt-3 mt-3 border-t border-white/[0.04]">
              <p className="text-[10px] uppercase tracking-[0.08em] text-slate-600 mb-2 font-medium">
                Incident IDs
              </p>
              <div className="flex flex-wrap gap-1">
                {incidents.map((id) => (
                  <span key={id} className="text-[10px] text-slate-500 font-mono px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.04]">
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatRow({ label, value, highlight, mono }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-white/[0.04] text-sm">
      <span className="text-slate-500 text-[12px]">{label}</span>
      <span className={`text-[13px] font-medium ${
        highlight ? "text-red-400" : "text-slate-300"
      } ${mono ? "font-mono text-[11px]" : ""}`}>
        {String(value)}
      </span>
    </div>
  );
}
