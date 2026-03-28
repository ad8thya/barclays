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
          return (
            <div
              key={layer.key}
              style={{
                opacity: 0,
                animation: `fadeSlideIn 0.3s ease forwards`,
                animationDelay: `${idx * 120}ms`,
              }}
            >
              <LayerCard
                icon={layer.icon}
                title={layer.title}
                weight={layer.weight}
                status={analyzing ? "running" : data ? "complete" : "pending"}
                score={
                  layer.key === "website"
                    ? (data?.final_score != null ? data.final_score / 100 : data?.risk_score)
                    : data?.risk_score
                }
              >
                {layer.key === "website" && data
                  ? <WebsiteBreakdown data={data} />
                  : <DefaultBreakdown layer={layer} data={data} />
                }
              </LayerCard>
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
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

  // Pull only the spiciest flags
  const flags = [
    typo.is_suspicious        && `Typosquatting: ${typo.verdict} → ${typo.closest_legit_domain || "?"}`,
    age.is_new_domain         && `New domain: ${age.domain_age_days ?? "?"}d old`,
    data.overlays?.fake_login_overlay && "Fake login overlay",
    data.dns?.fast_flux_suspected     && "Fast-flux DNS",
    inject.has_issues                 && "Prompt injection payload",
    data.dynamic?.suspicious_requests?.length > 0
      && `${data.dynamic.suspicious_requests.length} suspicious request(s)`,
  ].filter(Boolean);

  const riskColor =
    finalRisk === "HIGH"   ? "#ef4444" :
    finalRisk === "MEDIUM" ? "#f59e0b" : "#10b981";

  // Clean up the LLM text — strip "RISK:" / "CONFIDENCE:" lines, keep REASON
  const llmRaw = data.ai_analysis || "";
  const reasonLine = llmRaw
    .split("\n")
    .find((l) => l.trim().toUpperCase().startsWith("REASON:"));
  const llmReason = reasonLine
    ? reasonLine.replace(/^reason:/i, "").trim()
    : llmRaw.split("\n").find((l) => l.trim() && !l.match(/^(RISK|CONFIDENCE):/i))?.trim() || "";

  return (
    <div className="mt-2 space-y-3">

      {/* Score + risk + confidence in one line */}
      <div className="flex items-center gap-2 flex-wrap">
        {finalScore != null && (
          <span
            className="text-[12px] font-mono font-bold px-2 py-0.5 rounded"
            style={{ color: riskColor, background: riskColor + "18", border: `1px solid ${riskColor}35` }}
          >
            {finalScore}/100
          </span>
        )}
        <span
          className="text-[10px] uppercase tracking-widest font-semibold"
          style={{ color: riskColor }}
        >
          {finalRisk}
        </span>
        {confidence != null && (
          <span className="text-[10px] text-slate-600 font-mono ml-auto">
            {confidence}% confidence
          </span>
        )}
      </div>

      {/* LLM reasoning */}
      {llmReason && (
        <p className="text-[11px] text-slate-400 font-mono leading-relaxed border-l-2 border-slate-700 pl-2.5">
          {llmReason}
        </p>
      )}

      {/* Top flags only */}
      {flags.length > 0 && (
        <div className="pt-2 border-t border-white/[0.05] flex flex-col gap-1">
          {flags.map((f, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px]">
              <span className="text-red-500 select-none flex-shrink-0 mt-0.5">–</span>
              <span className="text-slate-400">{f}</span>
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
    <div className="mt-1 space-y-2">
      {signals.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {signals.map(([key, val]) =>
            val === true
              ? <SignalTag key={key} label={formatKey(key)} danger />
              : <SignalTag key={key} label={`${formatKey(key)}: ${val}`} />
          )}
        </div>
      )}

      {layer.key === "email" && data.flagged_phrases?.length > 0 && (
        <div className="pt-2 border-t border-white/[0.05]">
          <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-1.5">
            Flagged phrases
          </p>
          <div className="flex flex-wrap gap-1.5">
            {data.flagged_phrases.map((p, i) => (
              <span
                key={i}
                className="text-[11px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-mono"
              >
                &ldquo;{p}&rdquo;
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatKey(k) {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}