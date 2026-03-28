"use client";

import { useAnalysisContext } from "@/context/AnalysisContext";
import LayerCard from "@/components/analysis/LayerCard";
import EmptyState from "@/components/shared/EmptyState";
import { Mail, Globe, Paperclip, Mic, BarChart3 } from "lucide-react";

const LAYERS = [
  { key: "email", Icon: Mail, title: "Email Phishing", weight: 40 },
  { key: "website", Icon: Globe, title: "Website Spoofing", weight: 30 },
  { key: "attachment", Icon: Paperclip, title: "Attachment OCR", weight: 20 },
  { key: "audio", Icon: Mic, title: "Voice Analysis", weight: 10 },
];

export default function AnalysisPage() {
  const { layerResults, analysisStatus } = useAnalysisContext();

  function getScore(key) {
    const data = layerResults[key]?.data;
    if (!data) return null;
    if (key === "website") {
      if (data.final_score != null) return data.final_score / 100;
      if (data.risk_score != null) return data.risk_score;
      return null;
    }
    return data.risk_score ?? null;
  }

  function getFlags(key) {
    const data = layerResults[key]?.data;
    if (!data) return [];
    const flags = [];

    if (key === "email") {
      if (data.signals) {
        Object.entries(data.signals).forEach(([k, v]) => {
          if (v === true) flags.push(k.replace(/_/g, " "));
        });
      }
      if (data.flagged_phrases) {
        data.flagged_phrases.forEach((p) => flags.push(`"${p}"`));
      }
    }
    if (key === "website") {
      const d = data;
      if (d.typosquatting?.is_suspicious) flags.push("Typosquatting detected");
      if (d.domain_age?.is_new_domain) flags.push(`New domain: ${d.domain_age.domain_age_days}d`);
      if (d.overlays?.fake_login_overlay) flags.push("Fake login overlay");
      if (d.dns?.fast_flux_suspected) flags.push("Fast-flux DNS");
      if (d.prompt_injection?.has_issues) flags.push("Prompt injection");
    }
    if (key === "attachment" && data.flags) {
      data.flags.forEach((f) => flags.push(f));
    }
    return flags;
  }

  function getReason(key) {
    const data = layerResults[key]?.data;
    if (!data) return "";
    if (key === "website") {
      const raw = data.ai_analysis || "";
      const line = raw.split("\n").find((l) => l.trim().toUpperCase().startsWith("REASON:"));
      return line ? line.replace(/^reason:/i, "").trim() : "";
    }
    if (key === "attachment") return data.reason || "";
    return "";
  }

  if (analysisStatus === "idle") {
    return (
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
        <EmptyState
          icon={BarChart3}
          title="No analysis yet"
          message="Submit data on the Input page to see layer-by-layer results."
        />
      </div>
    );
  }

  return (
    <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-lg font-medium tracking-tight text-slate-100">
          Layer-by-Layer Analysis
        </h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Independent risk assessment per detection layer — before score fusion
        </p>
      </div>

      {/* 2x2 grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {LAYERS.map((layer, idx) => {
          const result = layerResults[layer.key];
          const status = result?.status || "pending";

          return (
            <div
              key={layer.key}
              style={{
                opacity: 0,
                animation: `slideUp 0.3s ease forwards`,
                animationDelay: `${idx * 150}ms`,
              }}
            >
              <LayerCard
                icon={layer.Icon}
                title={layer.title}
                weight={layer.weight}
                status={status}
                score={getScore(layer.key)}
                flags={getFlags(layer.key)}
                reason={getReason(layer.key)}
                error={result?.error}
              />
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
