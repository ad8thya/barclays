"use client";

import { useState, useEffect } from "react";

/* ── Icons ── */
function LockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function ArrowRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

/* ── Stat row shown inside live card ── */
function StatRow({ label, value, accent }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "7px 0",
      borderBottom: "1px solid rgba(255,255,255,0.03)",
    }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9,
        color: "#334155",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        fontWeight: 600,
        color: accent || "#475569",
      }}>
        {value}
      </span>
    </div>
  );
}

/* ── Drop zone subcomponent ── */
function DropZone({ locked, hint, types, icon, onDrop }) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!locked) setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); if (!locked && onDrop) onDrop(); }}
      style={{
        border: `1.5px dashed ${
          locked ? "rgba(255,255,255,0.04)"
          : dragOver ? "rgba(59,130,246,0.6)"
          : "rgba(255,255,255,0.07)"
        }`,
        borderRadius: 10,
        padding: "20px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        minHeight: 104,
        background: dragOver ? "rgba(59,130,246,0.05)" : "rgba(255,255,255,0.01)",
        transition: "border-color 0.2s, background 0.2s",
        cursor: locked ? "not-allowed" : "pointer",
        marginBottom: 16,
      }}
    >
      <div style={{ opacity: locked ? 0.15 : dragOver ? 1 : 0.35, transition: "opacity 0.2s" }}>
        {icon}
      </div>
      <p style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: locked ? "#1e2530" : dragOver ? "#60a5fa" : "#334155",
        textAlign: "center",
        transition: "color 0.2s",
        lineHeight: 1.6,
      }}>
        {locked ? "Dataset import unavailable" : hint}
      </p>
      {!locked && (
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          color: "#1e2530",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}>
          {types}
        </p>
      )}
    </div>
  );
}

/*
  ModeCard props:
  - icon: ReactNode
  - label: string
  - sublabel: string
  - description: string
  - badge: string
  - badgeColor: hex string
  - accentColor: hex string  (used for borders, glows, cta)
  - locked: bool
  - dropzone: { icon, hint, types }
  - stats: [{ label, value, accent }]   — shown only on live card
  - cta: string
  - dim: bool
  - delay: number (ms)
  - onClick: fn
*/
export default function ModeCard({
  icon,
  label,
  sublabel,
  description,
  badge,
  badgeColor = "#3b82f6",
  accentColor = "#3b82f6",
  locked = false,
  dropzone,
  stats,
  cta,
  dim = false,
  delay = 0,
  onClick,
}) {
  const [mounted, setMounted] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  const isActive = hovered && !locked;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={!locked ? onClick : undefined}
      style={{
        flex: 1,
        minWidth: 0,
        position: "relative",
        borderRadius: 16,
        border: `1px solid ${
          locked ? "rgba(255,255,255,0.04)"
          : isActive ? `${accentColor}35`
          : "rgba(255,255,255,0.07)"
        }`,
        background: locked
          ? "rgba(8,12,22,0.6)"
          : isActive
          ? `rgba(10,15,30,0.85)`
          : "rgba(10,15,30,0.75)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        padding: "36px 32px 30px",
        display: "flex",
        flexDirection: "column",
        cursor: locked ? "default" : "pointer",
        opacity: dim ? 0.3 : mounted ? 1 : 0,
        transform: mounted
          ? isActive && !locked ? "translateY(-3px)" : "translateY(0)"
          : "translateY(18px)",
        transition: `
          opacity 0.55s ease,
          transform 0.55s ease,
          border-color 0.25s ease,
          background 0.25s ease,
          box-shadow 0.25s ease
        `,
        boxShadow: isActive && !locked
          ? `0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px ${accentColor}20, inset 0 1px 0 ${accentColor}15`
          : "0 8px 32px rgba(0,0,0,0.25)",
        overflow: "hidden",
      }}
    >
      {/* Top edge glow — only on live card */}
      {!locked && (
        <div style={{
          position: "absolute",
          top: 0,
          left: "15%",
          right: "15%",
          height: 1,
          background: `linear-gradient(90deg, transparent, ${accentColor}55, transparent)`,
          opacity: isActive ? 1 : 0.4,
          transition: "opacity 0.3s",
          pointerEvents: "none",
        }} />
      )}

      {/* Corner accent — live card only */}
      {!locked && (
        <div style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 80,
          height: 80,
          background: `radial-gradient(circle at top right, ${accentColor}0d 0%, transparent 70%)`,
          pointerEvents: "none",
          borderRadius: "0 16px 0 0",
        }} />
      )}

      {/* Badge */}
      {badge && (
        <div style={{
          alignSelf: "flex-start",
          display: "flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 10px",
          borderRadius: 4,
          border: `1px solid ${badgeColor}25`,
          background: `${badgeColor}0e`,
          marginBottom: 26,
        }}>
          {locked ? (
            <span style={{ color: badgeColor, opacity: 0.5, display: "flex" }}>
              <LockIcon />
            </span>
          ) : (
            <span style={{
              width: 5,
              height: 5,
              borderRadius: "50%",
              background: badgeColor,
              opacity: 0.8,
              boxShadow: `0 0 6px ${badgeColor}80`,
              animation: "modePulse 2s ease-in-out infinite",
              flexShrink: 0,
            }} />
          )}
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 8,
            fontWeight: 700,
            color: badgeColor,
            textTransform: "uppercase",
            letterSpacing: "0.14em",
            opacity: locked ? 0.5 : 0.9,
          }}>
            {badge}
          </span>
        </div>
      )}

      {/* Icon */}
      <div style={{
        width: 48,
        height: 48,
        borderRadius: 11,
        background: locked ? "rgba(255,255,255,0.02)" : `${accentColor}0f`,
        border: `1px solid ${locked ? "rgba(255,255,255,0.05)" : `${accentColor}20`}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 22,
        transition: "background 0.25s, border-color 0.25s",
        flexShrink: 0,
      }}>
        {icon}
      </div>

      {/* Label */}
      <h2 style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 18,
        fontWeight: 700,
        color: locked ? "#2d3a4a" : "#e2e8f0",
        letterSpacing: "0.01em",
        marginBottom: 5,
        transition: "color 0.2s",
      }}>
        {label}
      </h2>

      <p style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9,
        color: locked ? "#1e2530" : "#334155",
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        marginBottom: 14,
      }}>
        {sublabel}
      </p>

      {/* Thin divider */}
      <div style={{
        height: 1,
        background: locked ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.04)",
        marginBottom: 16,
      }} />

      {/* Description */}
      <p style={{
        fontSize: 12,
        color: locked ? "#1e2530" : "#475569",
        lineHeight: 1.75,
        marginBottom: 22,
        fontFamily: "'JetBrains Mono', monospace",
        flexGrow: 1,
      }}>
        {description}
      </p>

      {/* Stats — live card only */}
      {stats && !locked && (
        <div style={{ marginBottom: 18 }}>
          {stats.map((s) => (
            <StatRow key={s.label} label={s.label} value={s.value} accent={s.accent} />
          ))}
        </div>
      )}

      {/* Drop zone */}
      {dropzone && (
        <DropZone
          locked={locked}
          hint={dropzone.hint}
          types={dropzone.types}
          icon={dropzone.icon}
          onDrop={!locked ? onClick : undefined}
        />
      )}

      {/* CTA button */}
      <button
        disabled={locked}
        onClick={!locked ? onClick : undefined}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          width: "100%",
          padding: "12px 20px",
          borderRadius: 9,
          border: `1px solid ${locked ? "rgba(255,255,255,0.04)" : `${accentColor}30`}`,
          background: locked
            ? "rgba(255,255,255,0.02)"
            : isActive
            ? `${accentColor}22`
            : `${accentColor}12`,
          cursor: locked ? "not-allowed" : "pointer",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          fontWeight: 700,
          color: locked ? "#1e2530" : accentColor,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          transition: "background 0.2s, border-color 0.2s",
        }}
      >
        {locked ? (
          <>
            <span style={{ opacity: 0.5, display: "flex" }}><LockIcon /></span>
            Enterprise Feature
          </>
        ) : (
          <>
            {cta}
            <ArrowRight />
          </>
        )}
      </button>

      {/* Locked footer note */}
      {locked && (
        <div style={{
          marginTop: 10,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 5,
          opacity: 0.4,
        }}>
          <span style={{ color: "#334155", display: "flex" }}><ChevronRight /></span>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            color: "#334155",
            letterSpacing: "0.06em",
          }}>
            Routes to compiled intelligence dashboard
          </span>
        </div>
      )}

      <style>{`
        @keyframes modePulse {
          0%, 100% { opacity: 0.8; }
          50%       { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}