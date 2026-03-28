"use client";

import { Mail, Globe, Network } from "lucide-react";

export default function LandingHero() {
  return (
    <div className="flex flex-col items-center text-center px-4">
      {/* Shield SVG */}
      <div className="mb-8">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      </div>

      {/* Title */}
      <h1
        className="text-[40px] sm:text-[56px] font-medium text-white tracking-[0.12em] uppercase mb-3"
        style={{ letterSpacing: "0.12em" }}
      >
        CROSSSHIELD
      </h1>

      {/* Subtitle */}
      <p className="text-[16px] text-accent/70 tracking-[0.04em] mb-2">
        Fraud Intelligence Platform
      </p>
      <p className="text-[13px] text-slate-500 max-w-md mb-10">
        Multi-layer AI fraud detection fusing email phishing, website spoofing,
        attachment analysis, and graph intelligence into a unified risk score.
      </p>
    </div>
  );
}
