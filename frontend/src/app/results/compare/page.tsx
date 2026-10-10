"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, StatusBadge } from "@/components/ui/card";
import { Spinner, ErrorBanner } from "@/components/ui/loading";
import { FluxMap } from "@/components/flux-map";
import { runLabel, simTitle, conditionLine, formatGrowth, GROWTH_UNIT } from "@/lib/sim-format";
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

const SIM_COLORS = ["#3ef2ff", "#b98bff", "#ffcf66", "#7dffef"];
const SIM_LABELS = ["A", "B", "C", "D"];

function exportComparisonMarkdown(sims: SimDetail[]) {
  const date = new Date().toISOString().split("T")[0];
  let md = `# Genesis Simulation Comparison (${date})\n\n`;

  md += `| Metric | ${sims.map((_, i) => `Sim ${SIM_LABELS[i]}`).join(" | ")} |\n`;
  md += `| --- | ${sims.map(() => "---").join(" | ")} |\n`;
  md += `| Run | ${sims.map(s => runLabel(s) || s.id.substring(0, 8)).join(" | ")} |\n`;
  md += `| Name | ${sims.map(s => simTitle(s)).join(" | ")} |\n`;
  md += `| Status | ${sims.map(s => s.status).join(" | ")} |\n`;
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

  // Chart Data
  const chartData = [
    { name: "Growth Rate", ...sims.reduce((acc, sim, i) => ({ ...acc, [SIM_LABELS[i]]: sim.growth_rate }), {}) },
    { name: "Doubling Time", ...sims.reduce((acc, sim, i) => ({ ...acc, [SIM_LABELS[i]]: sim.doubling_time }), {}) },
    { name: "Viability %", ...sims.reduce((acc, sim, i) => ({ ...acc, [SIM_LABELS[i]]: sim.viability_score ? sim.viability_score * 100 : 0 }), {}) }
  ];

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
              <span className="font-semibold" style={{ color: SIM_COLORS[i] }}>
                Sim {SIM_LABELS[i]}{sim.run_number != null && <span className="font-mono-readout font-normal text-[#5c8494]"> · {runLabel(sim)}</span>}
              </span>
              <StatusBadge status={sim.status} />
            </div>
            <div className="text-sm text-[#eaffff] mb-1">{simTitle(sim)}</div>
            {sim.name && <div className="text-xs text-[#5c8494] mb-3">{conditionLine(sim)}</div>}
            <div className={`font-mono-readout text-2xl text-[#eaffff] ${sim.name ? "" : "mt-3"}`}>
              {formatGrowth(sim.growth_rate, false)} <span className="text-sm text-[#5c8494]">{GROWTH_UNIT}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Bar Chart */}
      <Card className="p-6 bg-[#01070c] border-[#5c8494]/30 h-80">
        <h2 className="text-lg font-semibold mb-6">Metrics Comparison</h2>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#5c8494" opacity={0.3} />
            <XAxis dataKey="name" stroke="#8cc3d4" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#8cc3d4" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: "#01070c", borderColor: "#5c8494", color: "#eaffff" }}
              itemStyle={{ color: "#eaffff" }}
            />
            <Legend wrapperStyle={{ paddingTop: "20px" }} />
            {sims.map((_, i) => (
              <Bar key={SIM_LABELS[i]} dataKey={SIM_LABELS[i]} fill={SIM_COLORS[i]} radius={[4, 4, 0, 0]} maxBarSize={50} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Flux Maps */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Flux Distributions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sims.map((sim, i) => (
            <div key={sim.id} className="p-4 bg-white/[0.04] border border-white/[0.07] rounded-2xl" style={{ borderTopWidth: 4, borderTopColor: SIM_COLORS[i] }}>
              <div className="mb-4">
                <span className="font-semibold" style={{ color: SIM_COLORS[i] }}>Sim {SIM_LABELS[i]}{sim.run_number != null ? ` · ${runLabel(sim)}` : ""}</span>
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
                <h3 className="mb-3 font-semibold pb-2 border-b border-[#3ef2ff]/30" style={{ color: SIM_COLORS[0] }}>Only in Sim A</h3>
                {only1.length > 0 ? (
                  <ul className="space-y-1 text-sm text-[#8cc3d4]">
                    {only1.map(p => <li key={p}>&bull; {p}</li>)}
                  </ul>
                ) : <div className="text-sm text-[#5c8494]">None</div>}
              </div>
              <div>
                <h3 className="mb-3 font-semibold pb-2 border-b border-[#b98bff]/30" style={{ color: SIM_COLORS[1] }}>Only in Sim B</h3>
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