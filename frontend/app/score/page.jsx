"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import ScoreGauge from "@/components/ScoreGauge";
import OOBModal from "@/components/OOBModal";

const BAR_DEFS = [
  { key: "email_contribution",      label: "Email",      weight: 0.35 },
  { key: "website_contribution",    label: "Website",    weight: 0.25 },
  { key: "attachment_contribution", label: "Attachment", weight: 0.15 },
  { key: "audio_contribution",      label: "Audio",      weight: 0.15 },
  { key: "graph_contribution",      label: "Graph",      weight: 0.10 },
];

function threatColor(frs) {
  if (frs >= 0.8) return "#ef4444";
  if (frs >= 0.7) return "#f59e0b";
  return "#10b981";
}
function threatBorder(frs) {
  if (frs >= 0.8) return "#451a1a";
  if (frs >= 0.7) return "#3d2d0d";
  return "#14372a";
}
function barColor(val, weight) {
  if (val > weight * 0.8) return "#ef4444";
  if (val > weight * 0.5) return "#f59e0b";
  return "#3b82f6";
}

export default function ScorePage() {
  const { scoreResult, explanation, oobTriggered } = useAnalysis();
  const frs       = scoreResult?.final_risk_score  || 0;
  const breakdown = scoreResult?.score_breakdown   || {};
  const verdict   = scoreResult?.verdict           || "—";
  const tc        = threatColor(frs);
  const tb        = threatBorder(frs);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* OOB modal */}
      <OOBModal />

      {/* ── Page header ── */}
      <PageHeader frs={frs} verdict={verdict} tc={tc} />

      {/* ── Top row: gauge + breakdown ── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: 12,
      }}>
        <ScoreGauge score={frs} />
        <BreakdownPanel breakdown={breakdown} verdict={verdict} frs={frs} tc={tc} />
      </div>

      {/* ── Meta row: score stats ── */}
      <MetaStrip frs={frs} scoreResult={scoreResult} tc={tc} />

      {/* ── Explanation ── */}
      <ExplanationPanel explanation={explanation} frs={frs} tc={tc} tb={tb} />

    </div>
  );
}

/* ─────────────────────────────────────────
   Page header — incident + verdict strip
───────────────────────────────────────── */
function PageHeader({ frs, verdict, tc }) {
  const { incidentId, accountId } = useAnalysis();
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexWrap: "wrap",
      gap: 12,
      paddingBottom: 14,
      borderBottom: "1px solid #1e2530",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 3, height: 18, background: "#3b82f6", borderRadius: 1, flexShrink: 0 }} />
        <div>
          <div style={{
            fontFamily: "monospace",
            fontSize: 13,
            fontWeight: 600,
            color: "#e2e8f0",
            letterSpacing: "0.02em",
          }}>
            Fused Risk Score
          </div>
          <div style={{
            fontFamily: "monospace",
            fontSize: 10,
            color: "#475569",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginTop: 2,
          }}>
            Weighted verdict · all layers + graph
          </div>
        </div>
      </div>

      {/* Right: incident + verdict pill */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: "#475569",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}>
          {incidentId}
        </div>
        <div style={{ width: 1, height: 12, background: "#1e2530" }} />
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          border: `1px solid ${frs > 0 ? tc + "55" : "#1e2530"}`,
          borderRadius: 3,
          background: frs > 0 ? tc + "11" : "#0f1117",
        }}>
          {frs > 0 && (
            <span style={{
              width: 5, height: 5,
              borderRadius: "50%",
              background: tc,
              flexShrink: 0,
            }} />
          )}
          <span style={{
            fontFamily: "monospace",
            fontSize: 10,
            fontWeight: 700,
            color: frs > 0 ? tc : "#334155",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
          }}>
            {verdict}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   Score breakdown panel
───────────────────────────────────────── */
function BreakdownPanel({ breakdown, verdict, frs, tc }) {
  return (
    <div style={{
      background: "#13161e",
      border: "1px solid #1e2530",
      borderRadius: 6,
      padding: "18px 20px",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        marginBottom: 18,
        paddingBottom: 12,
        borderBottom: "1px solid #1e2530",
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6"  y1="20" x2="6"  y2="14"/>
        </svg>
        <span style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: "#475569",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}>
          Score Breakdown
        </span>
      </div>

      {/* Bars */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
        {BAR_DEFS.map(({ key, label, weight }) => {
          const val  = breakdown[key] || 0;
          const pct  = Math.min(100, (val / weight) * 100);
          const bc   = barColor(val, weight);
          return (
            <div key={key}>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 5,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{
                    fontFamily: "monospace",
                    fontSize: 10,
                    color: "#94a3b8",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}>
                    {label}
                  </span>
                  <span style={{
                    fontFamily: "monospace",
                    fontSize: 9,
                    color: "#334155",
                  }}>
                    {(weight * 100).toFixed(0)}%
                  </span>
                </div>
                <span style={{
                  fontFamily: "monospace",
                  fontSize: 11,
                  fontWeight: 600,
                  color: val > 0 ? bc : "#334155",
                }}>
                  {val.toFixed(3)}
                </span>
              </div>
              {/* Track */}
              <div style={{
                height: 3,
                background: "#1e2530",
                borderRadius: 2,
                overflow: "hidden",
              }}>
                <div style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: bc,
                  borderRadius: 2,
                  transition: "width 700ms ease-out",
                }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Verdict row */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginTop: 18,
        paddingTop: 12,
        borderTop: "1px solid #1e2530",
      }}>
        <span style={{
          fontFamily: "monospace",
          fontSize: 9,
          color: "#334155",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}>
          Final Verdict
        </span>
        <span style={{
          fontFamily: "monospace",
          fontSize: 12,
          fontWeight: 700,
          color: tc,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}>
          {verdict}
        </span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   Meta stat strip — 4 quick-read tiles
───────────────────────────────────────── */
function MetaStrip({ frs, scoreResult, tc }) {
  const oob    = scoreResult?.oob_triggered   ? "Yes" : "No";
  const graph  = scoreResult?.graph?.campaign_detected ? "Detected" : "None";
  const linked = scoreResult?.graph?.linked_incidents?.length ?? 0;

  const tiles = [
    { label: "FRS",              value: frs > 0 ? `${Math.round(frs * 100)}%` : "—", color: frs > 0 ? tc : "#475569" },
    { label: "OOB Triggered",    value: oob,    color: oob === "Yes" ? "#ef4444" : "#475569" },
    { label: "Campaign",         value: graph,  color: graph === "Detected" ? "#ef4444" : "#475569" },
    { label: "Linked Incidents", value: linked, color: linked > 0 ? "#f59e0b" : "#475569" },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 8,
    }}>
      {tiles.map(({ label, value, color }) => (
        <div key={label} style={{
          background: "#13161e",
          border: "1px solid #1e2530",
          borderRadius: 6,
          padding: "12px 14px",
        }}>
          <div style={{
            fontFamily: "monospace",
            fontSize: 9,
            color: "#334155",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            marginBottom: 6,
          }}>
            {label}
          </div>
          <div style={{
            fontFamily: "monospace",
            fontSize: 18,
            fontWeight: 700,
            color,
            letterSpacing: "0.02em",
          }}>
            {String(value)}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────
   Explanation panel
───────────────────────────────────────── */
function ExplanationPanel({ explanation, frs, tc, tb }) {
  return (
    <div style={{
      background: "#13161e",
      border: `1px solid ${frs > 0 ? tb : "#1e2530"}`,
      borderRadius: 6,
      padding: "18px 20px",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        marginBottom: 14,
        paddingBottom: 12,
        borderBottom: "1px solid #1e2530",
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        <span style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: "#475569",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}>
          Analysis Explanation
        </span>
      </div>

      {explanation ? (
        <div style={{
          paddingLeft: 12,
          borderLeft: `2px solid ${tc}33`,
        }}>
          {/* Parse explanation into paragraphs for readability */}
          {explanation.split("\n").filter(Boolean).map((line, i) => (
            <p key={i} style={{
              fontFamily: "monospace",
              fontSize: 12,
              color: "#64748b",
              lineHeight: 1.75,
              marginBottom: 6,
              margin: "0 0 6px",
            }}>
              {line}
            </p>
          ))}
        </div>
      ) : (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "12px 0",
        }}>
          <div style={{
            width: 4, height: 4,
            borderRadius: "50%",
            background: "#334155",
            flexShrink: 0,
          }} />
          <span style={{
            fontFamily: "monospace",
            fontSize: 11,
            color: "#334155",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}>
            Run analysis to generate explanation
          </span>
        </div>
      )}
    </div>
  );
}