"use client";

import { useState, useEffect, useMemo, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, Cell,
} from "recharts";
import { Card, MetricCard } from "@/components/ui/card";
import { LaunchSequence, ErrorBanner } from "@/components/ui/loading";
import { EnvParams, PRESETS, DEFAULT_PARAMS, shallowEqual } from "@/lib/presets";
import { Timer, HeartPulse, Zap, FlaskConical, LoaderCircle, Play } from "lucide-react";
import { GROWTH_UNIT, growthStateLabel, percentOfReference, REFERENCE_GROWTH_RATE } from "@/lib/sim-format";

const API = "http://localhost:8000/api/v1";

/* ─── Types ───────────────────────────────────────────────── */

interface SimulationResult {
  task_id: string;
  run_number?: number | null;
  name?: string | null;
  status: string;
  solver_status?: string | null;
  growth_state?: string | null;
  infeasibility_reason?: string | null;
  growth_rate: number | null;
  doubling_time: number | null;
  viability_score: number | null;
  expression_predictions: { gene_id: string; relative_expression: number; confidence: number }[] | null;
  active_pathways: string[] | null;
  bottlenecks: string[] | null;
  model_versions: Record<string, string> | null;
  compute_time_ms: number | null;
}

/* ─── Constants ───────────────────────────────────────────── */

const CARBON_OPTIONS = ["glucose", "lactose", "glycerol", "acetate", "succinate", "fructose", "galactose", "arabinose", "xylose"];
const NITROGEN_OPTIONS = ["ammonium", "glutamine", "nitrate"];
const OXYGEN_OPTIONS = ["aerobic", "microaerobic", "anaerobic"];

/* ─── Page wrapper (Suspense for useSearchParams) ─────────── */

export default function SimulatePage() {
  return (
    <Suspense fallback={<div className="text-[#5c8494]">Loading...</div>}>
      <SimulateContent />
    </Suspense>
  );
}

/* ─── Main content ────────────────────────────────────────── */

function SimulateContent() {
  const searchParams = useSearchParams();

  // ── Single source of truth for environment parameters ──
  const [params, setParams] = useState<EnvParams>(DEFAULT_PARAMS);
  const [sequence, setSequence] = useState("");
  const [runName, setRunName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seqError, setSeqError] = useState<string | null>(null);

  // Track whether params changed during an in-flight simulation
  const inflightParamsRef = useRef<EnvParams | null>(null);
  const paramsChangedDuringFlight = loading && inflightParamsRef.current !== null &&
    !shallowEqual(params, inflightParamsRef.current);

  // ── Derived active preset — never stored, never stale ──
  const activePresetId = useMemo(
    () => Object.entries(PRESETS).find(([, v]) => shallowEqual(v.params, params))?.[0] ?? null,
    [params]
  );

  // Apply presets from URL params (dashboard quick-launch)
  useEffect(() => {
    const newParams = { ...DEFAULT_PARAMS };
    let hasUrlParams = false;
    if (searchParams.get("temperature")) { newParams.temperature = Number(searchParams.get("temperature")); hasUrlParams = true; }
    if (searchParams.get("ph")) { newParams.ph = Number(searchParams.get("ph")); hasUrlParams = true; }
    if (searchParams.get("oxygen_level")) { newParams.oxygen = searchParams.get("oxygen_level")!; hasUrlParams = true; }
    if (searchParams.get("carbon_source")) { newParams.carbon = searchParams.get("carbon_source")!; hasUrlParams = true; }
    if (searchParams.get("nitrogen_source")) { newParams.nitrogen = searchParams.get("nitrogen_source")!; hasUrlParams = true; }
    if (hasUrlParams) setParams(newParams);
  }, [searchParams]);

  // ── Individual field setters — each patches ONLY its own field ──
  const setTemperature = (v: number) => setParams(p => ({ ...p, temperature: v }));
  const setPh = (v: number) => setParams(p => ({ ...p, ph: v }));
  const setOxygen = (v: string) => setParams(p => ({ ...p, oxygen: v }));
  const setCarbon = (v: string) => setParams(p => ({ ...p, carbon: v }));
  const setNitrogen = (v: string) => setParams(p => ({ ...p, nitrogen: v }));

  // ── Preset = one deliberate action that replaces the whole object ──
  const applyPreset = (id: string) => setParams(PRESETS[id].params);

  const validateSequence = (seq: string) => {
    if (!seq) { setSeqError(null); return; }
    const invalid = seq.replace(/[ATCGNatcgn\s]/g, "");
    if (invalid.length > 0) {
      setSeqError(`Invalid characters: ${Array.from(new Set(invalid)).slice(0, 5).join(", ")}`);
    } else {
      setSeqError(null);
    }
  };

  const resetForm = () => {
    setSequence("");
    setParams(DEFAULT_PARAMS);
    setResult(null);
    setError(null);
    setSeqError(null);
  };

  const runSimulation = async () => {
    if (seqError) return;
    setLoading(true);
    setError(null);
    setResult(null);

    // Snapshot the params at submission time — changing sliders during flight won't affect this request
    const submittedParams = { ...params };
    inflightParamsRef.current = submittedParams;

    try {
      const res = await fetch(`${API}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: runName.trim() || null,
          raw_sequence: sequence || null,
          temperature: submittedParams.temperature,
          ph: submittedParams.ph,
          oxygen_level: submittedParams.oxygen,
          carbon_source: submittedParams.carbon,
          nitrogen_source: submittedParams.nitrogen,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Simulation failed");
      }
      setResult(await res.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
      inflightParamsRef.current = null;
    }
  };

  // ── Chart data ──
  const growthGaugeData = result?.growth_rate != null
    ? [{ name: "Growth", value: Math.min(result.growth_rate / 1.0 * 100, 100), fill: result.growth_rate > 0.5 ? "#3ef2ff" : result.growth_rate > 0.1 ? "#ffcf66" : "#ff5a36" }]
    : [];

  const pathwayChartData = result?.active_pathways?.slice(0, 6).map((p, i) => ({
    name: p.length > 20 ? p.substring(0, 18) + "…" : p,
    fullName: p,
    value: 6 - i,
  })) || [];

  // B1: growth_state is computed server-side against the reference growth
  // rate. This fallback mirrors the same thresholds. Keep REFERENCE_GROWTH_RATE
  // in sync with backend/app/services/simulation_runner.py.
  const statusLabel = result?.growth_state
    ?? (result == null || result.growth_rate == null || result.growth_rate < 0.01 ? "not-viable"
      : result.growth_rate >= REFERENCE_GROWTH_RATE * 0.9 ? "optimal"
      : result.growth_rate >= REFERENCE_GROWTH_RATE * 0.5 ? "slowed" : "stressed");

  return (
    <div className="max-w-6xl page-enter">

      {/* ═══ Page header ═══ */}
      <h1 className="text-3xl font-semibold text-[#eaffff] mb-1 glow-text">Run Simulation</h1>
      <p className="text-sm text-[#8cc3d4] mb-6">Configure environment and predict E. coli metabolic behavior</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ═══════════════════════════════════════════════════════════
            LEFT COLUMN — Zone A: Configure (DNA) + Zone B: Preview
        ═══════════════════════════════════════════════════════════ */}
        <div className="lg:col-span-2 space-y-4">

          {/* ── Zone A label ── */}
          <div className="flex items-center gap-3 mb-1">
            <span className="text-xs font-medium uppercase tracking-widest text-[#5c8494]">Configure</span>
            <div className="flex-1 h-px bg-white/[0.07]" />
          </div>

          {/* Optional run name */}
          <Card className="p-6">
            <label htmlFor="run-name" className="block text-lg font-semibold text-[#d9f7ff] mb-1">
              Run Name <span className="text-sm font-normal text-[#5c8494]">(optional)</span>
            </label>
            <p className="text-xs text-[#5c8494] mb-3">
              Shown on the Results page. Leave empty and the run is titled from its conditions, e.g. &quot;Glucose · aerobic · 37 °C · pH 7&quot;.
            </p>
            <input
              id="run-name"
              value={runName}
              maxLength={120}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="e.g. Heat shock test"
              className="w-full px-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 focus:shadow-[0_0_0_1px_rgba(62,242,255,0.25)] transition-colors"
            />
          </Card>

          {/* DNA Input */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-[#d9f7ff] mb-3">DNA Sequence Input</h2>
            <textarea
              value={sequence}
              onChange={(e) => { setSequence(e.target.value); validateSequence(e.target.value); }}
              placeholder="Paste DNA sequence here (ATCG only)... Leave empty for default E. coli genes."
              className={`w-full h-40 p-4 rounded-xl bg-[#01070c]/60 border text-[#7dffef] font-mono-readout text-sm placeholder-[#5c8494] focus:outline-none resize-none transition-colors ${
                seqError
                  ? "border-[#ff5a36]/60 focus:border-[#ff5a36]"
                  : "border-white/10 focus:border-[#3ef2ff]/60 focus:shadow-[0_0_0_1px_rgba(62,242,255,0.25)]"
              }`}
            />
            <div className="flex justify-between mt-2">
              <div className="text-xs text-[#5c8494] font-mono-readout">
                {sequence.length > 0 ? `${sequence.replace(/\s/g, "").length} bp` : "0 bp"} | GC:{" "}
                {sequence.length > 0
                  ? (((sequence.match(/[GCgc]/g)?.length || 0) / sequence.replace(/\s/g, "").length) * 100).toFixed(1)
                  : "0.0"}%
              </div>
              {seqError && <div className="text-xs text-[#ff8b6e]">{seqError}</div>}
            </div>
          </Card>

          {/* Error */}
          {error && <ErrorBanner message={error} onRetry={runSimulation} />}

          {/* Launch sequence loading */}
          {loading && (
            <Card className="p-6">
              <LaunchSequence
                conditions={{ temperature: inflightParamsRef.current?.temperature ?? params.temperature, oxygen: inflightParamsRef.current?.oxygen ?? params.oxygen, carbon: inflightParamsRef.current?.carbon ?? params.carbon, nitrogen: inflightParamsRef.current?.nitrogen ?? params.nitrogen }}
              />
            </Card>
          )}

          {/* ── Zone B: Result Preview ── */}
          {result && !loading && (
            <div className="space-y-4">

              {/* Zone B label */}
              <div className="flex items-center gap-3 mt-2">
                <span className="text-xs font-medium uppercase tracking-widest text-[#5c8494]">Result Preview</span>
                <div className="flex-1 h-px bg-white/[0.07]" />
              </div>

              {/* Hero growth rate + metadata header */}
              <Card className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xs text-[#8cc3d4] mb-1">growth rate</div>
                    <div className="text-5xl font-light text-[#eaffff] font-mono-readout glow-text leading-none">
                      {result.growth_rate != null ? result.growth_rate.toFixed(3) : "—"}<span className="text-lg text-[#5c8494] ml-2">{GROWTH_UNIT}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <div className={`h-2 w-2 rounded-full ${result.growth_rate != null && result.growth_rate > 0.5 ? 'bg-[#3ef2ff] shadow-[0_0_8px_rgba(62,242,255,0.6)]' : 'bg-[#ffcf66]'}`} />
                      <span className="text-sm text-[#8cc3d4]">{growthStateLabel(statusLabel)}{percentOfReference(result.growth_rate) != null && ` · ${percentOfReference(result.growth_rate)}% of reference`}</span>
                    </div>
                  </div>
                  {/* Run metadata — moved here from page footer */}
                  <div className="text-right text-xs text-[#5c8494] font-mono-readout space-y-0.5">
                    <div>{result.run_number != null ? `Run #${result.run_number}` : `Task: ${result.task_id?.slice(0, 8)}`}</div>
                    {result.name && <div className="text-[#8cc3d4] max-w-[14rem] truncate">{result.name}</div>}
                    <div>Model: {result.model_versions?.predictor || "iML1515"}</div>
                  </div>
                </div>
              </Card>

              {/* Secondary metrics — Growth Rate REMOVED (already in hero) */}
              <div className="grid grid-cols-3 gap-3">
                <MetricCard
                  label="Doubling Time"
                  value={result.doubling_time != null ? `${result.doubling_time.toFixed(2)} h` : "N/A"}
                  color="blue"
                  icon={Timer}
                />
                <MetricCard
                  label="Viability"
                  value={result.viability_score != null ? `${(result.viability_score * 100).toFixed(0)}%` : "N/A"}
                  color={result.viability_score != null && result.viability_score > 0.5 ? "green" : "red"}
                  icon={HeartPulse}
                />
                <MetricCard
                  label="Compute Time"
                  value={result.compute_time_ms != null ? `${result.compute_time_ms} ms` : "N/A"}
                  color="gray"
                  icon={Zap}
                />
              </div>

              {/* Growth Rate Gauge + Top 6 Pathways side by side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Growth gauge — value displayed once, inside the arc */}
                {growthGaugeData.length > 0 && (
                  <Card className="p-6">
                    <h3 className="text-sm font-semibold text-[#d9f7ff] mb-3">Growth Rate Gauge</h3>
                    <ResponsiveContainer width="100%" height={160}>
                      <RadialBarChart cx="50%" cy="85%" innerRadius="70%" outerRadius="100%" startAngle={180} endAngle={0} data={growthGaugeData}>
                        <RadialBar dataKey="value" cornerRadius={10} background={{ fill: "rgba(255,255,255,0.06)" }}>
                          {growthGaugeData.map((entry, i) => (
                            <Cell key={i} fill={entry.fill} />
                          ))}
                        </RadialBar>
                      </RadialBarChart>
                    </ResponsiveContainer>
                    <div className="text-center mt-2">
                      <div className="text-3xl font-light text-[#eaffff] font-mono-readout glow-text">{result.growth_rate != null ? result.growth_rate.toFixed(3) : "—"} {GROWTH_UNIT}</div>
                      <div className="text-xs text-[#5c8494] mt-1">of ~0.88 theoretical max</div>
                    </div>
                  </Card>
                )}

                {/* Top 6 pathways bar chart */}
                {pathwayChartData.length > 0 && (
                  <Card className="p-6">
                    <h3 className="text-sm font-semibold text-[#d9f7ff] mb-3">Top Active Pathways</h3>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={pathwayChartData} layout="vertical" margin={{ left: 0, right: 10, top: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" horizontal={false} />
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" tick={{ fill: "#8cc3d4", fontSize: 10 }} width={150} interval={0} />
                        <Tooltip
                          contentStyle={{ background: "#031722", border: "1px solid rgba(62,242,255,0.25)", borderRadius: 12, fontSize: 12 }}
                          labelStyle={{ color: "#3ef2ff" }}
                          formatter={() => null}
                          content={({ payload }) => {
                            if (!payload || !payload[0]) return null;
                            const item = payload[0].payload as { fullName: string; value: number };
                            return (
                              <div style={{ background: "#031722", border: "1px solid rgba(62,242,255,0.25)", borderRadius: 12, fontSize: 12, padding: "8px 12px", boxShadow: "0 8px 28px -10px rgba(0,0,0,0.9)" }}>
                                <div style={{ color: "#7dffef" }}>{item.fullName}</div>
                              </div>
                            );
                          }}
                        />
                        <Bar dataKey="value" fill="#3ef2ff" radius={[0, 4, 4, 0]} barSize={16} />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                )}
              </div>

              {/* CTA — single, at the bottom, nothing below it */}
              <div className="flex justify-center pt-2">
                <a href={`/results/${result.task_id}`}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#3ef2ff]/10 text-[#3ef2ff] border border-[#3ef2ff]/20 hover:bg-[#3ef2ff]/20 hover:border-[#3ef2ff]/40 transition-all text-sm font-medium shadow-[0_0_20px_-6px_rgba(62,242,255,0.3)]">
                  Open full result →
                </a>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && !error && (
            <Card className="p-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#3ef2ff]/10 ring-1 ring-[#3ef2ff]/25 shadow-[0_0_24px_-4px_rgba(62,242,255,0.35)]">
                <FlaskConical className="h-8 w-8 text-[#7dffef]" strokeWidth={1.5} aria-hidden="true" />
              </div>
              <p className="text-[#8cc3d4] text-sm max-w-md mx-auto leading-relaxed">
                Configure environmental conditions and click <strong className="text-[#7dffef] font-medium">Run Simulation</strong> to
                predict gene expression and metabolic flux.
              </p>
            </Card>
          )}
        </div>

        {/* ═══════════════════════════════════════════════════════════
            RIGHT COLUMN — Sticky: Presets + Environment + Run
        ═══════════════════════════════════════════════════════════ */}
        <div className="lg:sticky lg:top-20 lg:self-start space-y-4">

          {/* Quick Presets */}
          <Card className="p-5">
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="text-sm font-semibold text-[#d9f7ff]">Quick Presets</h2>
              {activePresetId === null && (
                <span className="text-[10px] font-medium uppercase tracking-wider text-[#ffcf66] bg-[#ffcf66]/10 px-2 py-0.5 rounded-full border border-[#ffcf66]/20">
                  Custom
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(PRESETS).map(([id, preset]) => (
                <button
                  key={id}
                  onClick={() => applyPreset(id)}
                  className={`flex-1 min-w-[90px] px-3 py-2 rounded-full text-xs font-medium border transition-all ${
                    activePresetId === id
                      ? "bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40 shadow-[0_0_12px_-4px_rgba(62,242,255,0.35)]"
                      : "bg-white/[0.04] text-[#8cc3d4] hover:bg-[#3ef2ff]/10 hover:text-[#7dffef] hover:border-[#3ef2ff]/35 border-white/10"
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </Card>

          {/* Environment Parameters */}
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-[#d9f7ff] mb-4">Environment Parameters</h2>
            <div className="space-y-5">
              <SliderControl label="Temperature" value={params.temperature} onChange={setTemperature} min={20} max={50} unit="°C" />
              <SliderControl label="pH" value={params.ph} onChange={setPh} min={4} max={9} step={0.1} unit="" />
              <SelectControl label="Oxygen" value={params.oxygen} onChange={setOxygen} options={OXYGEN_OPTIONS} />
              <SelectControl label="Carbon Source" value={params.carbon} onChange={setCarbon} options={CARBON_OPTIONS} />
              <SelectControl label="Nitrogen Source" value={params.nitrogen} onChange={setNitrogen} options={NITROGEN_OPTIONS} />
            </div>

            {/* In-flight change hint */}
            {paramsChangedDuringFlight && (
              <div className="mt-3 text-[10px] text-[#ffcf66] bg-[#ffcf66]/[0.06] border border-[#ffcf66]/15 rounded-lg px-3 py-1.5 text-center">
                Changes will apply to the next run
              </div>
            )}

            <button
              className={`w-full mt-6 py-3 rounded-full font-semibold transition-all border ${
                loading || !!seqError
                  ? "bg-white/[0.04] text-[#5c8494] border-white/10 cursor-not-allowed"
                  : "bg-[#3ef2ff]/15 hover:bg-[#3ef2ff]/25 text-[#7dffef] border-[#3ef2ff]/40 shadow-[0_0_24px_-6px_rgba(62,242,255,0.5)] hover:shadow-[0_0_32px_-6px_rgba(62,242,255,0.7)]"
              }`}
              onClick={runSimulation}
              disabled={loading || !!seqError}
            >
              {loading ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Running…
                </span>
              ) : (
                <span className="inline-flex items-center justify-center gap-2">
                  <Play className="h-4 w-4 fill-current" aria-hidden="true" />
                  Run Simulation
                </span>
              )}
            </button>

            <button
              onClick={resetForm}
              className="w-full mt-2 py-2 rounded-full text-xs text-[#5c8494] hover:text-[#8cc3d4] hover:bg-white/[0.04] transition-colors"
            >
              Reset to defaults
            </button>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ─── Sub-components ──────────────────────────────────────── */

function SliderControl({ label, value, onChange, min, max, step = 1, unit }: {
  label: string; value: number; onChange: (v: number) => void; min: number; max: number; step?: number; unit: string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-[#8cc3d4]">{label}</span>
        <span className="text-[#7dffef] font-mono-readout text-sm">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full cursor-pointer"
        style={{
          background: `linear-gradient(to right, rgba(62,242,255,0.4) 0%, rgba(62,242,255,0.4) ${pct}%, rgba(255,255,255,0.08) ${pct}%, rgba(255,255,255,0.08) 100%)`,
          borderRadius: '999px',
          height: '4px',
        }}
      />
    </div>
  );
}

function SelectControl({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <div>
      <label className="text-sm text-[#8cc3d4] block mb-1.5">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full p-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm focus:border-[#3ef2ff]/60 focus:outline-none transition-colors">
        {options.map((opt) => (
          <option key={opt} value={opt} className="bg-[#031722] text-[#eaffff]">{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
        ))}
      </select>
    </div>
  );
}