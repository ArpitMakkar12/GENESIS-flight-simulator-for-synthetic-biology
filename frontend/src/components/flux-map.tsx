"use client";

import { useEffect, useRef, useCallback, useMemo } from "react";

/*
 * Metabolic flux map
 * ------------------
 * Every arrow is drawn from the real FBA solution of the simulation
 * (fluxDistribution = { reaction_id: flux in mmol/gDW/h }). Nothing is hardcoded.
 *
 * - The carbon source box is placed where that nutrient really enters
 *   metabolism (sugars → glycolysis, xylose/arabinose → pentose phosphate,
 *   acetate → acetyl-CoA, succinate → TCA cycle).
 * - Arrows can run backwards. Example: on acetate, glycolysis runs in reverse
 *   (gluconeogenesis) to make sugars, so the dots move right-to-left and the
 *   number is shown with "←".
 */

type NodeDef = [number, number, string]; // x, y, label

/* ─── Fixed boxes ───────────────────────────────────────── */
const BASE_NODES: Record<string, NodeDef> = {
  gly: [220, 165, "Glycolysis"],
  pyr: [370, 165, "Pyruvate"],
  acc: [520, 80, "Acetyl-CoA"],
  tca: [670, 80, "TCA cycle"],
  oxp: [815, 80, "Oxidative phos."],
  ferm: [520, 250, "Fermentation"],
  fout: [700, 250, "Secreted products"],
  ppp: [220, 265, "Pentose phosphate"],
  pre: [370, 275, "Precursors"],
  bio: [815, 165, "Biomass"],
};

/* ─── Where each carbon source enters, and its exchange reaction ───
 * Same exchange IDs as the backend (simulation_runner.py).
 * A new carbon source only needs one line here.
 */
type Entry = "gly" | "ppp" | "acc" | "tca";

const CARBON_SOURCES: Record<string, { exchange: string; entry: Entry }> = {
  glucose: { exchange: "EX_glc__D_e", entry: "gly" },
  fructose: { exchange: "EX_fru_e", entry: "gly" },
  galactose: { exchange: "EX_gal_e", entry: "gly" },
  lactose: { exchange: "EX_lcts_e", entry: "gly" },
  glycerol: { exchange: "EX_glyc_e", entry: "gly" },
  xylose: { exchange: "EX_xyl__D_e", entry: "ppp" },
  arabinose: { exchange: "EX_arab__L_e", entry: "ppp" },
  acetate: { exchange: "EX_ac_e", entry: "acc" },
  succinate: { exchange: "EX_succ_e", entry: "tca" },
};

/* Position of the carbon source box for each entry point */
const SOURCE_POS: Record<Entry, [number, number]> = {
  gly: [70, 165], // left of Glycolysis
  ppp: [70, 265], // left of Pentose phosphate
  acc: [370, 35], // above Pyruvate, feeding Acetyl-CoA
  tca: [670, 25], // straight above the TCA cycle
};

/* ─── What each arrow measures ─────────────────────────────
 * f(id) returns the flux of one reaction (0 if the backend didn't store it,
 * because it only keeps |flux| > 1e-6).
 * Positive result = arrow direction, negative = running backwards.
 */
type Flux = (id: string) => number;
const pos = (v: number) => Math.max(0, v);

/* ─── Pentose phosphate bookkeeping (counted in carbon atoms) ──────
 * The pentose phosphate pathway has several equally good routes back to
 * glycolysis (TKT2, TALA, or the PFK_3/FBA3 bypass, or Entner–Doudoroff),
 * and the solver may pick any of them. Counting carbon atoms makes the
 * arrows come out the same whichever route the solver chose.
 *
 * Carbon going from glycolysis into PPP (C-mmol/gDW/h):
 *   G6PDH2r brings in glucose-6-P            +6 C
 *   TKT1 sends out glyceraldehyde-3-P        −3 C
 *   TKT2 sends out fructose-6-P + G3P        −9 C
 *   TALA takes in G3P, sends out F6P         −3 C (net)
 *   FBA3 sends out DHAP (bypass)             −3 C
 *   EDA sends out G3P + pyruvate (E–D path)  −6 C
 */
const pppCarbonFromGlycolysis = (f: Flux) =>
  6 * f("G6PDH2r") - 3 * f("TKT1") - 9 * f("TKT2") - 3 * f("TALA") - 3 * f("FBA3") - 6 * f("EDA");

/* Carbon left in PPP for building blocks = what came in − what left as CO2.
 * In: from glycolysis (above) + xylose/arabinose entering directly (5 C each).
 * Out as CO2: GND (1 C each). What remains feeds nucleotides & aromatic amino acids.
 */
const pppCarbonForPrecursors = (f: Flux) =>
  pppCarbonFromGlycolysis(f) + 5 * (pos(f("XYLK")) + pos(f("RBK_L1"))) - pos(f("GND"));

const EDGE_DEFS: { a: string; b: string; what: string; value: (f: Flux, growth: number) => number }[] = [
  {
    a: "gly", b: "pyr",
    what: "Lower glycolysis, GAPD (← = gluconeogenesis)",
    value: (f) => f("GAPD"),
  },
  {
    a: "gly", b: "ppp",
    what: "Net carbon glycolysis ↔ pentose phosphate, in sugar (6-carbon) units; ↑ = returning to glycolysis",
    value: (f) => pppCarbonFromGlycolysis(f) / 6,
  },
  {
    a: "ppp", b: "pre",
    what: "Carbon kept for nucleotides & aromatic amino acids, in 5-carbon units",
    value: (f) => pos(pppCarbonForPrecursors(f)) / 5,
  },
  {
    a: "pyr", b: "acc",
    what: "Pyruvate dehydrogenase (PDH)",
    value: (f) => pos(f("PDH")),
  },
  {
    a: "pyr", b: "tca",
    what: "Anaplerosis PEP/pyruvate ↔ TCA (PPC − PPCK − ME1 − ME2; ← = gluconeogenesis)",
    value: (f) => f("PPC") - f("PPCK") - f("ME1") - f("ME2"),
  },
  {
    a: "acc", b: "tca",
    what: "Citrate synthase (CS)",
    value: (f) => pos(f("CS")),
  },
  {
    a: "tca", b: "oxp",
    what: "Oxygen uptake (EX_o2_e)",
    value: (f) => pos(-f("EX_o2_e")),
  },
  {
    a: "pyr", b: "ferm",
    what: "Pyruvate formate-lyase + lactate dehydrogenase (PFL, LDH_D)",
    value: (f) => pos(f("PFL")) + pos(-f("LDH_D")),
  },
  {
    a: "ferm", b: "fout",
    what: "Secreted acetate + formate + ethanol + lactate + succinate",
    value: (f) =>
      pos(f("EX_ac_e")) + pos(f("EX_for_e")) + pos(f("EX_etoh_e")) +
      pos(f("EX_lac__D_e")) + pos(f("EX_succ_e")),
  },
  {
    a: "tca", b: "bio",
    what: "Growth rate (h⁻¹)",
    value: (_f, growth) => growth,
  },
];

/* ─── Pathway mapping for node highlighting ──────────────── */
const PATHWAY_NODES: Record<string, string[]> = {
  "Glycolysis": ["src", "gly", "pyr"],
  "TCA Cycle": ["acc", "tca"],
  "Oxidative Phosphorylation": ["oxp", "bio"],
  "Pentose Phosphate": ["src", "ppp", "pre"],
  "Fermentation": ["pyr", "ferm", "fout"],
};

/* Half-width of a node box, based on its label length */
const hw = (label: string) => (label.length * 6.4 + 26) / 2;
const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

interface FluxMapProps {
  /** Carbon source name: labels the first box and decides where it enters */
  carbonSource?: string;
  /** Growth rate to display */
  growthRate?: number | null;
  /** Condition label string */
  conditionLabel?: string;
  /** Real flux distribution from the backend: { reaction_id: flux } */
  fluxDistribution?: Record<string, number> | null;
  /** Active pathway names for highlighting */
  activePathways?: string[];
  /** Whether to show in compact mode (fewer labels) */
  compact?: boolean;
  /** Highlighted pathway (dims all others) */
  highlightedPathway?: string | null;
}

export function FluxMap({
  carbonSource,
  growthRate,
  conditionLabel,
  fluxDistribution,
  compact = false,
  activePathways,
  highlightedPathway,
}: FluxMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dotsRef = useRef<
    { el: SVGCircleElement; p: number; len: number; dir: number; path: SVGPathElement }[]
  >([]);
  const animRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const hasFlux = !!fluxDistribution && Object.keys(fluxDistribution).length > 0;

  /* Carbon source info (unknown sources default to entering glycolysis) */
  const source = carbonSource ? CARBON_SOURCES[carbonSource.toLowerCase()] : undefined;
  const entry: Entry = source?.entry ?? "gly";

  /* Boxes: the fixed ones plus the carbon source at its real entry point */
  const nodes = useMemo<Record<string, NodeDef>>(() => {
    const [x, y] = SOURCE_POS[entry];
    return {
      src: [x, y, capitalize(carbonSource || "Carbon source")],
      ...BASE_NODES,
    };
  }, [carbonSource, entry]);

  /* Arrow values from the real fluxes */
  const edges = useMemo(() => {
    const fd = fluxDistribution ?? {};
    const f: Flux = (id) => fd[id] ?? 0;
    const uptake = source ? pos(-f(source.exchange)) : 0;

    const list = [
      {
        a: "src", b: entry,
        what: source ? `Uptake of ${carbonSource} (${source.exchange})` : "Carbon uptake",
        flux: uptake,
      },
      ...EDGE_DEFS.map(({ a, b, what, value }) => ({ a, b, what, flux: value(f, growthRate ?? 0) })),
    ];
    // Round away solver noise like -1e-7 so it doesn't show as "← 0.0"
    return list.map((e) => ({ ...e, flux: Math.abs(e.flux) < 1e-4 ? 0 : e.flux }));
  }, [fluxDistribution, growthRate, source, entry, carbonSource]);

  const uptake = edges[0].flux;

  /* Get highlighted node set */
  const highlightedNodes = highlightedPathway
    ? new Set(PATHWAY_NODES[highlightedPathway] || [])
    : null;

  /* Is this arrow drawn straight down (same x position)? */
  const isVertical = (a: string, b: string) => Math.abs(nodes[a][0] - nodes[b][0]) < 5;

  /* Path for an arrow: curved left-to-right, or straight down when stacked */
  const getPathD = (a: string, b: string) => {
    const A = nodes[a];
    const B = nodes[b];
    if (isVertical(a, b)) {
      return `M${A[0]} ${A[1] + 15} L${B[0]} ${B[1] - 15}`;
    }
    const x1 = A[0] + hw(A[2]);
    const y1 = A[1];
    const x2 = B[0] - hw(B[2]);
    const y2 = B[1];
    const dx = (x2 - x1) * 0.5;
    return `M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`;
  };

  /* Animate dots along paths (backwards for reversed arrows) */
  const animate = useCallback((time: number) => {
    if (!lastTimeRef.current) lastTimeRef.current = time;
    const dt = Math.min(0.05, (time - lastTimeRef.current) / 1000);
    lastTimeRef.current = time;

    dotsRef.current.forEach((dot) => {
      const speed = 0.12;
      dot.p = (dot.p + dot.dir * dt * speed + 1) % 1;
      const pt = dot.path.getPointAtLength(dot.p * dot.len);
      dot.el.setAttribute("cx", pt.x.toFixed(1));
      dot.el.setAttribute("cy", pt.y.toFixed(1));
    });

    animRef.current = requestAnimationFrame(animate);
  }, []);

  /* Set up dots whenever the fluxes change */
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const dotGroup = svg.querySelector(".dot-group");
    if (!dotGroup) return;

    // Clear old dots
    dotsRef.current.forEach((d) => d.el.remove());
    dotsRef.current = [];

    // More flux = more dots on that arrow
    const paths = svg.querySelectorAll<SVGPathElement>(".edge-path");
    paths.forEach((path, i) => {
      const edge = edges[i];
      if (!edge) return;
      const size = Math.abs(edge.flux);
      const numDots = size < 0.05 ? 0 : Math.min(16, Math.max(1, Math.round(size * 0.55)));
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
          dir: edge.flux < 0 ? -1 : 1,
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
  }, [edges, animate, nodes]);

  return (
    <div className="rounded-xl bg-[#01070c] border border-white/[0.08] overflow-hidden">
      {/* Header */}
      {(conditionLabel || growthRate != null) && (
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 border-b border-white/[0.06]">
          <span className="text-xs text-[#5c8494] font-mono-readout">
            {conditionLabel || "metabolic flux"}
            {hasFlux && source && (
              <> · uptake <span className="text-[#7dffef]">{uptake.toFixed(1)}</span> mmol/gDW/h</>
            )}
          </span>
          {growthRate != null && (
            <span className="text-xs text-[#5c8494] font-mono-readout">
              growth <span className="text-lg font-semibold text-[#3ef2ff] glow-text">{growthRate}</span> h⁻¹
            </span>
          )}
        </div>
      )}

      {!hasFlux && (
        <p className="px-4 pt-3 text-xs text-amber-300/80">
          No flux data was saved for this run, so the arrows are empty.
        </p>
      )}

      {/* SVG Flux Map */}
      <div className="px-2 py-3">
        <svg
          ref={svgRef}
          viewBox="0 0 900 330"
          role="img"
          aria-label="Metabolic flux map from the FBA solution"
          className="w-full h-auto"
        >
          {/* Edges */}
          <g>
            {edges.map((edge, i) => {
              const size = Math.abs(edge.flux);
              const strokeWidth = (0.8 + Math.min(size, 40) * 0.3).toFixed(2);
              const opacity = (0.22 + 0.6 * Math.min(1, size / 18)).toFixed(2);
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
                >
                  <title>{`${edge.what}: ${edge.flux.toFixed(2)}`}</title>
                </path>
              );
            })}
          </g>

          {/* Dot container */}
          <g className="dot-group" />

          {/* Flux labels (0.0 is shown too, so a switched-off route is visible) */}
          {!compact && (
            <g>
              {edges.map((edge, i) => {
                const A = nodes[edge.a];
                const B = nodes[edge.b];
                const size = Math.abs(edge.flux);
                const num = edge.b === "bio" ? size.toFixed(2) : size.toFixed(1);
                const vertical = isVertical(edge.a, edge.b);

                // Direction mark: ← for a reversed arrow, ↓/↑ on the vertical one
                let label = num;
                if (vertical) label = `${edge.flux < 0 ? "↑" : "↓"} ${num}`;
                else if (edge.flux < 0) label = `← ${num}`;

                const x = vertical ? A[0] + 8 : (A[0] + hw(A[2]) + B[0] - hw(B[2])) / 2;
                const y = vertical ? (A[1] + B[1]) / 2 + 4 : (A[1] + B[1]) / 2 - 10;
                return (
                  <text
                    key={i}
                    x={x}
                    y={y}
                    textAnchor={vertical ? "start" : "middle"}
                    className="text-[10px] font-mono-readout"
                    fill="#5c8494"
                    stroke="#01070c"
                    strokeWidth={3}
                    paintOrder="stroke"
                  >
                    <title>{edge.what}</title>
                    {label}
                  </text>
                );
              })}
            </g>
          )}

          {/* Nodes */}
          <g>
            {Object.entries(nodes).map(([key, [x, y, label]]) => {
              const w = hw(label) * 2;
              const dimmed = highlightedNodes && !highlightedNodes.has(key);
              const isSource = key === "src";
              return (
                <g key={key} style={{ transition: "opacity 0.3s", opacity: dimmed ? 0.15 : 1 }}>
                  <rect
                    x={x - w / 2}
                    y={y - 15}
                    width={w}
                    height={30}
                    rx={4}
                    fill={isSource ? "#06303a" : "#031722"}
                    stroke={isSource ? "rgba(62, 242, 255, 0.9)" : "rgba(62, 242, 255, 0.55)"}
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