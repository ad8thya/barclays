"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as THREE from "three";
import LandingHero from "@/components/LandingHero";

function LockIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function ArrowRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function UploadIcon({ size = 32, color = "#1e293b" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
}

function DatabaseIcon({ size = 32, color = "#1e293b" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function ModeCard({
  icon,
  label,
  sublabel,
  description,
  badge,
  badgeColor,
  dropzone,
  cta,
  ctaColor,
  locked,
  dim,
  onHover,
  onLeave,
  onClick,
  delay = 0,
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  const borderColor = locked
    ? "rgba(255,255,255,0.04)"
    : isDragOver
    ? "rgba(59,130,246,0.5)"
    : "rgba(255,255,255,0.07)";

  const bgColor = locked
    ? "rgba(10,15,30,0.55)"
    : isDragOver
    ? "rgba(59,130,246,0.06)"
    : "rgba(10,15,30,0.72)";

  return (
    <div
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onClick={!locked ? onClick : undefined}
      style={{
        flex: 1,
        minWidth: 0,
        background: bgColor,
        border: `1px solid ${borderColor}`,
        borderRadius: 16,
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        padding: "40px 36px 36px",
        display: "flex",
        flexDirection: "column",
        cursor: locked ? "default" : "pointer",
        opacity: dim ? 0.38 : mounted ? 1 : 0,
        transform: mounted ? "translateY(0)" : "translateY(20px)",
        transition: "opacity 0.55s ease, transform 0.55s ease, border-color 0.2s ease, background 0.2s ease",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {!locked && (
        <div style={{
          position: "absolute",
          top: 0,
          left: "20%",
          right: "20%",
          height: 1,
          background: "linear-gradient(90deg, transparent, rgba(59,130,246,0.4), transparent)",
          pointerEvents: "none",
        }} />
      )}

      {badge && (
        <div style={{
          alignSelf: "flex-start",
          display: "flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 9px",
          borderRadius: 4,
          border: `1px solid ${badgeColor}33`,
          background: `${badgeColor}11`,
          marginBottom: 28,
        }}>
          {locked && (
            <span style={{ color: badgeColor, opacity: 0.7, display: "flex" }}>
              <LockIcon />
            </span>
          )}
          <span style={{
            fontFamily: "monospace",
            fontSize: 9,
            fontWeight: 700,
            color: badgeColor,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            opacity: 0.85,
          }}>
            {badge}
          </span>
        </div>
      )}

      <div style={{
        width: 52,
        height: 52,
        borderRadius: 12,
        background: locked ? "rgba(255,255,255,0.03)" : "rgba(59,130,246,0.08)",
        border: `1px solid ${locked ? "rgba(255,255,255,0.05)" : "rgba(59,130,246,0.15)"}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 24,
        flexShrink: 0,
      }}>
        {icon}
      </div>

      <h2 style={{
        fontFamily: "monospace",
        fontSize: 20,
        fontWeight: 700,
        color: locked ? "#475569" : "#e2e8f0",
        letterSpacing: "0.02em",
        marginBottom: 6,
      }}>
        {label}
      </h2>
      <p style={{
        fontFamily: "monospace",
        fontSize: 10,
        color: locked ? "#334155" : "#475569",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        marginBottom: 16,
      }}>
        {sublabel}
      </p>

      <p style={{
        fontSize: 13,
        color: locked ? "#2d3a4a" : "#64748b",
        lineHeight: 1.7,
        marginBottom: 28,
        flexGrow: 1,
      }}>
        {description}
      </p>

      {dropzone && (
        <div
          onDragOver={(e) => { e.preventDefault(); if (!locked) setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setIsDragOver(false); if (!locked && onClick) onClick(); }}
          style={{
            border: `2px dashed ${
              locked
                ? "rgba(255,255,255,0.04)"
                : isDragOver
                ? "rgba(59,130,246,0.55)"
                : "rgba(255,255,255,0.07)"
            }`,
            borderRadius: 10,
            padding: "22px 20px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            marginBottom: 20,
            transition: "border-color 0.2s ease, background 0.2s ease",
            background: isDragOver ? "rgba(59,130,246,0.04)" : "transparent",
            minHeight: 110,
          }}
        >
          <div style={{ opacity: locked ? 0.2 : isDragOver ? 1 : 0.4, transition: "opacity 0.2s" }}>
            {dropzone.icon}
          </div>
          <p style={{
            fontFamily: "monospace",
            fontSize: 11,
            color: locked ? "#1e2530" : isDragOver ? "#60a5fa" : "#334155",
            textAlign: "center",
            transition: "color 0.2s",
          }}>
            {locked ? "Dataset import unavailable" : dropzone.hint}
          </p>
          {!locked && (
            <p style={{
              fontFamily: "monospace",
              fontSize: 10,
              color: "#1e2530",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}>
              {dropzone.types}
            </p>
          )}
        </div>
      )}

      <button
        disabled={locked}
        onClick={!locked ? onClick : undefined}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          width: "100%",
          padding: "13px 20px",
          borderRadius: 10,
          border: `1px solid ${locked ? "rgba(255,255,255,0.04)" : `${ctaColor}33`}`,
          background: locked ? "rgba(255,255,255,0.02)" : `${ctaColor}14`,
          cursor: locked ? "not-allowed" : "pointer",
          fontFamily: "monospace",
          fontSize: 12,
          fontWeight: 700,
          color: locked ? "#1e2530" : ctaColor,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          transition: "background 0.2s ease, border-color 0.2s ease",
        }}
      >
        {locked ? (
          <>
            <LockIcon />
            Enterprise Feature
          </>
        ) : (
          <>
            {cta}
            <ArrowRight />
          </>
        )}
      </button>

      {locked && (
        <div style={{
          marginTop: 12,
          textAlign: "center",
          fontFamily: "monospace",
          fontSize: 10,
          color: "#1e2530",
          letterSpacing: "0.06em",
        }}>
          Routes to compiled intelligence dashboard
        </div>
      )}
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [hoveredCard, setHoveredCard] = useState(null);
  const [headerMounted, setHeaderMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setHeaderMounted(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0f1e",
      position: "relative",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "flex-start",
      padding: "0",
      overflow: "hidden",
    }}>
      {/* Content */}
      <div style={{
        position: "relative",
        zIndex: 2,
        width: "100%",
        maxWidth: 960,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}>

        {/* LandingHero owns all background layers */}
        <LandingHero />

        {/* Card grid */}
        <div style={{
          display: "flex",
          gap: 16,
          width: "100%",
          alignItems: "stretch",
          padding: "0 0 48px",
        }}>
          <ModeCard
            delay={180}
            icon={<UploadIcon size={26} color="#3b82f6" />}
            label="Single Incident"
            sublabel="Individual Analysis"
            description="Submit a suspicious email, URL, attachment, or audio clip. All four analyzers run in parallel — results fused into a single risk score with graph correlation."
            badge="Live"
            badgeColor="#3b82f6"
            dropzone={{
              icon: <UploadIcon size={28} color="#3b82f6" />,
              hint: "Drop email file or fill fields manually",
              types: ".eml · .msg · .txt",
            }}
            cta="Begin Analysis"
            ctaColor="#3b82f6"
            locked={false}
            dim={hoveredCard === "dataset"}
            onHover={() => setHoveredCard("single")}
            onLeave={() => setHoveredCard(null)}
            onClick={() => router.push("/input")}
          />

          <div style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            flexShrink: 0,
            padding: "0 4px",
          }}>
            <div style={{ width: 1, flex: 1, background: "rgba(255,255,255,0.04)" }} />
            <span style={{
              fontFamily: "monospace",
              fontSize: 9,
              color: "#1e2530",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              writingMode: "vertical-rl",
              transform: "rotate(180deg)",
            }}>
              or
            </span>
            <div style={{ width: 1, flex: 1, background: "rgba(255,255,255,0.04)" }} />
          </div>

          <ModeCard
            delay={320}
            icon={<DatabaseIcon size={26} color="#475569" />}
            label="Dataset Import"
            sublabel="Campaign Intelligence"
            description="Import a multi-incident dataset. CrossShield compiles graph correlations across all entries and surfaces a campaign-level intelligence report."
            badge="Enterprise"
            badgeColor="#6366f1"
            dropzone={{
              icon: <DatabaseIcon size={28} color="#475569" />,
              hint: "",
              types: "",
            }}
            cta="Import Dataset"
            ctaColor="#6366f1"
            locked={true}
            dim={hoveredCard === "single"}
            onHover={() => setHoveredCard("dataset")}
            onLeave={() => setHoveredCard(null)}
            onClick={() => router.push("/score")}
          />
        </div>

        <div style={{
          marginTop: 0,
          marginBottom: 36,
          fontFamily: "monospace",
          fontSize: 10,
          color: "#1e2530",
          textAlign: "center",
          letterSpacing: "0.06em",
          opacity: headerMounted ? 1 : 0,
          transition: "opacity 0.8s ease 0.6s",
        }}>
          All analysis is performed locally against your configured backend endpoint.
        </div>
      </div>

      <style>{`
        @keyframes drift {
          0%   { transform: translate(0, 0) scale(1); }
          33%  { transform: translate(60px, 30px) scale(1.04); }
          66%  { transform: translate(-30px, 60px) scale(0.97); }
          100% { transform: translate(50px, -20px) scale(1.02); }
        }
      `}</style>
    </div>
  );
}