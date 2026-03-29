"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import LayerCard from "@/components/LayerCard";
import SignalTag from "@/components/SignalTag";

const LAYERS = [
  { key: "email",      icon: "✉",  title: "Email",      weight: 35 },
  { key: "website",    icon: "🌐", title: "Website",    weight: 25 },
  { key: "attachment", icon: "📎", title: "Attachment", weight: 15 },
  { key: "audio",      icon: "🎙", title: "Audio",      weight: 15 },
];

export default function AnalysisPage() {
  const { emailResult, websiteResult, attachmentResult, audioResult, analyzing } = useAnalysis();

  const resultMap = {
    email:      emailResult,
    website:    websiteResult,
    attachment: attachmentResult,
    audio:      audioResult,
  };

  return (
    <>
      <div className="mb-8">
        <h2 className="text-lg font-semibold tracking-tight text-slate-100">Module Breakdown</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Raw output per analyzer — before score fusion
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {LAYERS.map((layer, idx) => {
          const data = resultMap[layer.key];

          const score =
            layer.key === "website"
              ? (data?.final_score != null ? data.final_score / 100 : data?.risk_score ?? null)
              : (data?.risk_score ?? null);

          const pct = score != null ? Math.round(score * 100) : null;
          const isHighRisk = pct != null && pct >= 40;
          const scoreColor = pct == null ? "#475569" : pct >= 40 ? "#ef4444" : "#10b981";
          const riskLabel = pct == null ? null : pct >= 40 ? "High Risk" : "Low Risk";
          const riskPillColor = pct == null ? null : pct >= 40
            ? { bg: "rgba(239,68,68,0.1)", text: "#f87171", dot: "#ef4444", border: "rgba(239,68,68,0.2)" }
            : { bg: "rgba(16,185,129,0.1)", text: "#34d399", dot: "#10b981", border: "rgba(16,185,129,0.2)" };

          const borderColor = pct == null
            ? "rgba(255,255,255,0.04)"
            : pct >= 40
            ? "rgba(239,68,68,0.2)"
            : "rgba(16,185,129,0.15)";

          return (
            <div
              key={layer.key}
              style={{
                opacity: 0,
                animation: `fadeSlideIn 0.3s ease forwards`,
                animationDelay: `${idx * 120}ms`,
                background: "rgba(13,17,28,0.75)",
                border: `1px solid ${borderColor}`,
                borderRadius: 12,
                padding: "20px",
                backdropFilter: "blur(12px)",
                transition: "border-color 0.3s ease",
              }}
            >
              {/* Header row */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: "rgba(255,255,255,0.04)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 16,
                  }}>
                    {layer.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", lineHeight: 1 }}>
                      {layer.title}
                    </div>
                    <div style={{ fontSize: 10, color: "#475569", fontFamily: "monospace", marginTop: 3 }}>
                      Weight: {layer.weight}%
                    </div>
                  </div>
                </div>

                {/* Risk pill — only shown when score is available */}
                {riskLabel && riskPillColor && (
                  <span style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "4px 10px",
                    borderRadius: 100,
                    background: riskPillColor.bg,
                    border: `1px solid ${riskPillColor.border}`,
                    fontSize: 10,
                    fontWeight: 700,
                    fontFamily: "monospace",
                    color: riskPillColor.text,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    whiteSpace: "nowrap",
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: riskPillColor.dot, flexShrink: 0 }} />
                    {riskLabel}
                  </span>
                )}

                {/* Analyzing spinner */}
                {analyzing && !riskLabel && (
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: 5,
                    padding: "4px 10px", borderRadius: 100,
                    background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)",
                    fontSize: 10, fontWeight: 700, fontFamily: "monospace",
                    color: "#fbbf24", textTransform: "uppercase", letterSpacing: "0.06em",
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#f59e0b", animation: "pulse 1s ease-in-out infinite" }} />
                    Analysing
                  </span>
                )}
              </div>

              {/* Score display */}
              {analyzing && pct == null ? (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ height: 36, width: 96, background: "rgba(255,255,255,0.04)", borderRadius: 6, marginBottom: 10 }} />
                  <div style={{ height: 6, background: "rgba(255,255,255,0.04)", borderRadius: 4 }} />
                </div>
              ) : pct == null ? (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 30, fontWeight: 700, color: "#334155", fontFamily: "monospace" }}>—</div>
                  <div style={{ height: 6, background: "rgba(255,255,255,0.03)", borderRadius: 4, marginTop: 10 }} />
                </div>
              ) : (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                    <span style={{ fontSize: 30, fontWeight: 700, color: scoreColor, fontFamily: "monospace" }}>
                      {pct}
                    </span>
                    <span style={{ fontSize: 13, color: "#475569", fontWeight: 500 }}>/ 100</span>
                  </div>
                  <div style={{ height: 6, background: "rgba(255,255,255,0.04)", borderRadius: 4, marginTop: 10, overflow: "hidden" }}>
                    <div style={{
                      height: "100%",
                      width: `${pct}%`,
                      background: scoreColor,
                      borderRadius: 4,
                      transition: "width 700ms ease-out",
                    }} />
                  </div>
                </div>
              )}

              {/* Detail content */}
              <div style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6 }}>
                {layer.key === "website" && data
                  ? <WebsiteBreakdown data={data} />
                  : <DefaultBreakdown layer={layer} data={data} />
                }
              </div>
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </>
  );
}

/* ── Website card ── */
function WebsiteBreakdown({ data }) {
  const finalScore = data.final_score ?? null;
  const finalRisk  = data.final_risk  ?? data.risk ?? "—";
  const confidence = data.confidence  ?? null;
  const typo       = data.typosquatting || {};
  const age        = data.domain_age    || {};
  const inject     = data.prompt_injection || {};

  const flags = [
    typo.is_suspicious        && `Typosquatting: ${typo.verdict} → ${typo.closest_legit_domain || "?"}`,
    age.is_new_domain         && `New domain: ${age.domain_age_days ?? "?"}d old`,
    data.overlays?.fake_login_overlay && "Fake login overlay",
    data.dns?.fast_flux_suspected     && "Fast-flux DNS",
    inject.has_issues                 && "Prompt injection payload",
    data.dynamic?.suspicious_requests?.length > 0
      && `${data.dynamic.suspicious_requests.length} suspicious request(s)`,
  ].filter(Boolean);

  const pct = finalScore != null ? finalScore : null;
  const scoreColor = pct == null ? "#475569" : pct >= 40 ? "#ef4444" : "#10b981";

  const llmRaw = data.ai_analysis || "";
  const reasonLine = llmRaw
    .split("\n")
    .find((l) => l.trim().toUpperCase().startsWith("REASON:"));
  const llmReason = reasonLine
    ? reasonLine.replace(/^reason:/i, "").trim()
    : llmRaw.split("\n").find((l) => l.trim() && !l.match(/^(RISK|CONFIDENCE):/i))?.trim() || "";

  return (
    <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {finalScore != null && (
          <span style={{
            fontSize: 11, fontFamily: "monospace", fontWeight: 700,
            padding: "2px 8px", borderRadius: 4,
            color: scoreColor,
            background: scoreColor + "18",
            border: `1px solid ${scoreColor}35`,
          }}>
            {finalScore}/100
          </span>
        )}
        {confidence != null && (
          <span style={{ fontSize: 10, color: "#475569", fontFamily: "monospace", marginLeft: "auto" }}>
            {confidence}% confidence
          </span>
        )}
      </div>

      {llmReason && (
        <p style={{
          fontSize: 11, color: "#64748b", fontFamily: "monospace",
          lineHeight: 1.6, borderLeft: "2px solid #1e2530", paddingLeft: 10, margin: 0,
        }}>
          {llmReason}
        </p>
      )}

      {flags.length > 0 && (
        <div style={{ paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", flexDirection: "column", gap: 4 }}>
          {flags.map((f, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 11 }}>
              <span style={{ color: "#ef4444", flexShrink: 0, marginTop: 1 }}>–</span>
              <span style={{ color: "#64748b" }}>{f}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Email / attachment / audio cards ── */
function DefaultBreakdown({ layer, data }) {
  if (!data) return null;

  const signals = data.signals
    ? Object.entries(data.signals).filter(
        ([, v]) => v === true || typeof v === "number" || (typeof v === "string" && v)
      )
    : [];

  return (
    <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 8 }}>
      {signals.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {signals.map(([key, val]) =>
            val === true
              ? <SignalTag key={key} label={formatKey(key)} danger />
              : <SignalTag key={key} label={`${formatKey(key)}: ${val}`} />
          )}
        </div>
      )}

      {layer.key === "email" && data.flagged_phrases?.length > 0 && (
        <div style={{ paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", marginBottom: 6, margin: "0 0 6px" }}>
            Flagged phrases
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {data.flagged_phrases.map((p, i) => (
              <span key={i} style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 4,
                background: "rgba(239,68,68,0.08)", color: "#f87171",
                border: "1px solid rgba(239,68,68,0.2)", fontFamily: "monospace",
              }}>
                &ldquo;{p}&rdquo;
              </span>
            ))}
          </div>
        </div>
      )}

      {layer.key === "attachment" && data.flags?.length > 0 && (
        <div style={{ paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#334155", margin: "0 0 6px" }}>
            Flags
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {data.flags.map((f, i) => (
              <span key={i} style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 4,
                background: "rgba(239,68,68,0.08)", color: "#f87171",
                border: "1px solid rgba(239,68,68,0.2)", fontFamily: "monospace",
              }}>
                {f}
              </span>
            ))}
          </div>
          {data.reason && (
            <p style={{ fontSize: 11, color: "#475569", marginTop: 8, fontStyle: "italic" }}>{data.reason}</p>
          )}
        </div>
      )}

      {layer.key === "audio" && (
        <p style={{ fontSize: 11, color: "#334155", fontStyle: "italic" }}>Not available in this build</p>
      )}
    </div>
  );
}

function formatKey(k) {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}