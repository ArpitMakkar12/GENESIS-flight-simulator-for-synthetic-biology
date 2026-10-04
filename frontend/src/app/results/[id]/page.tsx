"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, StatusBadge, DetailRow } from "@/components/ui/card";
import { Spinner, ErrorBanner } from "@/components/ui/loading";
import { exportSimulationMarkdown } from "@/components/export-markdown";
import { FluxMap } from "@/components/flux-map";
import { ProcessTrace } from "@/components/process-trace";

interface ExpressionResult {
  gene_id: string;
  relative_expression: number;
  confidence: number;
  prediction_source?: string; // what the API actually sends ("lookup" | "model" | "fallback")
  source?: string;            // legacy field name, kept for older stored results
  reference_tpm?: number | null;
  rbs_score?: number | null;
}

interface ExpressionSummary {
  genes_up: number;
  genes_down: number;
  total_genes_evaluated: number;
  genes_with_changed_expression: number;
  genes_by_source?: Record<string, number>;
}

interface FbaResults {
  active_pathways: string[];
  bottlenecks: string[];
  active_tfs?: string[];
  growth_state?: string;
  solver_status?: string;
  infeasibility_reason?: string | null;
  regulator_state?: Record<string, boolean>;
  tf_state_changes?: Record<string, unknown>;
  expression_summary?: ExpressionSummary;
}

interface SimulationDetail {
  id: string;
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

/** Fold change as "2.00×" / "0.375×" — clearer than a percentage for regulation. */
function formatFold(value: number): string {
  if (value >= 1) return `${value.toFixed(2)}×`;
  return `${value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}×`;
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

  useEffect(() => {
    const fetchSim = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:8000/api/v1/results/${id}`);
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

  const handleDelete = async () => {
    if (!window.confirm("Delete this simulation? This cannot be undone.")) return;
    try {
      setDeleting(true);
      const res = await fetch(`http://localhost:8000/api/v1/results/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete simulation");
      router.push("/results");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
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

  const conditionSummary = `${sim.temperature}°C · pH ${sim.ph} · ${sim.oxygen_level} · ${sim.carbon_source}`;

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
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-medium text-[#eaffff]">Simulation {id.slice(0, 8)}...</h1>
            <span className="text-xs text-subtle font-mono-readout">{new Date(sim.created_at).toLocaleString()}</span>
          </div>
          <p className="text-sm text-[#8cc3d4] mt-1">{conditionSummary}</p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => exportSimulationMarkdown(sim)}
            className="px-4 py-2 text-sm rounded bg-white/[0.04] border border-white/[0.07] text-[#eaffff] hover:bg-white/[0.08] transition-colors"
          >
            Export .md
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-4 py-2 text-sm rounded bg-red-900/30 border border-red-500/30 text-red-400 hover:bg-red-900/50 transition-colors disabled:opacity-50"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>

      {/* Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <div className="text-2xl font-mono-readout text-[#3ef2ff] glow-text">{sim.growth_rate?.toFixed(3) || "0"} h⁻¹</div>
          <div className="text-xs text-[#5c8494] mt-1 uppercase tracking-wider">Growth Rate</div>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md p-4 flex flex-col items-center justify-center">
          <div className="text-2xl font-mono-readout text-[#3ef2ff] glow-text">
            {sim.doubling_time != null ? `${sim.doubling_time.toFixed(2)} hr` : "∞"}
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
          <StatusBadge status={growthState} />
          <div className="text-xs text-[#5c8494] mt-2 uppercase tracking-wider">Growth State</div>
        </div>
      </div>

      {/* V7: why no growth */}
      {infeasibilityReason && (
        <Card className="border-red-500/20 bg-red-500/5 p-5">
          <h3 className="text-sm font-semibold text-red-300 mb-1">No feasible growth</h3>
          <p className="text-sm text-[#8cc3d4]">{infeasibilityReason}</p>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Environment Section */}
        <Card className="lg:col-span-1 h-fit p-5">
          <h3 className="text-sm font-semibold text-[#d9f7ff] mb-3">Environment Conditions</h3>
          <div className="space-y-3">
            <DetailRow label="Temperature" value={`${sim.temperature} °C`} />
            <DetailRow label="pH Level" value={`${sim.ph}`} />
            <DetailRow label="Oxygen" value={sim.oxygen_level} />
            <DetailRow label="Carbon Source" value={sim.carbon_source} />
            <DetailRow label="Nitrogen Source" value={sim.nitrogen_source} />
          </div>
        </Card>

        {/* Process Trace */}
        <div className="lg:col-span-2">
          <ProcessTrace
            computeTimeMs={sim.compute_time_ms}
            modelVersions={sim.model_versions || {}}
            temperature={sim.temperature}
            ph={sim.ph}
            oxygenLevel={sim.oxygen_level}
            carbonSource={sim.carbon_source}
            nitrogenSource={sim.nitrogen_source}
            status={sim.status}
            growthRate={sim.growth_rate}
            activePathwayCount={sim.fba_results?.active_pathways?.length || 0}
            expressionCount={summary?.total_genes_evaluated ?? expressionResults.length}
          />
        </div>
      </div>

      {/* Flux Map */}
      <div className="mt-8">
        <h2 className="text-lg font-medium text-[#eaffff] mb-4">Metabolic Flux</h2>
        <FluxMap
          oxygenLevel={sim.oxygen_level as "aerobic" | "anaerobic" | "microaerobic"}
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
              <span key={i} className="px-3 py-1 bg-amber-500/20 text-amber-300 rounded text-sm border border-amber-500/30">
                {b}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Expression Predictions */}
      <Card className="p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
          <h3 className="text-sm font-semibold text-[#d9f7ff]">Expression Predictions</h3>
          {summary && (
            <span className="text-xs text-[#5c8494] font-mono-readout">
              {summary.genes_up.toLocaleString()} up · {summary.genes_down.toLocaleString()} down ·{" "}
              {summary.total_genes_evaluated.toLocaleString()} evaluated
              {expressionResults.length > 0 && expressionResults.length < summary.genes_with_changed_expression
                ? ` · showing top ${expressionResults.length}`
                : ""}
            </span>
          )}
        </div>

        {expressionResults.length === 0 ? (
          <p className="text-[#5c8494] text-sm italic">
            {summary?.total_genes_evaluated
              ? `No genes changed vs reference — all ${summary.total_genes_evaluated.toLocaleString()} evaluated genes are at 1.0×.`
              : "No expression predictions available for this simulation."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.07] text-[#5c8494] text-xs uppercase tracking-wider">
                  <th className="pb-2 font-medium">Gene</th>
                  <th className="pb-2 font-medium">Fold vs Reference</th>
                  <th className="pb-2 font-medium">Reference TPM</th>
                  <th className="pb-2 font-medium">Confidence</th>
                  <th className="pb-2 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {expressionResults.map((expr, idx) => {
                  const source = expr.prediction_source ?? expr.source ?? "prediction";
                  const isStub = expr.confidence === 0 && source === "stub";
                  const fold = expr.relative_expression;
                  const foldColor =
                    fold > 1 ? "text-[#3ef2ff]" : fold < 1 ? "text-amber-300" : "text-[#8cc3d4]";
                  return (
                    <tr key={`${expr.gene_id}-${idx}`} className="border-b border-white/[0.02] last:border-0 hover:bg-white/[0.02]">
                      <td className="py-3 font-mono-readout text-[#8cc3d4]">{expr.gene_id}</td>
                      <td className="py-3">
                        {isStub ? (
                          <span className="text-[#5c8494] italic text-xs">model not yet trained</span>
                        ) : (
                          <span className={`${foldColor} font-mono-readout`}>
                            {fold > 1 ? "▲ " : fold < 1 ? "▼ " : ""}
                            {formatFold(fold)}
                          </span>
                        )}
                      </td>
                      <td className="py-3 font-mono-readout text-[#5c8494]">
                        {expr.reference_tpm != null ? expr.reference_tpm.toLocaleString() : "-"}
                      </td>
                      <td className="py-3">
                        {isStub ? "-" : (
                          <span className="text-[#7dffef] font-mono-readout">{(expr.confidence * 100).toFixed(0)}%</span>
                        )}
                      </td>
                      <td className="py-3 text-[#5c8494]">{source}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

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