"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Mail, Globe, Paperclip, Network } from "lucide-react";
import LandingHero from "@/components/landing/LandingHero";
import { BentoGrid, BentoCard } from "@/components/ui/bento-grid";
import { LiquidButton } from "@/components/ui/liquid-glass-button";

const ShaderAnimation = dynamic(
  () => import("@/components/ui/shader-animation"),
  { ssr: false }
);

const BENTO_ITEMS = [
  {
    name: "Email Phishing Detection",
    Icon: Mail,
    description:
      "XGBoost-powered classifier analysing sender metadata, TF-IDF body features, and credential-harvesting signals. Flags urgency language, spoofed domains, and suspicious link patterns with 97% precision.",
    tags: ["XGBoost", "TF-IDF", "40% weight"],
    colSpan: 2,
  },
  {
    name: "Website Spoofing",
    Icon: Globe,
    description:
      "Headless Playwright renders suspicious URLs, detecting typosquatting, fake login overlays, fast-flux DNS, and prompt injection payloads via AI-powered visual and structural analysis.",
    tags: ["Playwright", "LLM", "30% weight"],
    colSpan: 1,
  },
  {
    name: "Attachment Analysis",
    Icon: Paperclip,
    description:
      "OCR extraction via PyTesseract on PDF and image attachments. Identifies credential-harvesting forms, obfuscated macros, and social engineering patterns in document content.",
    tags: ["OCR", "PyTesseract", "20% weight"],
    colSpan: 1,
  },
  {
    name: "Fraud Graph Intelligence",
    Icon: Network,
    description:
      "Correlates attacks across users via shared domains, IPs, and behavioural signals. Detects coordinated campaigns with deterministic campaign ID assignment and multi-type node relationships.",
    tags: ["SQLite", "Campaign Detection", "10% weight"],
    colSpan: 2,
  },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: "#080d1a" }}>
      {/* WebGL Background */}
      <ShaderAnimation />

      {/* Hero content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6">
        <LandingHero />

        {/* CTA */}
        <Link href="/input">
          <LiquidButton size="lg">
            Start Analysis
          </LiquidButton>
        </Link>
      </div>

      {/* Bento grid below the fold */}
      <div className="relative z-10 max-w-[1100px] mx-auto px-6 pb-24">
        <div className="text-center mb-12">
          <p className="text-[11px] uppercase tracking-[0.12em] text-accent/60 mb-2">
            Detection Layers
          </p>
          <h2 className="text-[22px] font-medium text-slate-200 tracking-tight">
            Four Independent Intelligence Layers
          </h2>
          <p className="text-[13px] text-slate-500 mt-2 max-w-lg mx-auto">
            Each layer scores independently before fusion into a unified Final Risk Score (FRS).
          </p>
        </div>

        <BentoGrid className="grid-cols-1 md:grid-cols-3 auto-rows-[16rem]">
          {BENTO_ITEMS.map((item) => (
            <BentoCard key={item.name} {...item} />
          ))}
        </BentoGrid>
      </div>
    </div>
  );
}
