"use client";

import { useEffect, useState } from "react";
import { useMotionValue, useSpring } from "framer-motion";

/* ─────────────────────────────────────────────
   Spring-animated number counter
   (ported from prompt's useNumberCounter hook)
───────────────────────────────────────────── */
function useNumberCounter({ value, delay = 0, decimalPlaces = 0 }) {
  const [displayValue, setDisplayValue] = useState(0);
  const [rawValue, setRawValue]         = useState(0);

  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 });

  useEffect(() => {
    const t = setTimeout(() => {
      motionValue.set(value);
    }, delay * 1000 + 120); // small boot delay
    return () => clearTimeout(t);
  }, [motionValue, value, delay]);

  useEffect(() => {
    const unsub = springValue.on("change", (latest) => {
      setDisplayValue(Number(latest.toFixed(decimalPlaces)));
      setRawValue(latest);
    });
    return unsub;
  }, [springValue, decimalPlaces]);

  return { displayValue, rawValue };
}

/* ─────────────────────────────────────────────
   Arc geometry helpers
───────────────────────────────────────────── */
const CX = 100, CY = 100, R = 76;
const GAP_DEG   = 60;                         // gap at the bottom
const ARC_DEG   = 360 - GAP_DEG;             // 300° arc
const START_DEG = 90 + GAP_DEG / 2;          // 120° (8 o'clock)

function degToRad(d) { return (d * Math.PI) / 180; }

function polarToXY(cx, cy, r, deg) {
  const rad = degToRad(deg);
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx, cy, r, startDeg, endDeg) {
  const s    = polarToXY(cx, cy, r, startDeg);
  const e    = polarToXY(cx, cy, r, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

function valToDeg(pct) {
  return START_DEG + (pct / 100) * ARC_DEG;
}

/* Stroke-dasharray for a partial arc on a full-circle path */
function useArcDash(pct) {
  const circumference = 2 * Math.PI * R;
  const arcLen        = (ARC_DEG / 360) * circumference;
  const filled        = (pct / 100) * arcLen;
  return { filled, arcLen, circumference };
}

/* ─────────────────────────────────────────────
   Threshold zones rendered as thin arc bands
───────────────────────────────────────────── */
const ZONES = [
  { from: 0,   to: 40,  color: "#10b981" },
  { from: 40,  to: 100, color: "#ef4444" },
];


const TICKS = [0, 20, 40, 60, 80, 100];

/* ─────────────────────────────────────────────
   Main component
───────────────────────────────────────────── */
export default function ScoreGauge({ score = 0 }) {
  const pct    = Math.max(0, Math.min(1, score)) * 100;
  const { displayValue, rawValue } = useNumberCounter({ value: pct, decimalPlaces: 0 });

  const threatColor = rawValue >= 40 ? "#ef4444" : "#10b981";
  const verdict = score >= 0.4 ? "HIGH RISK" : score > 0 ? "LOW RISK" : "—";

  const { filled, arcLen, circumference } = useArcDash(rawValue);

  // The full arc starts at START_DEG on the SVG circle.
  // We rotate the <circle> element so its zero-point aligns with START_DEG.
  const rotateOffset = `rotate(${START_DEG - 90}, ${CX}, ${CY})`;

  return (
    <div style={{
      background: "#13161e",
      border: "1px solid #1e2530",
      borderRadius: 6,
      padding: "28px 24px 20px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
    }}>
      <svg
        viewBox="0 0 200 200"
        width="100%"
        style={{ maxWidth: 220, userSelect: "none" }}
        fill="none"
      >
        {/* ── Zone bands (dim background) ── */}
        {ZONES.map(({ from, to, color }) => (
          <path
            key={from}
            d={arcPath(CX, CY, R, valToDeg(from), valToDeg(to))}
            stroke={color}
            strokeWidth={10}
            strokeLinecap="butt"
            opacity={0.1}
          />
        ))}

        {/* ── Track (full arc, dark) ── */}
        <circle
          cx={CX} cy={CY} r={R}
          stroke="#1e2530"
          strokeWidth={10}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeDashoffset={0}
          strokeLinecap="butt"
          transform={rotateOffset}
        />

        {/* ── Active filled arc (spring-animated via rawValue) ── */}
        {rawValue > 0 && (
          <circle
            cx={CX} cy={CY} r={R}
            stroke={threatColor}
            strokeWidth={10}
            strokeDasharray={`${filled} ${circumference}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform={rotateOffset}
            style={{ transition: "stroke 300ms ease" }}
          />
        )}

        {/* ── Tick marks ── */}
        {TICKS.map((val) => {
          const deg   = valToDeg(val);
          const outer = polarToXY(CX, CY, R + 7, deg);
          const inner = polarToXY(CX, CY, R - 4, deg);
          const lbl   = polarToXY(CX, CY, R + 18, deg);
          return (
            <g key={val}>
              <line
                x1={outer.x} y1={outer.y}
                x2={inner.x} y2={inner.y}
                stroke="#2a3545" strokeWidth={1.5}
              />
              <text
                x={lbl.x} y={lbl.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#334155"
                fontSize={8}
                fontFamily="monospace"
                fontWeight={500}
              >
                {val}
              </text>
            </g>
          );
        })}

        {/* ── Needle ── */}
        <NeedleArm pct={rawValue} color={threatColor} />

        {/* ── Centre hub ── */}
        <circle cx={CX} cy={CY} r={5}  fill={threatColor} opacity={0.9} />
        <circle cx={CX} cy={CY} r={2.5} fill="#0f1117" />

        {/* ── Score text in centre ── */}
        <text
          x={CX} y={CY - 14}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={threatColor}
          fontSize={16}
          fontWeight={700}
          fontFamily="monospace"
          style={{ transition: "fill 300ms ease" }}
        >
          {Math.round(displayValue)}
        </text>
        <text
          x={CX} y={CY + 10}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#334155"
          fontSize={9}
          fontFamily="monospace"
          fontWeight={500}
          letterSpacing={2}
        >
          / 100
        </text>
      </svg>

      {/* ── Verdict label ── */}
      <div style={{
        marginTop: 12,
        fontFamily: "monospace",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.18em",
        textTransform: "uppercase",
        color: threatColor,
        transition: "color 300ms ease",
      }}>
        {verdict}
      </div>

      {/* ── Threshold legend ── */}
      <div style={{
        display: "flex",
        gap: 16,
        marginTop: 14,
        paddingTop: 12,
        borderTop: "1px solid #1e2530",
        width: "100%",
        justifyContent: "center",
      }}>
        {[
  { label: "Low Risk",  color: "#10b981", range: "< 40" },
  { label: "High Risk", color: "#ef4444", range: ">= 40" },
].map(({ label, color, range }) => (
  <div key={label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
    <span style={{
      width: 6, height: 6,
      borderRadius: "50%",
      background: color,
      flexShrink: 0,
    }} />
    <span style={{
      fontFamily: "monospace",
      fontSize: 9,
      color: "#475569",
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
      {range}
    </span>
  </div>
))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Needle — rendered as a <line> from centre
   pointing outward, angle derived from pct
───────────────────────────────────────────── */
function NeedleArm({ pct, color }) {
  const deg     = valToDeg(pct);
  const tip     = polarToXY(CX, CY, R - 14, deg);
  const tailDeg = deg + 180;
  const tail    = polarToXY(CX, CY, 8, tailDeg);

  return (
    <line
      x1={tail.x} y1={tail.y}
      x2={tip.x}  y2={tip.y}
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      style={{ transition: "stroke 300ms ease" }}
    />
  );
}