"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, StatusBadge } from "@/components/ui/card";
import { Spinner, ErrorBanner } from "@/components/ui/loading";
import { FluxMap } from "@/components/flux-map";
import { exportComparisonMarkdown, exportComparisonPdf } from "@/components/export-markdown";
import { PdfButton } from "@/components/pdf-button";
import { pathwayDiff, fmtPathway, allOf, MAX_COMPARE, type PathwayRow } from "@/lib/pathway-diff";
import { FLUX_UNIT } from "@/lib/flux-summary";
import {
  runLabel, simTitle, conditionLine, formatGrowth, GROWTH_UNIT,
  REFERENCE_GROWTH_RATE, REFERENCE_CONDITION,
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
  infeasibility_reason?: string | null;
  expression_results: { gene_id: string; gene_name?: string | null; relative_expression: number; confidence: number }[] | null;
  fba_results: {
    active_pathways: string[];
    bottlenecks: string[];
    pathway_fluxes?: Record<string, number> | null;
    tf_state_changes?: Record<string, string> | null;
    expression_summary?: { genes_up: number; genes_down: number; total_genes_evaluated: number } | null;
  } | null;
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

/** Column headers shared by the pathway tables: swatch + "A · #145". */
function RunHeaders({ sims }: { sims: SimDetail[] }) {
  return (
    <>
      {sims.map((sim, i) => (
        <th key={sim.id} className="p-2 text-right font-medium whitespace-nowrap">
          <span className="inline-flex items-center gap-1.5">
            <Swatch color={SIM_COLORS[i]} /> {SIM_LABELS[i]}
            {sim.run_number != null && <span className="font-mono-readout text-[#5c8494]">{runLabel(sim)}</span>}
          </span>
        </th>
      ))}
    </>
  );
}

function PathwayTable({ sims, rows, exact, showRatio }: { sims: SimDetail[]; rows: PathwayRow[]; exact: boolean; showRatio?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-xs text-[#8cc3d4]">
            <th className="p-2 text-left font-medium">Pathway</th>
            <RunHeaders sims={sims} />
            {showRatio && <th className="p-2 text-right font-medium" title="Max ÷ min of pathway flux per unit growth">Beyond growth</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const top = Math.max(...row.values);
            return (
              <tr key={row.pathway} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.03]">
                <td className="p-2 text-[#d9f7ff]">{row.pathway}</td>
                {row.values.map((v, i) => (
                  <td key={i} className={`p-2 text-right font-mono-readout ${v === top && exact ? "text-[#eaffff] font-semibold" : "text-[#8cc3d4]"}`}>
                    {fmtPathway(v, exact)}
                  </td>
                ))}
                {showRatio && <td className="p-2 text-right font-mono-readout text-[#8cc3d4]">{row.ratio!.toFixed(1)}×</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Same layout for 2, 3 or 4 runs:
 *   - switched on/off: pathways with flux in some runs and none in others
 *   - biggest changes: running everywhere but at very different levels
 *   - the shared rest, folded away
 */
function PathwayDifferences({ sims }: { sims: SimDetail[] }) {
  const diff = pathwayDiff(sims);
  const n = sims.length;
  return (
    <Card className="p-6 bg-[#01070c] border-[#5c8494]/30 space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Pathway Differences</h2>
        <p className="text-sm text-[#8cc3d4] mt-1">
          {diff.shared.length} pathways run in {allOf(n)} · {diff.switched.length} switched on/off
          {diff.exact && ` · ${diff.bigChanges.length} shifted beyond what growth explains`}
        </p>
        {!diff.exact && (
          <p className="text-xs text-amber-300/80 mt-2">
            Some of these runs have no saved fluxes, so this falls back to their top-15 pathway lists: ✓ means listed, which is not the same as switched on.
          </p>
        )}
      </div>

      <section>
        <h3 className="text-sm font-semibold text-[#d9f7ff]">Switched on or off</h3>
        <p className="text-xs text-[#5c8494] mb-2">
          {diff.exact ? `Total flux through each pathway (${FLUX_UNIT}); — means no flux. Highest value in bold.` : "Listed in the run's top-15 pathways."}
        </p>
        {diff.switched.length > 0
          ? <PathwayTable sims={sims} rows={diff.switched} exact={diff.exact} />
          : <p className="text-sm text-[#5c8494]">None — every pathway runs in {allOf(n)} simulations.</p>}
      </section>

      {diff.exact && (
        <section>
          <h3 className="text-sm font-semibold text-[#d9f7ff]">Biggest changes among shared pathways</h3>
          <p className="text-xs text-[#5c8494] mb-2">
            {diff.growthAdjusted
              ? "Running in every simulation, but differing at least 2× even after allowing for growth (a faster-growing cell builds more of everything). Values are raw totals; the last column is the growth-adjusted difference."
              : "Running in every simulation, but the busiest carries at least twice the flux of the quietest."}
          </p>
          {diff.bigChanges.length > 0
            ? <PathwayTable sims={sims} rows={diff.bigChanges} exact showRatio />
            : <p className="text-sm text-[#5c8494]">No shared pathway differs by 2× or more beyond the growth difference.</p>}
        </section>
      )}

      {diff.shared.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-sm text-[#8cc3d4] hover:text-[#eaffff]">
            Running in {allOf(n)} simulations ({diff.shared.length})
          </summary>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {diff.shared.map((p) => (
              <span key={p} className="px-2.5 py-0.5 text-[11px] rounded-full border border-white/[0.08] bg-white/[0.03] text-[#8cc3d4]">{p}</span>
            ))}
          </div>
        </details>
      )}
    </Card>
  );
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

    const ids = idsParam.split(",").slice(0, MAX_COMPARE);
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
        <div className="flex gap-3">
          <button
            onClick={() => exportComparisonMarkdown(sims, SIM_LABELS)}
            className="px-4 py-2 bg-[#b98bff]/20 text-[#d4bcff] rounded-xl hover:bg-[#b98bff]/30 transition-colors border border-[#b98bff]/50"
          >
            Export .md
          </button>
          <PdfButton
            onExport={() => exportComparisonPdf(sims, SIM_LABELS)}
            className="px-4 py-2 bg-[#b98bff]/20 text-[#d4bcff] rounded-xl hover:bg-[#b98bff]/30 transition-colors border border-[#b98bff]/50"
          />
        </div>
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

      {/* Pathway Differences (works for 2, 3 or 4 runs) */}
      <PathwayDifferences sims={sims} />
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