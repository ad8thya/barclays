"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAnalysis } from "@/context/AnalysisContext";
import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";

const NAV_ITEMS = [
  { href: "/",         label: "Input",    num: "01" },
  { href: "/analysis", label: "Analysis", num: "02" },
  { href: "/graph",    label: "Graph",    num: "03" },
  { href: "/score",    label: "Score",    num: "04" },
];

export default function Navbar() {
  const pathname = usePathname();
  const { incidentId, analyzing, scoreResult } = useAnalysis();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  const frs = scoreResult?.final_risk_score ?? null;
  const threatColor =
    frs === null ? "#475569"
    : frs >= 0.8 ? "#ef4444"
    : frs >= 0.7 ? "#f59e0b"
    :              "#10b981";

  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 40,
      background: "#0c0e12",
      borderBottom: "1px solid #1e2530",
      transition: "box-shadow 200ms ease",
      boxShadow: scrolled ? "0 1px 0 #1e2530" : "none",
    }}>

      {/* ── Main bar ── */}
      <div style={{
        maxWidth: 1280,
        margin: "0 auto",
        padding: "0 24px",
        height: scrolled ? 44 : 52,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        transition: "height 200ms ease",
      }}>

        {/* Brand */}
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <div style={{
            width: 24, height: 24,
            border: "1.5px solid #3b82f6",
            borderRadius: 4,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <span style={{
            fontFamily: "monospace",
            fontSize: 13,
            fontWeight: 600,
            color: "#e2e8f0",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}>
            CrossShield
          </span>
          <span style={{ width: 1, height: 14, background: "#1e2530", flexShrink: 0 }} />
          <span style={{
            fontFamily: "monospace",
            fontSize: 10,
            color: "#475569",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
            className="hide-xs"
          >
            Fraud Intelligence
          </span>
        </Link>

        {/* Desktop nav links */}
        <nav style={{ display: "flex", alignItems: "stretch" }} className="hide-mobile">
          {NAV_ITEMS.map(({ href, label, num }) => {
            const active = pathname === href;
            return (
              <NavLink key={href} href={href} active={active} num={num} label={label} scrolled={scrolled} />
            );
          })}
        </nav>

        {/* Right: incident pill + hamburger */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <IncidentPill
            incidentId={incidentId}
            analyzing={analyzing}
            frs={frs}
            threatColor={threatColor}
          />
          <button
            onClick={() => setMenuOpen(p => !p)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            style={{
              background: "none",
              border: "1px solid #1e2530",
              borderRadius: 4,
              padding: "5px 7px",
              cursor: "pointer",
              color: "#475569",
              display: "flex",
              alignItems: "center",
            }}
            className="show-mobile"
          >
            {menuOpen
              ? <X size={15} strokeWidth={1.5} />
              : <Menu size={15} strokeWidth={1.5} />
            }
          </button>
        </div>
      </div>

      {/* ── Mobile dropdown ── */}
      {menuOpen && (
        <div style={{ borderTop: "1px solid #1e2530", background: "#0c0e12" }}>
          {NAV_ITEMS.map(({ href, label, num }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "11px 24px",
                  fontSize: 11,
                  fontFamily: "monospace",
                  fontWeight: active ? 600 : 400,
                  color: active ? "#e2e8f0" : "#475569",
                  textDecoration: "none",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  borderLeft: active ? "2px solid #3b82f6" : "2px solid transparent",
                  background: active ? "#13161e" : "transparent",
                }}
              >
                <span style={{ fontSize: 9, color: active ? "#3b82f6" : "#334155" }}>{num}</span>
                {label}
              </Link>
            );
          })}
        </div>
      )}

      <style>{`
        @keyframes navPulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.25; }
        }
        @media (max-width: 768px) {
          .hide-mobile { display: none !important; }
          .show-mobile  { display: flex !important; }
        }
        @media (min-width: 769px) {
          .show-mobile { display: none !important; }
        }
        @media (max-width: 480px) {
          .hide-xs { display: none !important; }
        }
      `}</style>
    </header>
  );
}

/* ── Sub-components ── */

function NavLink({ href, active, num, label, scrolled }) {
  const [hovered, setHovered] = useState(false);
  return (
    <Link
      href={href}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "0 14px",
        height: scrolled ? 44 : 52,
        fontSize: 11,
        fontFamily: "monospace",
        fontWeight: active ? 600 : 400,
        color: active ? "#e2e8f0" : hovered ? "#94a3b8" : "#475569",
        textDecoration: "none",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        borderBottom: active ? "2px solid #3b82f6" : "2px solid transparent",
        transition: "color 120ms ease, border-color 120ms ease",
      }}
    >
      <span style={{ fontSize: 9, color: active ? "#3b82f6" : "#334155" }}>{num}</span>
      {label}
    </Link>
  );
}

function IncidentPill({ incidentId, analyzing, frs, threatColor }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 7,
      padding: "4px 10px",
      border: "1px solid #1e2530",
      borderRadius: 4,
      background: "#0f1117",
    }}>
      {/* Status dot */}
      <span style={{
        width: 6, height: 6,
        borderRadius: "50%",
        background: analyzing ? "#f59e0b" : threatColor,
        flexShrink: 0,
        animation: analyzing ? "navPulse 1s ease-in-out infinite" : "none",
      }} />

      {/* Incident ID */}
      <span style={{
        fontFamily: "monospace",
        fontSize: 10,
        color: "#475569",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        whiteSpace: "nowrap",
      }}>
        {incidentId || "—"}
      </span>

      {/* FRS score — only shown after analysis */}
      {frs !== null && (
        <>
          <span style={{ width: 1, height: 10, background: "#1e2530", flexShrink: 0 }} />
          <span style={{
            fontFamily: "monospace",
            fontSize: 10,
            fontWeight: 700,
            color: threatColor,
            letterSpacing: "0.04em",
          }}>
            {Math.round(frs * 100)}%
          </span>
        </>
      )}
    </div>
  );
}