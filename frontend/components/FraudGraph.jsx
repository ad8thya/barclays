"use client";

import { useRef, useEffect } from "react";

export default function FraudGraph({ graphData }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!graphData) return;

    import("d3").then((d3) => {
      renderGraph(d3, containerRef.current, graphData);
    });
  }, [graphData]);

  // Empty state
  if (!graphData) {
    return (
      <div className="glass-card overflow-hidden w-full h-full min-h-[480px] flex flex-col items-center justify-center network-pattern">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#1e293b" strokeWidth="1.5" className="mb-4">
          <circle cx="5" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><circle cx="19" cy="6" r="2" />
          <line x1="6.5" y1="7.5" x2="10.5" y2="16.5" /><line x1="17.5" y1="7.5" x2="13.5" y2="16.5" />
          <line x1="7" y1="6" x2="17" y2="6" />
        </svg>
        <p className="text-sm text-slate-600 font-medium">Run analysis to map campaign infrastructure</p>
        <p className="text-[11px] text-slate-700 mt-1">Nodes represent incidents, edges show shared signals</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="glass-card overflow-hidden w-full h-full min-h-[480px] relative"
    />
  );
}

function renderGraph(d3, container, graphData) {
  container.innerHTML = "";

  const width = container.clientWidth || 700;
  const height = container.clientHeight || 480;

  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height);

  // Gradient definitions
  const defs = svg.append("defs");

  // Glow filter
  const glow = defs.append("filter").attr("id", "glow");
  glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
  const feMerge = glow.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "coloredBlur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");

  // Arrow marker
  defs
    .append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 30)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-4L8,0L0,4")
    .attr("fill", "rgba(255,255,255,0.1)");

  const nodes = (graphData.nodes || []).map((n) => ({ ...n }));
  const edges = (graphData.edges || []).map((e) => ({ ...e }));

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(edges).id((d) => d.id).distance(170))
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(50))
    .force("x", d3.forceX(width / 2).strength(0.08))   // ← pulls nodes toward center X
    .force("y", d3.forceY(height / 2).strength(0.08));  // ← pulls nodes toward center Y;

  // Tooltip
  const tooltip = d3
    .select(container)
    .append("div")
    .style("position", "absolute")
    .style("pointer-events", "none")
    .style("background", "rgba(10,15,30,0.95)")
    .style("backdrop-filter", "blur(8px)")
    .style("border", "1px solid rgba(255,255,255,0.08)")
    .style("border-radius", "8px")
    .style("padding", "10px 14px")
    .style("font-size", "11px")
    .style("color", "#e2e8f0")
    .style("display", "none")
    .style("z-index", "10")
    .style("min-width", "140px");

  // Edges
  const link = svg
    .append("g")
    .selectAll("line")
    .data(edges)
    .enter()
    .append("line")
    .attr("stroke", "rgba(255,255,255,0.06)")
    .attr("stroke-width", 1.5)
    .attr("marker-end", "url(#arrow)");

  // Edge labels
  const linkLabel = svg
    .append("g")
    .selectAll("text")
    .data(edges)
    .enter()
    .append("text")
    .attr("font-size", "8px")
    .attr("fill", "#334155")
    .attr("text-anchor", "middle")
    .attr("font-family", "monospace")
    .text((d) => (d.shared || []).slice(0, 1).join(""));

  // Node groups
  const node = svg
    .append("g")
    .selectAll("g")
    .data(nodes)
    .enter()
    .append("g")
    .style("cursor", "grab")
    .call(
      d3
        .drag()
        .on("start", (e, d) => {
          if (!e.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on("end", (e, d) => {
          if (!e.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );

  // Outer glow ring
  node
    .append("circle")
    .attr("r", 28)
    .attr("fill", (d) => nodeColor(d.risk_score))
    .attr("fill-opacity", 0.06)
    .attr("stroke", "none");

  // Main circle
  node
    .append("circle")
    .attr("r", 22)
    .attr("fill", (d) => nodeColor(d.risk_score))
    .attr("fill-opacity", 0.1)
    .attr("stroke", (d) => nodeColor(d.risk_score))
    .attr("stroke-width", 2)
    .attr("stroke-opacity", 0.6)
    .style("filter", "url(#glow)");

  // Inner dot
  node
    .append("circle")
    .attr("r", 4)
    .attr("fill", (d) => nodeColor(d.risk_score))
    .attr("fill-opacity", 0.8);

  // Node label
  node
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", -32)
    .attr("font-size", "10px")
    .attr("font-weight", "600")
    .attr("fill", "#94a3b8")
    .attr("font-family", "monospace")
    .text((d) => d.id);

  // Score inside
  node
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", 36)
    .attr("font-size", "9px")
    .attr("font-weight", "700")
    .attr("fill", (d) => nodeColor(d.risk_score))
    .attr("font-family", "monospace")
    .text((d) => (d.risk_score != null ? (d.risk_score * 100).toFixed(0) + "%" : "—"));

  // Hover interactions
  node
    .on("mouseover", function (e, d) {
      // Highlight connected edges
      link
        .attr("stroke", (l) =>
          l.source.id === d.id || l.target.id === d.id
            ? nodeColor(d.risk_score)
            : "rgba(255,255,255,0.03)"
        )
        .attr("stroke-width", (l) =>
          l.source.id === d.id || l.target.id === d.id ? 2.5 : 1
        )
        .attr("stroke-opacity", (l) =>
          l.source.id === d.id || l.target.id === d.id ? 0.6 : 0.3
        );

      // Fade non-connected nodes
      node.attr("opacity", (n) => {
        if (n.id === d.id) return 1;
        const connected = edges.some(
          (ed) =>
            (ed.source.id === d.id && ed.target.id === n.id) ||
            (ed.target.id === d.id && ed.source.id === n.id)
        );
        return connected ? 1 : 0.25;
      });

      // Show tooltip
      const risk = d.risk_score != null ? (d.risk_score * 100).toFixed(0) + "%" : "N/A";
      const camp = d.campaign_id || "None";
      tooltip
        .style("display", "block")
        .style("left", (e.offsetX + 16) + "px")
        .style("top", (e.offsetY - 10) + "px")
        .html(
          `<div style="font-weight:700;font-size:12px;margin-bottom:4px;color:${nodeColor(d.risk_score)}">${d.id}</div>` +
          `<div style="color:#64748b">Risk: <span style="color:#e2e8f0;font-weight:600">${risk}</span></div>` +
          `<div style="color:#64748b">Campaign: <span style="color:#e2e8f0">${camp}</span></div>` +
          (d.timestamp ? `<div style="color:#64748b;font-size:10px;margin-top:2px">${d.timestamp.split("T")[0]}</div>` : "")
        );
    })
    .on("mouseout", function () {
      link
        .attr("stroke", "rgba(255,255,255,0.06)")
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 1);
      node.attr("opacity", 1);
      tooltip.style("display", "none");
    });

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2 - 8);

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

function nodeColor(score) {
  if (score == null) return "#64748b";
  if (score >= 0.8) return "#ef4444";
  if (score >= 0.7) return "#f59e0b";
  return "#3b82f6";
}
