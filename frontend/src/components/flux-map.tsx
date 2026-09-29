"use client";

import { useEffect, useRef, useCallback } from "react";

/* ─── Node positions (x, y, label) ───────────────────────── */
const NODES: Record<string, [number, number, string]> = {
  glc: [70, 165, "Glucose"],
  gly: [220, 165, "Glycolysis"],
  pyr: [370, 165, "Pyruvate"],
  acc: [520, 80, "Acetyl-CoA"],
  tca: [670, 80, "TCA cycle"],
  oxp: [815, 80, "Oxidative phos."],
  ferm: [520, 250, "Fermentation"],
  fout: [700, 250, "Acetate · formate"],
  ppp: [220, 265, "Pentose phosphate"],
  pre: [370, 275, "Precursors"],
  bio: [815, 165, "Biomass"],
};

/* Half-width of each node box */
const hw = (k: string) => (NODES[k][2].length * 6.4 + 26) / 2;

/* Default edge flux values [from, to, aerobicFlux, anaerobicFlux] */
const DEFAULT_EDGES: [string, string, number, number][] = [
  ["glc", "gly", 10, 18],
  ["gly", "pyr", 19, 34],
  ["pyr", "acc", 16, 3],
  ["acc", "tca", 14, 2],
  ["tca", "oxp", 20, 0.6],
  ["pyr", "ferm", 1, 28],
  ["ferm", "fout", 1, 28],
  ["glc", "ppp", 3, 2.2],
  ["ppp", "pre", 2.6, 1.8],
  ["tca", "bio", 4, 0.8],
];

/* ─── Pathway mapping for node highlighting ──────────────── */
const PATHWAY_NODES: Record<string, string[]> = {
  "Glycolysis": ["glc", "gly", "pyr"],
  "TCA Cycle": ["acc", "tca"],
  "Oxidative Phosphorylation": ["oxp", "bio"],
  "Pentose Phosphate": ["glc", "ppp", "pre"],
  "Fermentation": ["pyr", "ferm", "fout"],
};

interface FluxMapProps {
  /** Oxygen level to select default flux values */
  oxygenLevel?: "aerobic" | "anaerobic" | "microaerobic";
  /** Growth rate to display */
  growthRate?: number | null;
  /** Condition label string */
  conditionLabel?: string;
  /** Optional real flux distribution from backend */
  fluxDistribution?: Record<string, number> | null;
  /** Active pathway names for highlighting */
  activePathways?: string[];
  /** Whether to show in compact mode (fewer labels) */
  compact?: boolean;
  /** Callback when a pathway node is clicked */
  onPathwayClick?: (pathway: string) => void;
  /** Highlighted pathway (dims all others) */
  highlightedPathway?: string | null;
}

export function FluxMap({
  oxygenLevel = "aerobic",
  growthRate,
  conditionLabel,
  compact = false,
  activePathways,
  highlightedPathway,
}: FluxMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dotsRef = useRef<{ el: SVGCircleElement; p: number; len: number; path: SVGPathElement }[]>([]);
  const animRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const isAnaerobic = oxygenLevel === "anaerobic";

  /* Build edge data with flux values */
  const edges = DEFAULT_EDGES.map(([a, b, fa, fn]) => {
    const flux = isAnaerobic ? fn : fa;
    return { a, b, flux: flux, fa, fn };
  });

  /* Get highlighted node set */
  const highlightedNodes = highlightedPathway
    ? new Set(PATHWAY_NODES[highlightedPathway] || [])
    : null;

  /* Compute path d-string for a curved edge */
  const getPathD = (a: string, b: string) => {
    const A = NODES[a];
    const B = NODES[b];
    const x1 = A[0] + hw(a);
    const y1 = A[1];
    const x2 = B[0] - hw(b);
    const y2 = B[1];
    const dx = (x2 - x1) * 0.5;
    return `M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`;
  };

  /* Animate dots along paths */
  const animate = useCallback((time: number) => {
    if (!lastTimeRef.current) lastTimeRef.current = time;
    const dt = Math.min(0.05, (time - lastTimeRef.current) / 1000);
    lastTimeRef.current = time;

    dotsRef.current.forEach((dot) => {
      const speed = 0.12;
      dot.p = (dot.p + dt * speed) % 1;
      const pt = dot.path.getPointAtLength(dot.p * dot.len);
      dot.el.setAttribute("cx", pt.x.toFixed(1));
      dot.el.setAttribute("cy", pt.y.toFixed(1));
    });

    animRef.current = requestAnimationFrame(animate);
  }, []);

  /* Setup dots on mount */
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const dotGroup = svg.querySelector(".dot-group");
    if (!dotGroup) return;

    // Clear old dots
    dotsRef.current.forEach((d) => d.el.remove());
    dotsRef.current = [];

    // Create dots for each edge
    const paths = svg.querySelectorAll<SVGPathElement>(".edge-path");
    paths.forEach((path, i) => {
      const edge = edges[i];
      if (!edge) return;
      const flux = edge.flux;
      const numDots = flux < 0.05 ? 0 : Math.min(16, Math.max(1, Math.round(flux * 0.55)));
      const len = path.getTotalLength();

      for (let j = 0; j < numDots; j++) {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("r", "2.6");
        circle.setAttribute("class", "flux-dot");
        circle.setAttribute("fill", "#7dffef");
        circle.setAttribute("opacity", "0.85");
        dotGroup.appendChild(circle);
        dotsRef.current.push({
          el: circle,
          p: (j + Math.random() * 0.5) / numDots,
          len,
          path,
        });
      }
    });

    // Start animation
    lastTimeRef.current = 0;
    animRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animRef.current);
      dotsRef.current.forEach((d) => d.el.remove());
      dotsRef.current = [];
    };
  }, [oxygenLevel, animate, edges]);

  return (
    <div className="rounded-xl bg-[#01070c] border border-white/[0.08] overflow-hidden">
      {/* Header */}
      {(conditionLabel || growthRate != null) && (
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 border-b border-white/[0.06]">
          <span className="text-xs text-[#5c8494] font-mono-readout">
            {conditionLabel || "metabolic flux"}
          </span>
          {growthRate != null && (
            <span className="text-xs text-[#5c8494] font-mono-readout">
              growth <span className="text-lg font-semibold text-[#3ef2ff] glow-text">{growthRate}</span> h⁻¹
            </span>
          )}
        </div>
      )}

      {/* SVG Flux Map */}
      <div className="px-2 py-3">
        <svg
          ref={svgRef}
          viewBox="0 0 900 330"
          role="img"
          aria-label="Schematic metabolic flux map"
          className="w-full h-auto"
        >
          {/* Edges */}
          <g>
            {edges.map((edge, i) => {
              const strokeWidth = (0.8 + edge.flux * 0.3).toFixed(2);
              const opacity = (0.22 + 0.6 * Math.min(1, edge.flux / 18)).toFixed(2);
              const dimmed = highlightedNodes && (!highlightedNodes.has(edge.a) || !highlightedNodes.has(edge.b));
              return (
                <path
                  key={i}
                  className="edge-path"
                  d={getPathD(edge.a, edge.b)}
                  fill="none"
                  stroke="#3ef2ff"
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  opacity={dimmed ? 0.08 : opacity}
                  style={{ transition: "opacity 0.3s" }}
                />
              );
            })}
          </g>

          {/* Dot container */}
          <g className="dot-group" />

          {/* Flux labels */}
          {!compact && (
            <g>
              {edges.map((edge, i) => {
                if (edge.flux < 0.05) return null;
                const A = NODES[edge.a];
                const B = NODES[edge.b];
                const mx = (A[0] + hw(edge.a) + B[0] - hw(edge.b)) / 2;
                const my = (A[1] + B[1]) / 2 - 10;
                return (
                  <text
                    key={i}
                    x={mx}
                    y={my}
                    textAnchor="middle"
                    className="text-[10px] font-mono-readout"
                    fill="#5c8494"
                  >
                    {edge.flux.toFixed(1)}
                  </text>
                );
              })}
            </g>
          )}

          {/* Nodes */}
          <g>
            {Object.entries(NODES).map(([key, [x, y, label]]) => {
              const w = hw(key) * 2;
              const dimmed = highlightedNodes && !highlightedNodes.has(key);
              return (
                <g key={key} style={{ transition: "opacity 0.3s", opacity: dimmed ? 0.15 : 1 }}>
                  <rect
                    x={x - w / 2}
                    y={y - 15}
                    width={w}
                    height={30}
                    rx={4}
                    fill="#031722"
                    stroke="rgba(62, 242, 255, 0.55)"
                    strokeWidth={1}
                  />
                  <text
                    x={x}
                    y={y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="text-[12px] font-mono-readout"
                    fill="#7dffef"
                  >
                    {label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Pathway legend */}
      {activePathways && activePathways.length > 0 && (
        <div className="px-4 pb-3 flex flex-wrap gap-1.5">
          {activePathways.slice(0, compact ? 6 : undefined).map((p) => (
            <span
              key={p}
              className={`px-2.5 py-0.5 text-[10px] rounded-full border cursor-default transition-all ${
                highlightedPathway === p
                  ? "bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40"
                  : "bg-white/[0.03] text-[#5c8494] border-white/[0.08] hover:text-[#8cc3d4]"
              }`}
            >
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default FluxMap;
