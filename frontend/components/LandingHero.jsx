"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

function ShaderBackground() {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    const vertexShader = `void main() { gl_Position = vec4(position, 1.0); }`;
    const fragmentShader = `
      precision highp float;
      uniform vec2 resolution;
      uniform float time;
      void main(void) {
        vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);
        float t = time * 0.05;
        float lineWidth = 0.002;
        vec3 color = vec3(0.0);
        for(int j = 0; j < 3; j++){
          for(int i = 0; i < 5; i++){
            color[j] += lineWidth * float(i*i) / abs(
              fract(t - 0.01*float(j) + float(i)*0.01)*5.0
              - length(uv)
              + mod(uv.x + uv.y, 0.2)
            );
          }
        }
        gl_FragColor = vec4(color[0], color[1], color[2], 1.0);
      }
    `;

    const camera = new THREE.Camera();
    camera.position.z = 1;
    const scene = new THREE.Scene();
    const geometry = new THREE.PlaneGeometry(2, 2);
    const uniforms = {
      time: { value: 1.0 },
      resolution: { value: new THREE.Vector2() },
    };
    const material = new THREE.ShaderMaterial({ uniforms, vertexShader, fragmentShader });
    scene.add(new THREE.Mesh(geometry, material));

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const resize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      renderer.setSize(w, h);
      uniforms.resolution.value.set(renderer.domElement.width, renderer.domElement.height);
    };
    resize();
    window.addEventListener("resize", resize);

    let animId;
    const tick = () => {
      animId = requestAnimationFrame(tick);
      uniforms.time.value += 0.05;
      renderer.render(scene, camera);
    };
    tick();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animId);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        opacity: 0.11,
        pointerEvents: "none",
        zIndex: 0,
      }}
    />
  );
}

function ScanLine() {
  return (
    <div style={{
      position: "fixed",
      left: 0,
      right: 0,
      height: 1,
      background: "linear-gradient(90deg, transparent 0%, rgba(59,130,246,0.25) 30%, rgba(59,130,246,0.5) 50%, rgba(59,130,246,0.25) 70%, transparent 100%)",
      animation: "scanline 8s ease-in-out infinite",
      pointerEvents: "none",
      zIndex: 1,
    }} />
  );
}

function GridOverlay() {
  return (
    <div style={{
      position: "fixed",
      inset: 0,
      zIndex: 0,
      pointerEvents: "none",
      backgroundImage: `
        linear-gradient(rgba(59,130,246,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59,130,246,0.025) 1px, transparent 1px)
      `,
      backgroundSize: "60px 60px",
      maskImage: "radial-gradient(ellipse 80% 60% at 50% 50%, black 30%, transparent 100%)",
      WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 50%, black 30%, transparent 100%)",
    }} />
  );
}

function AmbientBlobs() {
  return (
    <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
      <div style={{
        position: "absolute",
        width: 800,
        height: 800,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(59,130,246,0.055) 0%, transparent 65%)",
        top: "-300px",
        left: "-300px",
        animation: "blobDrift 30s ease-in-out infinite alternate",
      }} />
      <div style={{
        position: "absolute",
        width: 600,
        height: 600,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(99,102,241,0.04) 0%, transparent 65%)",
        bottom: "-200px",
        right: "-200px",
        animation: "blobDrift 24s ease-in-out infinite alternate-reverse",
      }} />
      <div style={{
        position: "absolute",
        width: 400,
        height: 400,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(16,185,129,0.025) 0%, transparent 65%)",
        top: "40%",
        right: "10%",
        animation: "blobDrift 20s ease-in-out infinite alternate",
        animationDelay: "-10s",
      }} />
    </div>
  );
}

function ShieldIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function SignalPill({ label, index }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 600 + index * 80);
    return () => clearTimeout(t);
  }, [index]);

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "5px 12px",
      border: "1px solid rgba(59,130,246,0.12)",
      borderRadius: 100,
      background: "rgba(59,130,246,0.05)",
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(6px)",
      transition: "opacity 0.4s ease, transform 0.4s ease",
    }}>
      <span style={{
        width: 4,
        height: 4,
        borderRadius: "50%",
        background: "#3b82f6",
        opacity: 0.6,
        flexShrink: 0,
      }} />
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9,
        color: "#475569",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        whiteSpace: "nowrap",
      }}>
        {label}
      </span>
    </div>
  );
}

const SIGNALS = ["Email Analysis", "Website Intel", "Audio Deepfake", "Attachment Scan", "Graph Correlation", "Score Fusion"];

export default function LandingHero() {
  const [tagMounted, setTagMounted] = useState(false);
  const [headingMounted, setHeadingMounted] = useState(false);
  const [subMounted, setSubMounted] = useState(false);

  useEffect(() => {
    setTimeout(() => setTagMounted(true), 100);
    setTimeout(() => setHeadingMounted(true), 250);
    setTimeout(() => setSubMounted(true), 420);
  }, []);

  return (
    <div style={{
      position: "relative",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      paddingBottom: 56,
      overflow: "visible",
      width: "100%",
    }}>
      <ShaderBackground />
      <GridOverlay />
      <AmbientBlobs />
      <ScanLine />

      <div style={{
        position: "relative",
        zIndex: 2,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 36,
          opacity: tagMounted ? 1 : 0,
          transform: tagMounted ? "translateY(0)" : "translateY(-10px)",
          transition: "opacity 0.5s ease, transform 0.5s ease",
        }}>
          <div style={{
            width: 28,
            height: 28,
            border: "1.5px solid #3b82f6",
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            <ShieldIcon />
          </div>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            fontWeight: 700,
            color: "#e2e8f0",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}>
            CrossShield
          </span>
          <span style={{ width: 1, height: 12, background: "#1e2530", flexShrink: 0 }} />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            color: "#2d3a4a",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
          }}>
            Fraud Intelligence
          </span>
        </div>

        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 7,
          padding: "4px 12px 4px 8px",
          border: "1px solid rgba(59,130,246,0.2)",
          borderRadius: 100,
          background: "rgba(59,130,246,0.07)",
          marginBottom: 28,
          opacity: tagMounted ? 1 : 0,
          transition: "opacity 0.5s ease 0.1s",
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#10b981",
            boxShadow: "0 0 6px rgba(16,185,129,0.6)",
            flexShrink: 0,
            animation: "pulse 2s ease-in-out infinite",
          }} />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: "#3b82f6",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}>
            v2.1 — Multi-Layer Analyzer
          </span>
        </div>

        <h1 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "clamp(30px, 4.5vw, 52px)",
          fontWeight: 700,
          color: "#e2e8f0",
          letterSpacing: "-0.02em",
          textAlign: "center",
          lineHeight: 1.15,
          marginBottom: 20,
          maxWidth: 700,
          opacity: headingMounted ? 1 : 0,
          transform: headingMounted ? "translateY(0)" : "translateY(14px)",
          transition: "opacity 0.6s ease, transform 0.6s ease",
        }}>
          Detect Fraud.<br />
          <span style={{
            background: "linear-gradient(90deg, #3b82f6 0%, #6366f1 60%, #3b82f6 100%)",
            backgroundSize: "200% 100%",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            animation: "shimmerText 4s linear infinite",
          }}>
            Before It Lands.
          </span>
        </h1>

        <p style={{
          fontSize: 14,
          color: "#475569",
          textAlign: "center",
          maxWidth: 480,
          lineHeight: 1.75,
          marginBottom: 36,
          fontFamily: "'JetBrains Mono', monospace",
          opacity: subMounted ? 1 : 0,
          transform: subMounted ? "translateY(0)" : "translateY(10px)",
          transition: "opacity 0.5s ease, transform 0.5s ease",
        }}>
          Submit a single suspicious email for real-time multi-signal analysis, or import a compiled dataset for campaign-level intelligence.
        </p>
      </div>

      <style>{`
        @keyframes blobDrift {
          0%   { transform: translate(0, 0) scale(1); }
          33%  { transform: translate(60px, 30px) scale(1.04); }
          66%  { transform: translate(-30px, 60px) scale(0.97); }
          100% { transform: translate(50px, -20px) scale(1.02); }
        }
        @keyframes scanline {
          0%   { top: -2px; opacity: 0; }
          10%  { opacity: 1; }
          90%  { opacity: 1; }
          100% { top: 100vh; opacity: 0; }
        }
        @keyframes shimmerText {
          0%   { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}