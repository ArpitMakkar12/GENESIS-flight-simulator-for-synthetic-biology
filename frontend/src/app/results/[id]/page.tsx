"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, StatusBadge } from "@/components/ui/card";
import { Spinner, ErrorBanner } from "@/components/ui/loading";
import { exportSimulationMarkdown, exportSimulationPdf } from "@/components/export-markdown";
import { PdfButton } from "@/components/pdf-button";
import { FluxMap } from "@/components/flux-map";
import { ProcessTrace } from "@/components/process-trace";
import { GeneExpression, type GeneRow, type ExpressionSummary } from "@/components/gene-expression";
import { Pencil, Check, X } from "lucide-react";
import { runLabel, simTitle, autoTitle, fullTitle, conditionLine, formatDateTime, formatGrowth, GROWTH_UNIT, percentOfReference, REFERENCE_CONDITION } from "@/lib/sim-format";

const API = "http://localhost:8000/api/v1";

type ExpressionResult = GeneRow;

interface FbaResults {
  active_pathways: string[];
  bottlenecks: string[];
  bottleneck_names?: Record<string, string>;  // reaction id -> readable name
  pathway_fluxes?: Record<string, number>;
  active_tfs?: string[];
  growth_state?: string;
  solver_status?: string;
  infeasibility_reason?: string | null;
  regulator_state?: Record<string, boolean>;
  tf_state_changes?: Record<string, string>;  // regulator -> "on" | "off"
  expression_summary?: ExpressionSummary & { genes_by_source?: Record<string, number> };
}

interface SimulationDetail {
  id: string;
  run_number: number | null;
  name: string | null;
  status: string;
  growth_state?: string;
  solver_status?: string;
  infeasibility_reason?: string | null;
  temperature: number;
  ph: number;
  oxygen_level: string;
  carbon_source: string;
  nitrogen_source: string;
  growth_rate: number;
  doubling_time: number | null;
  viability_score: number;
  expression_results: ExpressionResult[] | null;
  fba_results: FbaResults | null;
  flux_distribution: Record<string, number> | null;
  model_versions: Record<string, string> | null;
  compute_time_ms: number;
  created_at: string;
  completed_at: string;
}

export default function SimulationDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const [sim, setSim] = useState<SimulationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [rawExpanded, setRawExpanded] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  // Rename: null = not editing, otherwise the text being typed
  const [draftName, setDraftName] = useState<string | null>(null);
  const [savingName, setSavingName] = useState<boolean>(false);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSim = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API}/results/${id}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch simulation detail: ${response.statusText}`);
        }
        const data = await response.json();
        setSim(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "An unknown error occurred");
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      fetchSim();
    }
  }, [id]);

  // Browser tab shows "#12 · Heat shock test · GENESIS" instead of the generic site title
  useEffect(() => {
    if (sim) document.title = `${fullTitle(sim)} · GENESIS`;
  }, [sim]);

  // Same in-page confirmation as the Results list (no browser pop-up)
  const handleDelete = async () => {
    try {
      setDeleting(true);
      setDeleteError(null);
      const res = await fetch(`${API}/results/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      router.push("/results");
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  };

  const saveName = async () => {
    if (draftName === null || !sim) return;
    try {
      setSavingName(true);
      setNameError(null);
      const res = await fetch(`${API}/results/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: draftName }),
      });
      if (!res.ok) throw new Error(res.status === 422 ? "Name is too long (120 characters max)" : `Save failed (${res.status})`);
      const data = (await res.json()) as { name: string | null };
      setSim({ ...sim, name: data.name });
      setDraftName(null);
    } catch (err: unknown) {
      setNameError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSavingName(false);
    }
  };

  const handleCopyRaw = () => {
    if (sim) {
      navigator.clipboard.writeText(JSON.stringify(sim, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error || !sim) {
    return <ErrorBanner message={error || "Simulation not found."} />;
  }

  const conditionSummary = conditionLine(sim);

  // B1: show the biological growth state, not the LP solver status.
  const growthState = sim.growth_state ?? sim.fba_results?.growth_state ?? sim.status;
  const infeasibilityReason = sim.infeasibility_reason ?? sim.fba_results?.infeasibility_reason ?? null;
  const summary = sim.fba_results?.expression_summary;
  const expressionResults = sim.expression_results ?? [];

  return (
    <div className="page-enter space-y-6 pb-20">
      {/* Header Breadcrumb Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/[0.07] pb-4">
        <div>
          <button
            onClick={() => router.push("/results")}
            className="text-muted hover:text-white transition-colors mb-2 text-sm"
          >
            ← Results
          </button>
          {draftName === null ? (
            <div className="flex items-center gap-3 flex-wrap">
              {sim.run_number != null && (
                <span className="text-xl font-mono-readout text-[#5c8494]">{runLabel(sim)}</span>
              )}
              <h1 className="text-xl font-medium text-[#eaffff]">{simTitle(sim)}</h1>
              <button
                onClick={() => { setDraftName(sim.name ?? ""); setNameError(null); }}
                className="p-1 text-[#5c8494] hover:text-[#7dffef] transition-colors"
                title="Rename"
                aria-label="Rename simulation"
              >
                <Pencil className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              </button>
            </div>
          ) : (
            <form
              onSubmit={(e) => { e.preventDefault(); saveName(); }}
              className="flex items-center gap-2 flex-wrap"
            >
              {sim.run_number != null && (
                <span className="text-xl font-mono-readout text-[#5c8494]">{runLabel(sim)}</span>
              )}
              <input
                autoFocus
                value={draftName}
                maxLength={120}
                onChange={(e) => setDraftName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Escape") setDraftName(null); }}
                placeholder={autoTitle(sim)}
                aria-label="Simulation name"
                className="w-72 max-w-full px-3 py-1.5 rounded-lg bg-[#01070c]/60 border border-[#3ef2ff]/40 text-[#eaffff] text-base focus:outline-none focus:border-[#3ef2ff]/80"
              />
              <button type="submit" disabled={savingName} className="p-1.5 text-[#7dffef] hover:text-[#eaffff] disabled:opacity-50" title="Save" aria-label="Save name">
                <Check className="h-4 w-4" aria-hidden="true" />
              </button>
              <button type="button" onClick={() => setDraftName(null)} className="p-1.5 text-[#5c8494] hover:text-[#eaffff]" title="Cancel" aria-label="Cancel rename">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
              <span className="w-full text-xs text-[#5c8494]">Leave empty to use the automatic title. Enter saves, Esc cancels.</span>
            </form>
          )}
          {nameError && <p className="text-xs text-[#ff8b6e] mt-1">{nameError}</p>}
          <p className="text-sm text-[#8cc3d4] mt-1">
            {sim.name ? `${conditionSummary} · ` : ""}{formatDateTime(sim.created_at)}
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => exportSimulationMarkdown(sim)}
            className="px-4 py-2 text-sm rounded-xl bg-white/[0.04] border border-white/[0.07] text-[#eaffff] hover:bg-white/[0.08] transition-colors"
          >
            Export .md
          </button>
          <PdfButton
            onExport={() => exportSimulationPdf(sim)}
            className="px-4 py-2 text-sm rounded-xl bg-white/[0.04] border border-white/[0.07] text-[#eaffff] hover:bg-white/[0.08] transition-colors"
          />
          <button
            onClick={() => { setDeleteError(null); setConfirmDelete(true); }}
            disabled={deleting}
            className="px-4 py-2 text-sm rounded-xl bg-red-900/30 border border-red-500/30 text-red-400 hover:bg-red-900/50 transition-colors disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Delete confirmation (matches the Results list) */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => !deleting && setConfirmDelete(false)}>
          <div className="p-6 max-w-sm mx-4 bg-[#031722] border border-white/[0.07] rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-[#d9f7ff] mb-2">Delete {runLabel(sim) || "this simulation"}?</h3>
            <p className="text-xs text-[#8cc3d4] mb-4">This action cannot be undone. The simulation data will be permanently removed.</p>
            {deleteError && <p className="text-xs text-[#ff8b6e] mb-3">{deleteError}. Nothing was removed; try again.</p>}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmDelete(false)} disabled={deleting}
                className="px-4 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors disabled:opacity-50">Cancel</button>
              <button onClick={handleDelete} disabled={deleting}
                className="px-4 py-1.5 text-xs rounded-xl bg-[#ff5a36]/20 text-[#ff5a36] border border-[#ff5a36]/30 hover:bg-[#ff5a36]/30 transition-colors disabled:opacity-50">
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <div className="text-2xl font-mono-readout text-[#3ef2ff] glow-text">{formatGrowth(sim.growth_rate, false)} {GROWTH_UNIT}</div>
          <div className="text-xs text-[#5c8494] mt-1 uppercase tracking-wider">Growth Rate</div>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <div className="text-2xl font-mono-readout text-[#3ef2ff] glow-text">
            {sim.doubling_time != null ? `${sim.doubling_time.toFixed(2)} h` : "∞"}
          </div>
          <div className="text-xs text-[#5c8494] mt-1 uppercase tracking-wider">Doubling Time</div>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <div className="text-2xl font-mono-readout text-[#7dffef] glow-text">
            {sim.viability_score ? (sim.viability_score * 100).toFixed(0) : "0"}%
          </div>
          <div className="text-xs text-[#5c8494] mt-1 uppercase tracking-wider">Viability</div>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <StatusBadge status={growthState} growthRate={sim.growth_rate} />
          {percentOfReference(sim.growth_rate) != null && (
            <div className="text-xs text-[#8cc3d4] mt-1.5 font-mono-readout" title={`Reference: ${REFERENCE_CONDITION}`}>
              {percentOfReference(sim.growth_rate)}% of reference
            </div>
          )}
          <div className="text-xs text-[#5c8494] mt-1 uppercase tracking-wider">Vs Reference</div>
        </div>
      </div>

      {/* V7: why no growth */}
      {infeasibilityReason && (
        <Card className="border-red-500/20 bg-red-500/5 p-5">
          <h3 className="text-sm font-semibold text-red-300 mb-1">No feasible growth</h3>
          <p className="text-sm text-[#8cc3d4]">{infeasibilityReason}</p>
        </Card>
      )}

      {/* Environment: one compact row instead of a tall card next to a short one */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-[#d9f7ff] mb-3">Environment Conditions</h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {[
            ["Temperature", `${sim.temperature} °C`],
            ["pH", `${sim.ph}`],
            ["Oxygen", sim.oxygen_level],
            ["Carbon source", sim.carbon_source],
            ["Nitrogen source", sim.nitrogen_source],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-[#5c8494] uppercase tracking-wider">{label}</dt>
              <dd className="text-[#eaffff] font-mono-readout mt-1">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {/* Process Trace (full width; expands downward when opened) */}
      <ProcessTrace
        computeTimeMs={sim.compute_time_ms}
        modelVersions={sim.model_versions || {}}
        temperature={sim.temperature}
        ph={sim.ph}
        oxygenLevel={sim.oxygen_level}
        carbonSource={sim.carbon_source}
        nitrogenSource={sim.nitrogen_source}
        growthState={growthState}
        growthRate={sim.growth_rate}
        pathwayCount={Object.keys(sim.fba_results?.pathway_fluxes ?? {}).length || sim.fba_results?.active_pathways?.length || 0}
        expressionCount={summary?.total_genes_evaluated ?? expressionResults.length}
      />

      {/* Flux Map */}
      <div className="mt-8">
        <h2 className="text-lg font-medium text-[#eaffff] mb-4">Metabolic Flux</h2>
        <FluxMap
          carbonSource={sim.carbon_source}
          growthRate={sim.growth_rate}
          conditionLabel={conditionSummary}
          activePathways={sim.fba_results?.active_pathways || []}
          fluxDistribution={sim.flux_distribution || {}}
        />
      </div>

      {/* Bottlenecks */}
      {sim.fba_results?.bottlenecks && sim.fba_results.bottlenecks.length > 0 && (
        <Card className="border-amber-500/20 bg-amber-500/5 p-5">
          <h3 className="text-sm font-semibold text-amber-300 mb-3">Detected Bottlenecks</h3>
          <div className="flex flex-wrap gap-2">
            {sim.fba_results.bottlenecks.map((b, i) => (
              <span key={i} className="px-3 py-1 bg-amber-500/20 text-amber-300 rounded text-sm border border-amber-500/30" title={sim.fba_results?.bottleneck_names?.[b] ?? b}>
                {b}
                {sim.fba_results?.bottleneck_names?.[b] && (
                  <span className="ml-1.5 text-xs text-amber-200/70">{sim.fba_results.bottleneck_names[b]}</span>
                )}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Expression Predictions: tabs, search over every gene, short list */}
      <GeneExpression
        simId={sim.id}
        summary={summary}
        customPart={expressionResults.find((e) => e.gene_id.startsWith("custom_part"))}
      />

      {/* Raw Output Toggle */}
      <Card className="!p-0 overflow-hidden mt-6">
        <button
          onClick={() => setRawExpanded(!rawExpanded)}
          className="w-full p-4 flex justify-between items-center text-left hover:bg-white/[0.02] transition-colors"
        >
          <span className="font-medium text-[#8cc3d4]">View Raw JSON {rawExpanded ? "▴" : "▾"}</span>
        </button>

        {rawExpanded && (
          <div className="p-4 border-t border-white/[0.07] relative">
            <button
              onClick={handleCopyRaw}
              className="absolute top-4 right-4 px-3 py-1 bg-white/[0.1] text-xs rounded hover:bg-white/[0.2] transition-colors text-[#eaffff]"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            <pre className="text-xs text-[#5c8494] font-mono-readout overflow-auto max-h-[400px] p-2 bg-[#01070c]/50 rounded">
              {JSON.stringify(sim, null, 2)}
            </pre>
          </div>
        )}
      </Card>
    </div>
  );
}