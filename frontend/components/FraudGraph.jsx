"use client";

import { useRef, useEffect } from "react";

/* ─── Type-based visual config ─── */
const NODE_CONFIG = {
  incident: { radius: 22, shape: "circle", defaultColor: "#3b82f6" },
  domain:   { radius: 16, shape: "diamond", defaultColor: "#a855f7" },
  ip:       { radius: 14, shape: "square",  defaultColor: "#06b6d4" },
};

const EDGE_COLORS = {
  uses_domain:   "rgba(168,85,247,0.25)",
  uses_ip:       "rgba(6,182,212,0.25)",
  shared_signal: "rgba(239,68,68,0.30)",
};

function riskColor(score) {
  if (score == null) return null;
  if (score >= 0.8) return "#ef4444";
  if (score >= 0.6) return "#f59e0b";
  return "#3b82f6";
}

function nodeColor(d) {
  const cfg = NODE_CONFIG[d.type] || NODE_CONFIG.incident;
  return riskColor(d.risk_score) || cfg.defaultColor;
}

function nodeRadius(d) {
  return (NODE_CONFIG[d.type] || NODE_CONFIG.incident).radius;
}

export default function FraudGraph({ graphData }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;
    import("d3").then((d3) => renderGraph(d3, containerRef.current, graphData));
  }, [graphData]);

  if (!graphData) {
    return (
      <div className="glass-card overflow-hidden w-full h-full min-h-[480px] flex flex-col items-center justify-center network-pattern">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#1e293b" strokeWidth="1.5" className="mb-4">
          <circle cx="5" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><circle cx="19" cy="6" r="2" />
          <line x1="6.5" y1="7.5" x2="10.5" y2="16.5" /><line x1="17.5" y1="7.5" x2="13.5" y2="16.5" />
          <line x1="7" y1="6" x2="17" y2="6" />
        </svg>
        <p className="text-sm text-slate-600 font-medium">Run analysis to map campaign infrastructure</p>
        <p className="text-[11px] text-slate-700 mt-1">Nodes = incidents + domains + IPs — edges show relationships</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="glass-card overflow-hidden w-full h-full min-h-[480px] relative" />
  );
}

/* ─── D3 Renderer ─── */
function renderGraph(d3, container, graphData) {
  container.innerHTML = "";

  const width  = container.clientWidth  || 700;
  const height = container.clientHeight || 480;

  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const defs = svg.append("defs");

  // Glow filter
  const glow = defs.append("filter").attr("id", "glow");
  glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
  const fm = glow.append("feMerge");
  fm.append("feMergeNode").attr("in", "coloredBlur");
  fm.append("feMergeNode").attr("in", "SourceGraphic");

  // Arrow marker
  defs.append("marker").attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10").attr("refX", 28).attr("refY", 0)
    .attr("markerWidth", 5).attr("markerHeight", 5).attr("orient", "auto")
    .append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "rgba(255,255,255,0.12)");

  const nodes = (graphData.nodes || []).map((n) => ({ ...n }));
  const edges = (graphData.edges || []).map((e) => ({ ...e }));

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(edges).id((d) => d.id).distance(140))
    .force("charge", d3.forceManyBody().strength(-350))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius((d) => nodeRadius(d) + 10));

  // Tooltip
  const tooltip = d3.select(container).append("div")
    .style("position", "absolute").style("pointer-events", "none")
    .style("background", "rgba(10,15,30,0.95)").style("backdrop-filter", "blur(8px)")
    .style("border", "1px solid rgba(255,255,255,0.08)")
    .style("border-radius", "8px").style("padding", "10px 14px")
    .style("font-size", "11px").style("color", "#e2e8f0")
    .style("display", "none").style("z-index", "10").style("min-width", "160px");

  // ── Edges ──
  const link = svg.append("g").selectAll("line").data(edges).enter().append("line")
    .attr("stroke", (d) => EDGE_COLORS[d.relation] || "rgba(255,255,255,0.06)")
    .attr("stroke-width", (d) => d.relation === "shared_signal" ? 2 : 1.2)
    .attr("stroke-dasharray", (d) => d.relation === "shared_signal" ? "4 3" : null)
    .attr("marker-end", "url(#arrow)");

  // Edge labels
  const linkLabel = svg.append("g").selectAll("text").data(edges).enter().append("text")
    .attr("font-size", "7px").attr("fill", "#475569").attr("text-anchor", "middle")
    .attr("font-family", "monospace")
    .text((d) => d.relation === "shared_signal" ? (d.signal || "shared") : d.relation.replace("uses_", ""));

  // ── Node groups ──
  const node = svg.append("g").selectAll("g").data(nodes).enter().append("g")
    .style("cursor", "grab")
    .call(d3.drag()
      .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on("end",   (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  // Outer glow
  node.append("circle")
    .attr("r", (d) => nodeRadius(d) + 6)
    .attr("fill", (d) => nodeColor(d)).attr("fill-opacity", 0.06);

  // Main shape
  node.each(function (d) {
    const g = d3.select(this);
    const r  = nodeRadius(d);
    const c  = nodeColor(d);
    const cfg = NODE_CONFIG[d.type] || NODE_CONFIG.incident;

    if (cfg.shape === "diamond") {
      g.append("polygon")
        .attr("points", `0,${-r} ${r},0 0,${r} ${-r},0`)
        .attr("fill", c).attr("fill-opacity", 0.12)
        .attr("stroke", c).attr("stroke-width", 2).attr("stroke-opacity", 0.6)
        .style("filter", "url(#glow)");
    } else if (cfg.shape === "square") {
      const half = r * 0.8;
      g.append("rect")
        .attr("x", -half).attr("y", -half).attr("width", half * 2).attr("height", half * 2)
        .attr("rx", 3)
        .attr("fill", c).attr("fill-opacity", 0.12)
        .attr("stroke", c).attr("stroke-width", 2).attr("stroke-opacity", 0.6)
        .style("filter", "url(#glow)");
    } else {
      g.append("circle").attr("r", r)
        .attr("fill", c).attr("fill-opacity", 0.1)
        .attr("stroke", c).attr("stroke-width", 2).attr("stroke-opacity", 0.6)
        .style("filter", "url(#glow)");
    }
  });

  // Inner dot (incidents only)
  node.filter((d) => d.type === "incident")
    .append("circle").attr("r", 4).attr("fill", (d) => nodeColor(d)).attr("fill-opacity", 0.8);

  // Type badge (domain / ip)
  node.filter((d) => d.type !== "incident")
    .append("text").attr("text-anchor", "middle").attr("dy", "0.35em")
    .attr("font-size", "8px").attr("font-weight", "700").attr("fill", (d) => nodeColor(d))
    .attr("font-family", "monospace")
    .text((d) => d.type === "domain" ? "D" : "IP");

  // Label above
  node.append("text")
    .attr("text-anchor", "middle").attr("dy", (d) => -(nodeRadius(d) + 10))
    .attr("font-size", (d) => d.type === "incident" ? "10px" : "8px")
    .attr("font-weight", "600")
    .attr("fill", (d) => d.type === "incident" ? "#94a3b8" : "#64748b")
    .attr("font-family", "monospace")
    .text((d) => d.label || d.id);

  // Score below (incidents only)
  node.filter((d) => d.type === "incident")
    .append("text").attr("text-anchor", "middle").attr("dy", 36)
    .attr("font-size", "9px").attr("font-weight", "700")
    .attr("fill", (d) => nodeColor(d)).attr("font-family", "monospace")
    .text((d) => d.risk_score != null ? (d.risk_score * 100).toFixed(0) + "%" : "—");

  // ── Hover ──
  node.on("mouseover", function (e, d) {
    link
      .attr("stroke", (l) => (l.source.id === d.id || l.target.id === d.id)
        ? nodeColor(d) : "rgba(255,255,255,0.03)")
      .attr("stroke-width", (l) => (l.source.id === d.id || l.target.id === d.id) ? 2.5 : 1);
    node.attr("opacity", (n) => {
      if (n.id === d.id) return 1;
      return edges.some((ed) =>
        (ed.source.id === d.id && ed.target.id === n.id) ||
        (ed.target.id === d.id && ed.source.id === n.id)
      ) ? 1 : 0.25;
    });
    const risk = d.risk_score != null ? (d.risk_score * 100).toFixed(0) + "%" : "—";
    const camp = d.campaign_id || "None";
    const typeLabel = d.type.charAt(0).toUpperCase() + d.type.slice(1);
    tooltip.style("display", "block")
      .style("left", (e.offsetX + 16) + "px").style("top", (e.offsetY - 10) + "px")
      .html(
        `<div style="font-weight:700;font-size:12px;margin-bottom:4px;color:${nodeColor(d)}">${d.label || d.id}</div>` +
        `<div style="color:#64748b">Type: <span style="color:#e2e8f0;font-weight:600">${typeLabel}</span></div>` +
        (d.type === "incident" ? `<div style="color:#64748b">Risk: <span style="color:#e2e8f0;font-weight:600">${risk}</span></div>` : "") +
        `<div style="color:#64748b">Campaign: <span style="color:#e2e8f0">${camp}</span></div>` +
        (d.timestamp ? `<div style="color:#64748b;font-size:10px;margin-top:2px">${d.timestamp.split("T")[0]}</div>` : "")
      );
  }).on("mouseout", function () {
    link.attr("stroke", (d) => EDGE_COLORS[d.relation] || "rgba(255,255,255,0.06)")
      .attr("stroke-width", (d) => d.relation === "shared_signal" ? 2 : 1.2);
    node.attr("opacity", 1);
    tooltip.style("display", "none");
  });

  // ── Tick ──
  simulation.on("tick", () => {
    link.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2 - 8);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });

  // ── Legend ──
  const legend = svg.append("g").attr("transform", `translate(14, ${height - 80})`);
  const items = [
    { label: "Incident", shape: "circle", color: "#3b82f6" },
    { label: "Domain",   shape: "diamond", color: "#a855f7" },
    { label: "IP",       shape: "square",  color: "#06b6d4" },
  ];
  items.forEach((item, i) => {
    const g = legend.append("g").attr("transform", `translate(0, ${i * 20})`);
    if (item.shape === "circle")
      g.append("circle").attr("cx", 6).attr("cy", 0).attr("r", 5).attr("fill", item.color).attr("fill-opacity", 0.5);
    else if (item.shape === "diamond")
      g.append("polygon").attr("points", "6,-5 11,0 6,5 1,0").attr("fill", item.color).attr("fill-opacity", 0.5);
    else
      g.append("rect").attr("x", 1).attr("y", -5).attr("width", 10).attr("height", 10).attr("rx", 2).attr("fill", item.color).attr("fill-opacity", 0.5);
    g.append("text").attr("x", 18).attr("y", 4).attr("font-size", "9px").attr("fill", "#64748b").text(item.label);
  });
}
