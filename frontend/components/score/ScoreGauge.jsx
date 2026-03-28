"use client";

import { useEffect, useRef, useState } from "react";

export default function ScoreGauge({ score }) {
  const svgRef = useRef(null);
  const [displayScore, setDisplayScore] = useState(0);

  const size = 280;
  const cx = size / 2;
  const cy = size / 2 + 20;
  const radius = 110;
  const startAngle = -210;
  const endAngle = 30;
  const totalArc = endAngle - startAngle; // 240 degrees

  // Zones: 0-70 green, 70-80 amber, 80-100 red
  const zones = [
    { start: 0, end: 0.70, color: "#10b981" },
    { start: 0.70, end: 0.80, color: "#f59e0b" },
    { start: 0.80, end: 1.0, color: "#ef4444" },
  ];

  function polarToCartesian(angle) {
    const rad = (angle * Math.PI) / 180;
    return {
      x: cx + radius * Math.cos(rad),
      y: cy + radius * Math.sin(rad),
    };
  }

  function describeArc(startPct, endPct) {
    const sAngle = startAngle + startPct * totalArc;
    const eAngle = startAngle + endPct * totalArc;
    const s = polarToCartesian(sAngle);
    const e = polarToCartesian(eAngle);
    const largeArc = eAngle - sAngle > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${largeArc} 1 ${e.x} ${e.y}`;
  }

  // Animate score
  useEffect(() => {
    if (score == null || score === 0) { setDisplayScore(0); return; }
    const target = Math.round(score * 100);
    let current = 0;
    const step = target / 60;
    let frame;

    function animate() {
      current += step;
      if (current >= target) {
        setDisplayScore(target);
        return;
      }
      setDisplayScore(Math.round(current));
      frame = requestAnimationFrame(animate);
    }
    animate();
    return () => cancelAnimationFrame(frame);
  }, [score]);

  const verdictLabel =
    score >= 0.80 ? "OOB TRIGGERED" :
    score >= 0.70 ? "SUSPICIOUS" : "CLEAR";
  const verdictColor =
    score >= 0.80 ? "#ef4444" :
    score >= 0.70 ? "#f59e0b" : "#10b981";

  // Needle angle
  const needleAngle = startAngle + (score || 0) * totalArc;
  const needleEnd = polarToCartesian(needleAngle);
  const needleLen = radius - 15;
  const needleEndInner = {
    x: cx + needleLen * Math.cos((needleAngle * Math.PI) / 180),
    y: cy + needleLen * Math.sin((needleAngle * Math.PI) / 180),
  };

  // Tick marks
  const ticks = [0, 25, 50, 70, 80, 100];

  return (
    <div className="glass-card p-6 flex items-center justify-center">
      <svg width={size} height={size - 20} viewBox={`0 0 ${size} ${size - 20}`}>
        {/* Arc zones */}
        {zones.map((z, i) => (
          <path
            key={i}
            d={describeArc(z.start, z.end)}
            fill="none"
            stroke={z.color}
            strokeWidth={8}
            strokeLinecap="round"
            opacity={0.3}
          />
        ))}

        {/* Ticks */}
        {ticks.map((t) => {
          const angle = startAngle + (t / 100) * totalArc;
          const outer = {
            x: cx + (radius + 8) * Math.cos((angle * Math.PI) / 180),
            y: cy + (radius + 8) * Math.sin((angle * Math.PI) / 180),
          };
          const inner = {
            x: cx + (radius - 3) * Math.cos((angle * Math.PI) / 180),
            y: cy + (radius - 3) * Math.sin((angle * Math.PI) / 180),
          };
          return (
            <g key={t}>
              <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="#334155" strokeWidth={1.5} />
              <text
                x={cx + (radius + 20) * Math.cos((angle * Math.PI) / 180)}
                y={cy + (radius + 20) * Math.sin((angle * Math.PI) / 180)}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#475569"
                fontSize="9"
                fontFamily="monospace"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={needleEndInner.x}
          y2={needleEndInner.y}
          stroke={verdictColor}
          strokeWidth={2}
          strokeLinecap="round"
          style={{ transition: "all 1s ease-out" }}
        />
        <circle cx={cx} cy={cy} r={4} fill={verdictColor} />

        {/* Centre text */}
        <text
          x={cx}
          y={cy - 25}
          textAnchor="middle"
          fill="#e2e8f0"
          fontSize="36"
          fontWeight="500"
          fontFamily="system-ui, sans-serif"
        >
          {displayScore}
        </text>
        <text
          x={cx}
          y={cy - 5}
          textAnchor="middle"
          fill={verdictColor}
          fontSize="11"
          fontWeight="500"
          fontFamily="monospace"
          letterSpacing="0.1em"
        >
          {verdictLabel}
        </text>
      </svg>
    </div>
  );
}
