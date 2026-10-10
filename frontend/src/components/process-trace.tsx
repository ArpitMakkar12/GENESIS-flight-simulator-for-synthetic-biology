"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Settings, Check, TriangleAlert } from "lucide-react";
import { growthStateLabel, percentOfReference, GROWTH_UNIT } from "@/lib/sim-format";

interface ProcessTraceProps {
  /** Total compute time in milliseconds */
  computeTimeMs?: number | null;
  /** Model version info */
  modelVersions?: Record<string, string> | null;
  /** Environment conditions */
  temperature?: number;
  ph?: number;
  oxygenLevel?: string;
  carbonSource?: string;
  nitrogenSource?: string;
  /** Growth state from the backend: optimal / slowed / stressed / not-viable */
  growthState?: string;
  /** Growth rate result */
  growthRate?: number | null;
  /** How many pathways carry any flux */
  pathwayCount?: number;
  /** Expression prediction count */
  expressionCount?: number;
}

export function ProcessTrace({
  computeTimeMs,
  modelVersions,
  temperature = 37,
  ph = 7,
  oxygenLevel = "aerobic",
  carbonSource = "glucose",
  nitrogenSource = "ammonium",
  growthState = "optimal",
  growthRate,
  pathwayCount = 0,
  expressionCount = 0,
}: ProcessTraceProps) {
  const [expanded, setExpanded] = useState(false);

  const solver = modelVersions?.solver || "glpk";
  const model = modelVersions?.metabolic_model || "iML1515";

  /* Build honest process steps from actual data */
  const steps = [
    {
      label: `Loaded ${model}`,
      detail: "2,712 reactions · 1,877 metabolites",
      status: "done" as const,
    },
    {
      label: `Applied regulatory constraints`,
      detail: `${oxygenLevel}, ${temperature}°C, pH ${ph}`,
      status: "done" as const,
    },
    {
      label: `Set exchange bounds`,
      detail: `${carbonSource}, ${nitrogenSource}`,
      status: "done" as const,
    },
    {
      label: `Solved FBA — objective: biomass`,
      detail: `solver: ${solver}${computeTimeMs ? ` · ${computeTimeMs.toLocaleString()} ms` : ""}`,
      status: "done" as const,
    },
    {
      // Same wording as the badge above: "Much slower", not the raw "stressed"
      label: `Result: ${growthStateLabel(growthState)}`,
      detail:
        growthRate != null && growthRate > 0
          ? `μ = ${growthRate.toFixed(3)} ${GROWTH_UNIT} · ${percentOfReference(growthRate)}% of reference growth`
          : "no growth: the model found no feasible solution",
      status: growthState === "optimal" || growthState === "slowed" ? ("done" as const) : ("warn" as const),
    },
  ];

  /* Optional additional info steps */
  if (expressionCount > 0) {
    steps.push({
      label: `Expression predictions`,
      detail: `${expressionCount.toLocaleString()} genes evaluated`,
      status: "done" as const,
    });
  }
  if (pathwayCount > 0) {
    steps.push({
      label: `Pathway analysis`,
      detail: `${pathwayCount} pathways carry flux`,
      status: "done" as const,
    });
  }

  const summaryText = `Computed${computeTimeMs ? ` in ${computeTimeMs.toLocaleString()} ms` : ""} · ${solver} · ${model}`;

  return (
    <Card className="p-0 overflow-hidden">
      {/* Collapsed summary / toggle header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-white/[0.02] transition-colors group"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-[#3ef2ff]/[0.08] text-[#3ef2ff] text-xs flex-shrink-0">
            <Settings className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-[#d9f7ff]">Simulation Process</h3>
            <p className="text-[11px] text-[#5c8494] font-mono-readout truncate">
              {summaryText}
            </p>
          </div>
        </div>
        <span className={`text-[#5c8494] text-xs transition-transform ${expanded ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>

      {/* Expanded step list */}
      {expanded && (
        <div className="border-t border-white/[0.06] px-5 py-4 space-y-0">
          {steps.map((step, i) => (
            <div
              key={i}
              className="flex items-start gap-3 py-2"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              {/* Status icon */}
              <div className="flex-shrink-0 mt-0.5">
                {step.status === "done" ? (
                  <Check className="h-3.5 w-3.5 text-[#3ef2ff]" strokeWidth={2.5} aria-hidden="true" />
                ) : (
                  <TriangleAlert className="h-3.5 w-3.5 text-[#ffcf66]" strokeWidth={2} aria-hidden="true" />
                )}
              </div>

              {/* Step content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm text-[#d9f7ff]">{step.label}</span>
                </div>
                <span className="text-[11px] text-[#5c8494] font-mono-readout">
                  {step.detail}
                </span>
              </div>

              {/* Connector line (not on last item) */}
              {i < steps.length - 1 && (
                <div className="hidden" /> /* vertical line handled by spacing */
              )}
            </div>
          ))}

          {/* Footer */}
          <div className="pt-3 mt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-[#5c8494]">
            <span className="font-mono-readout">
              Solver: {solver} · Model: {model}
            </span>
            {computeTimeMs && (
              <span className="font-mono-readout">
                Total: {computeTimeMs.toLocaleString()} ms
              </span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

export default ProcessTrace;