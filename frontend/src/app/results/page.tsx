"use client";

import { useState, useEffect } from "react";

interface SimulationSummary {
  id: string;
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
}

interface SimulationDetail extends SimulationSummary {
  expression_results: {
    gene_id: string;
    relative_expression: number;
    confidence: number;
  }[] | null;
  fba_results: {
    active_pathways: string[];
    bottlenecks: string[];
  } | null;
  model_versions: Record<string, string> | null;
}

export default function ResultsPage() {
  const [simulations, setSimulations] = useState<SimulationSummary[]>([]);
  const [selected, setSelected] = useState<SimulationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSimulations();
  }, []);

  const fetchSimulations = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/results?limit=50");
      if (!res.ok) throw new Error("Failed to fetch results");
      const data: SimulationSummary[] = await res.json();
      setSimulations(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const selectSimulation = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/results/${id}`);
      if (!res.ok) throw new Error("Failed to fetch detail");
      const data: SimulationDetail = await res.json();
      setSelected(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    }
  };

  const formatDate = (isoStr: string | null) => {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Simulation Results</h1>

      {error && (
        <div className="p-4 rounded-xl border border-red-800 bg-red-950 text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Simulation list */}
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="text-left p-4">Date</th>
                  <th className="text-left p-4">Conditions</th>
                  <th className="text-left p-4">Growth Rate</th>
                  <th className="text-left p-4">Viability</th>
                  <th className="text-left p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">
                      Loading simulations...
                    </td>
                  </tr>
                )}
                {!loading && simulations.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">
                      No simulations yet. Go to{" "}
                      <a href="/simulate" className="text-green-400 hover:underline">
                        Simulate
                      </a>{" "}
                      to run your first simulation.
                    </td>
                  </tr>
                )}
                {simulations.map((sim) => (
                  <tr
                    key={sim.id}
                    onClick={() => selectSimulation(sim.id)}
                    className={`border-b border-gray-800/50 cursor-pointer transition-colors hover:bg-gray-800 ${
                      selected?.id === sim.id ? "bg-gray-800" : ""
                    }`}
                  >
                    <td className="p-4 text-gray-300">{formatDate(sim.created_at)}</td>
                    <td className="p-4">
                      <span className="text-xs text-gray-400">
                        {sim.temperature}&deg;C, pH {sim.ph}, {sim.oxygen_level}, {sim.carbon_source}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-white">
                      {sim.growth_rate !== null ? `${sim.growth_rate} hr\u207B\u00B9` : "-"}
                    </td>
                    <td className="p-4">
                      {sim.viability_score !== null ? (
                        <span className={sim.viability_score > 0.5 ? "text-green-400" : "text-red-400"}>
                          {(sim.viability_score * 100).toFixed(0)}%
                        </span>
                      ) : "-"}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        sim.status === "optimal" ? "bg-green-900 text-green-300" :
                        sim.status === "failed" ? "bg-red-900 text-red-300" :
                        "bg-gray-700 text-gray-300"
                      }`}>
                        {sim.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Detail panel */}
        <div className="space-y-4">
          {selected ? (
            <>
              <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                <h2 className="text-lg font-semibold text-gray-200 mb-4">Details</h2>
                <div className="space-y-3 text-sm">
                  <DetailRow label="Growth Rate" value={selected.growth_rate !== null ? `${selected.growth_rate} hr\u207B\u00B9` : "-"} />
                  <DetailRow label="Doubling Time" value={selected.doubling_time !== null ? `${selected.doubling_time} hr` : "-"} />
                  <DetailRow label="Viability" value={selected.viability_score !== null ? `${(selected.viability_score * 100).toFixed(0)}%` : "-"} />
                  <DetailRow label="Temperature" value={`${selected.temperature}\u00B0C`} />
                  <DetailRow label="pH" value={`${selected.ph}`} />
                  <DetailRow label="Oxygen" value={selected.oxygen_level} />
                  <DetailRow label="Carbon" value={selected.carbon_source} />
                  <DetailRow label="Nitrogen" value={selected.nitrogen_source} />
                  <DetailRow label="Compute" value={selected.compute_time_ms !== null ? `${selected.compute_time_ms} ms` : "-"} />
                  <DetailRow label="Model" value={selected.model_versions?.predictor || "unknown"} />
                </div>
              </div>

              {/* Active pathways */}
              {selected.fba_results?.active_pathways && selected.fba_results.active_pathways.length > 0 && (
                <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                  <h3 className="text-md font-semibold text-gray-200 mb-3">Active Pathways</h3>
                  <div className="flex flex-wrap gap-2">
                    {selected.fba_results.active_pathways.map((p, i) => (
                      <span key={i} className="px-2 py-1 text-xs rounded-full bg-green-900 text-green-300 border border-green-800">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Expression results */}
              {selected.expression_results && selected.expression_results.length > 0 && (
                <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                  <h3 className="text-md font-semibold text-gray-200 mb-3">Expression</h3>
                  <div className="space-y-1 text-xs">
                    {selected.expression_results.map((exp) => (
                      <div key={exp.gene_id} className="flex justify-between">
                        <span className="text-green-400 font-mono">{exp.gene_id}</span>
                        <span className="text-white">{exp.relative_expression.toFixed(2)}x</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
              <p className="text-gray-500 text-sm">
                Click a simulation row to view its full results.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-white font-mono">{value}</span>
    </div>
  );
}
