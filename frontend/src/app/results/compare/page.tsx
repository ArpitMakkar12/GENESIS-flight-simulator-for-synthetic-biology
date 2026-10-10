"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, StatusBadge } from "@/components/ui/card";
import { Spinner, ErrorBanner } from "@/components/ui/loading";
import { FluxMap } from "@/components/flux-map";
import {
  runLabel, simTitle, conditionLine, formatGrowth, GROWTH_UNIT,
  growthStateLabel, percentOfReference, REFERENCE_GROWTH_RATE, REFERENCE_CONDITION,
} from "@/lib/sim-format";
import Link from "next/link";

interface SimDetail {
  id: string;
  run_number?: number | null;
  name?: string | null;
  status: string;
  temperature: number;
  ph: number;
  oxygen_level: string;
  carbon_source: string;
  nitrogen_source: string;
  growth_rate: number | null;
  doubling_time: number | null;
  viability_score: number | null;
  compute_time_ms: number | null;
  created_at: string | null;
  completed_at: string | null;
  expression_results: { gene_id: string; relative_expression: number; confidence: number }[] | null;
  fba_results: { active_pathways: string[]; bottlenecks: string[] } | null;
  flux_distribution: Record<string, number> | null;
  model_versions: Record<string, string> | null;
}

/* One colour per compared run: cyan, violet, amber, pink.
 * Checked with a colour-blindness validator on this dark background: every
 * pair stays distinguishable (the old set had two near-identical cyans). */
const SIM_COLORS = ["#0fa0b4", "#9b6ff1", "#b98a10", "#e05a88"];
const SIM_LABELS = ["A", "B", "C", "D"];

/** Small coloured square that ties a label to its run's colour (text stays white). */
function Swatch({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-sm shrink-0" style={{ backgroundColor: color }} aria-hidden="true" />;
}

interface BarRow {
  key: string;
  label: string;      // "Sim A · #60"
  title: string;      // full run title, shown on hover
  color: string;
  value: number | null;
  display: string;    // text printed at the end of the bar
}

/**
 * One metric = one small chart with its own scale.
 * (The old chart put growth ≈ 0.6 and viability = 100 on the same axis, so
 * growth bars were nearly invisible.) Bars are thin, labelled with their value,
 * and an optional reference line marks the baseline condition.
 */
function MetricBars({
  title, subtitle, rows, max, reference,
}: {
  title: string;
  subtitle: string;
  rows: BarRow[];
  max: number;
  reference?: { value: number; label: string };
}) {
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  return (
    <Card className="p-5 bg-[#01070c] border-[#5c8494]/30">
      <h3 className="text-sm font-semibold text-[#eaffff]">{title}</h3>
      <p className="text-xs text-[#5c8494] mb-4">{subtitle}</p>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.key} className="group" title={`${r.title}: ${r.display}`}>
            <div className="flex items-center justify-between gap-2 text-xs mb-1">
              <span className="flex items-center gap-1.5 text-[#8cc3d4] truncate">
                <Swatch color={r.color} /> {r.label}
              </span>
              <span className="font-mono-readout text-[#eaffff] shrink-0">{r.display}</span>
            </div>
            <div className="relative h-3 rounded-sm bg-white/[0.04] group-hover:bg-white/[0.07] transition-colors">
              {r.value != null && r.value > 0 && (
                <div className="absolute inset-y-0 left-0 rounded-r" style={{ width: pct(r.value), backgroundColor: r.color }} />
              )}
              {reference && (
                <div className="absolute -inset-y-1 w-px bg-[#8cc3d4]/70" style={{ left: pct(reference.value) }} aria-hidden="true" />
              )}
            </div>
          </div>
        ))}
      </div>
      {reference && (
        <p className="mt-3 text-[11px] text-[#5c8494] flex items-center gap-1.5">
          <span className="inline-block h-3 w-px bg-[#8cc3d4]/70" aria-hidden="true" /> {reference.label}
        </p>
      )}
    </Card>
  );
}

function exportComparisonMarkdown(sims: SimDetail[]) {
  const date = new Date().toISOString().split("T")[0];
  let md = `# Genesis Simulation Comparison (${date})\n\n`;

  md += `| Metric | ${sims.map((_, i) => `Sim ${SIM_LABELS[i]}`).join(" | ")} |\n`;
  md += `| --- | ${sims.map(() => "---").join(" | ")} |\n`;
  md += `| Run | ${sims.map(s => runLabel(s) || s.id.substring(0, 8)).join(" | ")} |\n`;
  md += `| Name | ${sims.map(s => simTitle(s)).join(" | ")} |\n`;
  md += `| Vs reference | ${sims.map(s => `${growthStateLabel(s.status)}${percentOfReference(s.growth_rate) != null ? ` (${percentOfReference(s.growth_rate)}%)` : ""}`).join(" | ")} |\n`;
  md += `| Condition | ${sims.map(s => `${s.temperature}°C · ${s.oxygen_level} · ${s.carbon_source}`).join(" | ")} |\n`;
  md += `| Growth Rate | ${sims.map(s => s.growth_rate?.toFixed(4) || "N/A").join(" | ")} |\n`;
  md += `| Doubling Time | ${sims.map(s => s.doubling_time?.toFixed(2) || "N/A").join(" | ")} |\n`;
  md += `| Viability | ${sims.map(s => s.viability_score ? (s.viability_score * 100).toFixed(1) + "%" : "N/A").join(" | ")} |\n`;

  md += `\n## Pathway Differences\n\n`;
  
  if (sims.length === 2) {
    const p1 = new Set(sims[0].fba_results?.active_pathways || []);
    const p2 = new Set(sims[1].fba_results?.active_pathways || []);
    
    const only1 = Array.from(p1).filter(p => !p2.has(p));
    const only2 = Array.from(p2).filter(p => !p1.has(p));
    const shared = Array.from(p1).filter(p => p2.has(p));

    md += `### Only in Sim A\n${only1.map(p => `- ${p}`).join("\n") || "None"}\n\n`;
    md += `### Only in Sim B\n${only2.map(p => `- ${p}`).join("\n") || "None"}\n\n`;
    md += `### Shared\n${shared.map(p => `- ${p}`).join("\n") || "None"}\n\n`;
  } else {
    md += `Pathway differences are optimized for comparing 2 simulations.\n\n`;
  }

  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `genesis-comparison-${date}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idsParam = searchParams.get("ids");
  
  const [sims, setSims] = useState<SimDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!idsParam) {
      setError("No simulation IDs provided.");
      setLoading(false);
      return;
    }

    const ids = idsParam.split(",").slice(0, 4);
    if (ids.length < 2) {
      setError("Need at least 2 simulations to compare.");
      setLoading(false);
      return;
    }

    const fetchSims = async () => {
      try {
        setLoading(true);
        const results = await Promise.all(
          ids.map(async (id) => {
            const res = await fetch(`http://localhost:8000/api/v1/results/${id}`);
            if (!res.ok) throw new Error(`Failed to fetch sim ${id}`);
            return res.json() as Promise<SimDetail>;
          })
        );
        setSims(results);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load simulations");
      } finally {
        setLoading(false);
      }
    };

    fetchSims();
  }, [idsParam]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-2xl mx-auto page-enter">
        <ErrorBanner message={error || "Error loading comparison"} />
        <button onClick={() => router.push("/results")} className="mt-4 px-4 py-2 bg-[#5c8494]/20 text-[#8cc3d4] rounded hover:bg-[#5c8494]/30 transition-colors">
          Back to Results
        </button>
      </div>
    );
  }

  if (sims.length === 0) return null;

  // One row per run, reused by the three small charts
  const rowBase = sims.map((sim, i) => ({
    key: sim.id,
    label: `Sim ${SIM_LABELS[i]}${sim.run_number != null ? ` · ${runLabel(sim)}` : ""}`,
    title: simTitle(sim),
    color: SIM_COLORS[i],
  }));
  const growthRows: BarRow[] = sims.map((sim, i) => ({
    ...rowBase[i],
    value: sim.growth_rate,
    display: formatGrowth(sim.growth_rate),
  }));
  const doublingRows: BarRow[] = sims.map((sim, i) => ({
    ...rowBase[i],
    value: sim.doubling_time,
    display: sim.doubling_time != null ? `${sim.doubling_time.toFixed(2)} h` : "no growth",
  }));
  const viabilityRows: BarRow[] = sims.map((sim, i) => ({
    ...rowBase[i],
    value: sim.viability_score != null ? sim.viability_score * 100 : null,
    display: sim.viability_score != null ? `${(sim.viability_score * 100).toFixed(0)}%` : "—",
  }));
  // Scales: start at 0, leave a little room past the biggest bar (and the reference line)
  const growthMax = Math.max(REFERENCE_GROWTH_RATE, ...sims.map((s) => s.growth_rate ?? 0)) * 1.1;
  const doublingMax = Math.max(1, ...sims.map((s) => s.doubling_time ?? 0)) * 1.1;

  return (
    <div className="p-8 max-w-6xl mx-auto text-[#eaffff] page-enter space-y-8">
      <div className="flex items-center justify-between">
        <Link href="/results" className="text-[#8cc3d4] hover:text-[#3ef2ff] transition-colors flex items-center gap-2">
          <span>&larr;</span> Results
        </Link>
        <h1 className="text-xl font-semibold">Comparing {sims.length} simulations</h1>
        <button
          onClick={() => exportComparisonMarkdown(sims)}
          className="px-4 py-2 bg-[#b98bff]/20 text-[#b98bff] rounded hover:bg-[#b98bff]/30 transition-colors border border-[#b98bff]/50"
        >
          Export .md
        </button>
      </div>

      {/* Conditions Strip */}
      <div className={`grid gap-4 ${sims.length === 2 ? "grid-cols-2" : sims.length === 3 ? "grid-cols-3" : "grid-cols-4"}`}>
        {sims.map((sim, i) => (
          <Card key={sim.id} className="p-4 bg-[#01070c] border-[#5c8494]/30 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: SIM_COLORS[i] }}></div>
            <div className="flex justify-between items-start mb-2">
              <span className="flex items-center gap-1.5 font-semibold text-[#eaffff]">
                <Swatch color={SIM_COLORS[i]} />
                Sim {SIM_LABELS[i]}{sim.run_number != null && <span className="font-mono-readout font-normal text-[#5c8494]"> · {runLabel(sim)}</span>}
              </span>
              <StatusBadge status={sim.status} growthRate={sim.growth_rate} />
            </div>
            <div className="text-sm text-[#eaffff] mb-1">{simTitle(sim)}</div>
            {sim.name && <div className="text-xs text-[#5c8494] mb-3">{conditionLine(sim)}</div>}
            <div className={`font-mono-readout text-2xl text-[#eaffff] ${sim.name ? "" : "mt-3"}`}>
              {formatGrowth(sim.growth_rate, false)} <span className="text-sm text-[#5c8494]">{GROWTH_UNIT}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Metrics: one small chart per measure, each on its own scale */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Metrics Comparison</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricBars
            title="Growth rate"
            subtitle={`${GROWTH_UNIT} · higher is faster`}
            rows={growthRows}
            max={growthMax}
            reference={{ value: REFERENCE_GROWTH_RATE, label: `Reference ${REFERENCE_GROWTH_RATE} ${GROWTH_UNIT} (${REFERENCE_CONDITION})` }}
          />
          <MetricBars title="Doubling time" subtitle="hours · lower is faster" rows={doublingRows} max={doublingMax} />
          <MetricBars title="Viability" subtitle="% of cells surviving" rows={viabilityRows} max={100} />
        </div>
      </div>

      {/* Flux Maps */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Flux Distributions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sims.map((sim, i) => (
            <div key={sim.id} className="p-4 bg-white/[0.04] border border-white/[0.07] rounded-2xl" style={{ borderTopWidth: 4, borderTopColor: SIM_COLORS[i] }}>
              <div className="mb-4 flex items-center gap-1.5">
                <Swatch color={SIM_COLORS[i]} />
                <span className="font-semibold text-[#eaffff]">Sim {SIM_LABELS[i]}{sim.run_number != null ? ` · ${runLabel(sim)}` : ""}</span>
                <span className="text-xs text-[#5c8494] truncate">{simTitle(sim)}</span>
              </div>
              <FluxMap
                carbonSource={sim.carbon_source}
                growthRate={sim.growth_rate}
                conditionLabel={conditionLine(sim)}
                activePathways={sim.fba_results?.active_pathways || []}
                fluxDistribution={sim.flux_distribution}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Pathway Differences */}
      <Card className="p-6 bg-[#01070c] border-[#5c8494]/30">
        <h2 className="text-lg font-semibold mb-4">Pathway Differences</h2>
        {sims.length === 2 ? (() => {
          const p1 = new Set(sims[0].fba_results?.active_pathways || []);
          const p2 = new Set(sims[1].fba_results?.active_pathways || []);
          const only1 = Array.from(p1).filter(p => !p2.has(p));
          const only2 = Array.from(p2).filter(p => !p1.has(p));
          const shared = Array.from(p1).filter(p => p2.has(p));

          return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h3 className="mb-3 font-semibold pb-2 border-b border-white/10 text-[#eaffff] flex items-center gap-1.5"><Swatch color={SIM_COLORS[0]} /> Only in Sim A</h3>
                {only1.length > 0 ? (
                  <ul className="space-y-1 text-sm text-[#8cc3d4]">
                    {only1.map(p => <li key={p}>&bull; {p}</li>)}
                  </ul>
                ) : <div className="text-sm text-[#5c8494]">None</div>}
              </div>
              <div>
                <h3 className="mb-3 font-semibold pb-2 border-b border-white/10 text-[#eaffff] flex items-center gap-1.5"><Swatch color={SIM_COLORS[1]} /> Only in Sim B</h3>
                {only2.length > 0 ? (
                  <ul className="space-y-1 text-sm text-[#8cc3d4]">
                    {only2.map(p => <li key={p}>&bull; {p}</li>)}
                  </ul>
                ) : <div className="text-sm text-[#5c8494]">None</div>}
              </div>
              <div>
                <h3 className="mb-3 font-semibold pb-2 border-b border-[#5c8494]/30 text-[#eaffff]">Shared</h3>
                {shared.length > 0 ? (
                  <ul className="space-y-1 text-sm text-[#8cc3d4]">
                    {shared.map(p => <li key={p}>&bull; {p}</li>)}
                  </ul>
                ) : <div className="text-sm text-[#5c8494]">None</div>}
              </div>
            </div>
          );
        })() : (
          <div className="text-sm text-[#5c8494]">Pathway difference view is optimized for 2 simulations. {sims.length > 2 && "Detailed differences omitted for >2 sims."}</div>
        )}
      </Card>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="p-8 flex justify-center"><Spinner /></div>}>
      <CompareContent />
    </Suspense>
  );
}