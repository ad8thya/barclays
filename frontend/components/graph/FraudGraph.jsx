"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";

const NODE_CONFIG = {
  incident: { radius: 10, shape: "circle", defaultColor: "#3b82f6" },
  domain: { radius: 9, shape: "diamond", defaultColor: "#a855f7" },
  ip: { radius: 8, shape: "square", defaultColor: "#06b6d4" },
};

const EDGE_COLORS = {
  uses_domain: "#a855f7",
  uses_ip: "#06b6d4",
  shared_signal: "#f59e0b",
};

function riskColor(score) {
  if (score >= 0.8) return "#ef4444";
  if (score >= 0.5) return "#f59e0b";
  return "#3b82f6";
}

export default function FraudGraph({ graphData }) {
  const svgRef = useRef(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    if (!graphData?.nodes?.length) return;

    const width = svgRef.current.clientWidth || 600;
    const height = svgRef.current.clientHeight || 480;

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    const nodes = graphData.nodes.map((n) => ({ ...n }));
    const edges = graphData.edges.map((e) => ({ ...e }));

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(20));

    // Edges
    const link = g.append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d) => EDGE_COLORS[d.relation] || "#334155")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.5);

    // Nodes
    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag()
        .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on("end", (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    node.each(function (d) {
      const el = d3.select(this);
      const cfg = NODE_CONFIG[d.type] || NODE_CONFIG.incident;
      const color = d.type === "incident" ? riskColor(d.risk_score || 0) : cfg.defaultColor;

      if (cfg.shape === "diamond") {
        const s = cfg.radius;
        el.append("path")
          .attr("d", `M0,${-s} L${s},0 L0,${s} L${-s},0 Z`)
          .attr("fill", color)
          .attr("fill-opacity", 0.8)
          .attr("stroke", color)
          .attr("stroke-width", 1);
      } else if (cfg.shape === "square") {
        const s = cfg.radius * 0.8;
        el.append("rect")
          .attr("x", -s).attr("y", -s)
          .attr("width", s * 2).attr("height", s * 2)
          .attr("rx", 2)
          .attr("fill", color)
          .attr("fill-opacity", 0.8)
          .attr("stroke", color)
          .attr("stroke-width", 1);
      } else {
        el.append("circle")
          .attr("r", cfg.radius)
          .attr("fill", color)
          .attr("fill-opacity", 0.8)
          .attr("stroke", color)
          .attr("stroke-width", 1);
      }

      // Label
      el.append("text")
        .text(d.label || d.id)
        .attr("dy", cfg.radius + 14)
        .attr("text-anchor", "middle")
        .attr("fill", "#64748b")
        .attr("font-size", "9px")
        .attr("font-family", "monospace");
    });

    // Tooltip on hover
    const tooltip = d3.select(tooltipRef.current);

    node
      .on("mouseenter", (e, d) => {
        const cfg = NODE_CONFIG[d.type] || NODE_CONFIG.incident;
        tooltip
          .style("display", "block")
          .style("left", `${e.offsetX + 12}px`)
          .style("top", `${e.offsetY - 10}px`)
          .html(`
            <div style="font-size:11px;font-weight:500;color:#e2e8f0;margin-bottom:4px">${d.label || d.id}</div>
            <div style="font-size:10px;color:#64748b">Type: ${d.type}</div>
            ${d.risk_score ? `<div style="font-size:10px;color:#64748b">Risk: ${Math.round(d.risk_score * 100)}%</div>` : ""}
            ${d.campaign_id ? `<div style="font-size:10px;color:#64748b">Campaign: ${d.campaign_id}</div>` : ""}
          `);

        // Highlight connected edges
        link.attr("stroke-opacity", (l) =>
          l.source.id === d.id || l.target.id === d.id ? 1 : 0.1
        );
      })
      .on("mouseleave", () => {
        tooltip.style("display", "none");
        link.attr("stroke-opacity", 0.5);
      });

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);
      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [graphData]);

  const isEmpty = !graphData?.nodes?.length;

  return (
    <div className="glass-card relative overflow-hidden" style={{ minHeight: 480 }}>
      {isEmpty && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <svg width="48" height="48" viewBox="0 0 48 48" className="mx-auto mb-4 opacity-20">
              {[...Array(6)].map((_, i) => (
                <circle key={i} cx={8 + (i % 3) * 16} cy={8 + Math.floor(i / 3) * 16} r="2" fill="#334155" />
              ))}
            </svg>
            <p className="text-sm text-slate-600">Run analysis to map campaign infrastructure</p>
          </div>
        </div>
      )}
      <svg
        ref={svgRef}
        className="w-full"
        style={{ height: 480 }}
      />
      <div
        ref={tooltipRef}
        className="absolute pointer-events-none hidden z-50 glass-card px-3 py-2 rounded-lg"
        style={{ maxWidth: 200, display: "none" }}
      />

      {/* Legend */}
      {!isEmpty && (
        <div className="absolute bottom-4 left-4 glass-card px-3 py-2 text-[10px] space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#3b82f6]" />
            <span className="text-slate-500">Incident</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rotate-45 bg-[#a855f7]" />
            <span className="text-slate-500">Domain</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm bg-[#06b6d4]" />
            <span className="text-slate-500">IP Address</span>
          </div>
          <div className="border-t border-white/[0.04] pt-1.5 mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 bg-[#a855f7]" />
              <span className="text-slate-600">uses_domain</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 bg-[#06b6d4]" />
              <span className="text-slate-600">uses_ip</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 bg-[#f59e0b]" />
              <span className="text-slate-600">shared_signal</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
