"use client";

import { useState } from "react";

interface SimulationResult {
  task_id: string;
  status: string;
  growth_rate: number | null;
  doubling_time: number | null;
  viability_score: number | null;
  expression_predictions: {
    gene_id: string;
    relative_expression: number;
    confidence: number;
  }[] | null;
  active_pathways: string[] | null;
  bottlenecks: string[] | null;
  model_versions: Record<string, string> | null;
  compute_time_ms: number | null;
}

export default function SimulatePage() {
  const [sequence, setSequence] = useState("");
  const [temperature, setTemperature] = useState(37);
  const [ph, setPh] = useState(7.0);
  const [oxygen, setOxygen] = useState("aerobic");
  const [carbonSource, setCarbonSource] = useState("glucose");
  const [nitrogenSource, setNitrogenSource] = useState("ammonium");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/v1/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_sequence: sequence || null,
          temperature,
          ph,
          oxygen_level: oxygen,
          carbon_source: carbonSource,
          nitrogen_source: nitrogenSource,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Simulation failed");
      }

      const data: SimulationResult = await response.json();
      setResult(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Run Simulation</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: DNA Input + Results */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-200 mb-3">
              DNA Sequence Input
            </h2>
            <textarea
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
              placeholder="Paste DNA sequence here (ATCG only)... Leave empty for default E. coli genes."
              className="w-full h-48 p-4 rounded-lg bg-gray-950 border border-gray-700 text-green-400 font-mono text-sm placeholder-gray-600 focus:border-green-500 focus:outline-none resize-none"
            />
            <div className="mt-2 text-xs text-gray-500">
              {sequence.length} bp | GC:{" "}
              {sequence.length > 0
                ? (
                    ((sequence.match(/[GCgc]/g)?.length || 0) /
                      sequence.length) *
                    100
                  ).toFixed(1)
                : "0.0"}
              %
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="p-4 rounded-xl border border-red-800 bg-red-950 text-red-300 text-sm">
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              {/* Growth metrics */}
              <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                <h2 className="text-lg font-semibold text-gray-200 mb-4">
                  Simulation Results
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard
                    label="Growth Rate"
                    value={result.growth_rate !== null ? `${result.growth_rate} hr⁻¹` : "N/A"}
                    color={result.growth_rate && result.growth_rate > 0.5 ? "green" : result.growth_rate && result.growth_rate > 0.1 ? "yellow" : "red"}
                  />
                  <MetricCard
                    label="Doubling Time"
                    value={result.doubling_time !== null ? `${result.doubling_time} hr` : "N/A"}
                    color="blue"
                  />
                  <MetricCard
                    label="Viability"
                    value={result.viability_score !== null ? `${(result.viability_score * 100).toFixed(0)}%` : "N/A"}
                    color={result.viability_score && result.viability_score > 0.5 ? "green" : "red"}
                  />
                  <MetricCard
                    label="Compute Time"
                    value={result.compute_time_ms !== null ? `${result.compute_time_ms} ms` : "N/A"}
                    color="gray"
                  />
                </div>
                <div className="mt-3 text-xs text-gray-500">
                  Status: {result.status} | Model: {result.model_versions?.predictor || "unknown"}
                </div>
              </div>

              {/* Active pathways */}
              {result.active_pathways && result.active_pathways.length > 0 && (
                <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                  <h3 className="text-md font-semibold text-gray-200 mb-3">
                    Active Metabolic Pathways
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.active_pathways.map((pathway, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 text-xs rounded-full bg-green-900 text-green-300 border border-green-800"
                      >
                        {pathway}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Expression predictions */}
              {result.expression_predictions && result.expression_predictions.length > 0 && (
                <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
                  <h3 className="text-md font-semibold text-gray-200 mb-3">
                    Expression Predictions
                  </h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-800">
                        <th className="text-left p-2">Gene</th>
                        <th className="text-left p-2">Relative Expression</th>
                        <th className="text-left p-2">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.expression_predictions.map((pred) => (
                        <tr key={pred.gene_id} className="border-b border-gray-800/50">
                          <td className="p-2 text-green-400 font-mono">{pred.gene_id}</td>
                          <td className="p-2 text-white">{pred.relative_expression.toFixed(2)}x</td>
                          <td className="p-2">
                            <span className={pred.confidence > 0.5 ? "text-green-400" : "text-yellow-400"}>
                              {(pred.confidence * 100).toFixed(0)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Bottlenecks */}
              {result.bottlenecks && result.bottlenecks.length > 0 && (
                <div className="p-6 rounded-xl border border-yellow-800 bg-yellow-950">
                  <h3 className="text-md font-semibold text-yellow-200 mb-2">
                    Bottleneck Reactions
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.bottlenecks.map((b, i) => (
                      <span key={i} className="px-3 py-1 text-xs rounded-full bg-yellow-900 text-yellow-300">
                        {b}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && !error && (
            <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
              <h2 className="text-lg font-semibold text-gray-200 mb-3">
                Results
              </h2>
              <p className="text-gray-500 text-sm">
                Run a simulation to see expression predictions, metabolic flux,
                and growth rate here.
              </p>
            </div>
          )}
        </div>

        {/* Right: Environment Controls */}
        <div className="space-y-4">
          <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-200 mb-4">
              Environment
            </h2>

            <div className="space-y-4">
              <SliderControl
                label="Temperature"
                value={temperature}
                onChange={setTemperature}
                min={20}
                max={50}
                unit="°C"
              />
              <SliderControl
                label="pH"
                value={ph}
                onChange={setPh}
                min={4}
                max={9}
                step={0.1}
                unit=""
              />

              <SelectControl
                label="Oxygen"
                value={oxygen}
                onChange={setOxygen}
                options={["aerobic", "microaerobic", "anaerobic"]}
              />
              <SelectControl
                label="Carbon Source"
                value={carbonSource}
                onChange={setCarbonSource}
                options={[
                  "glucose",
                  "lactose",
                  "glycerol",
                  "acetate",
                  "succinate",
                  "fructose",
                  "galactose",
                ]}
              />
              <SelectControl
                label="Nitrogen Source"
                value={nitrogenSource}
                onChange={setNitrogenSource}
                options={["ammonium", "glutamine", "nitrate"]}
              />
            </div>

            <button
              className={`w-full mt-6 py-3 rounded-lg font-semibold transition-colors ${
                loading
                  ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                  : "bg-green-600 hover:bg-green-500 text-white"
              }`}
              onClick={runSimulation}
              disabled={loading}
            >
              {loading ? "⏳ Running Simulation..." : "▶ Run Simulation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    green: "text-green-400",
    yellow: "text-yellow-400",
    red: "text-red-400",
    blue: "text-blue-400",
    gray: "text-gray-400",
  };
  return (
    <div className="p-3 rounded-lg bg-gray-950 border border-gray-800">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${colorMap[color] || "text-white"}`}>
        {value}
      </div>
    </div>
  );
}

function SliderControl({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  unit: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-mono">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-green-500"
      />
    </div>
  );
}

function SelectControl({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="text-sm text-gray-400 block mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full p-2 rounded-lg bg-gray-950 border border-gray-700 text-white text-sm focus:border-green-500 focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt.charAt(0).toUpperCase() + opt.slice(1)}
          </option>
        ))}
      </select>
    </div>
  );
}
