"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import MicroscopeHero from "@/components/microscope-hero";
import { PRESETS, DEFAULT_PARAMS, GENESIS_STATS, presetToSearchParams, EnvParams } from "@/lib/presets";
import { Dna, FlaskConical, ChartColumn, ArrowRight } from "lucide-react";
import { runLabel, simTitle, formatDateTime, formatGrowth, percentOfReference, growthStateLabel } from "@/lib/sim-format";

const API = "http://localhost:8000/api/v1";

/* ─── Types ───────────────────────────────────────────────── */

interface RecentSim {
  id: string;
  run_number: number | null;
  name: string | null;
  status: string;
  growth_state?: string;
  temperature: number;
  ph: number;
  oxygen_level: string;
  carbon_source: string;
  growth_rate: number | null;
  viability_score: number | null;
  created_at: string | null;
}

/* ─── Presets shown on the home page ──────────────────────── */

const HOME_PRESET_IDS = ["reference", "anaerobic", "heatShock", "glycerolFeed"] as const;

/**
 * What a preset changes compared with the reference condition.
 * Showing only the difference is what makes these read as experiments
 * ("42 °C, everything else held") rather than four lists of settings.
 */
function presetDelta(p: EnvParams): { label: string; held: string } {
  const changes: string[] = [];
  if (p.temperature !== DEFAULT_PARAMS.temperature) changes.push(`${p.temperature} °C`);
  if (p.ph !== DEFAULT_PARAMS.ph) changes.push(`pH ${p.ph}`);
  if (p.oxygen !== DEFAULT_PARAMS.oxygen) changes.push(p.oxygen === "anaerobic" ? "no oxygen" : p.oxygen);
  if (p.carbon !== DEFAULT_PARAMS.carbon) changes.push(p.carbon);

  // The reference run changes nothing, so it names its own conditions instead
  if (changes.length === 0) {
    return {
      label: `${p.temperature} °C · ${p.carbon} · ${p.oxygen} · pH ${p.ph}`,
      held: "the control every other run is measured against",
    };
  }
  return { label: changes.join(" · "), held: "everything else held at reference" };
}

/* ─── The three stages, drawn as one connected run ────────── */

const STAGES = [
  {
    Icon: Dna,
    title: "Design",
    body: `Paste a DNA sequence, or start from one of ${GENESIS_STATS.parts.value} characterized iGEM parts — promoters, RBS, coding sequences, terminators.`,
  },
  {
    Icon: FlaskConical,
    title: "Simulate",
    body: "Set temperature, pH, oxygen and carbon source. Flux balance analysis solves the whole network and predicts growth, usually in under two seconds.",
  },
  {
    Icon: ChartColumn,
    title: "Analyze",
    body: "Read the flux map, compare up to four runs side by side, search every gene's predicted expression, and export a report as Markdown or PDF.",
  },
];

/* ─── Page ────────────────────────────────────────────────── */

export default function HomePage() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [recentSims, setRecentSims] = useState<RecentSim[]>([]);
  const [recentLoading, setRecentLoading] = useState(true);
  const [recentError, setRecentError] = useState(false);

  useEffect(() => {
    checkHealth();
    loadRecent();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API}/genes/b0344`, { signal: AbortSignal.timeout(5000) });
      setApiStatus(res.ok ? "online" : "offline");
    } catch {
      setApiStatus("offline");
    }
  };

  const loadRecent = async () => {
    try {
      setRecentLoading(true);
      setRecentError(false);
      const res = await fetch(`${API}/results?limit=4`);
      if (res.ok) {
        const data = await res.json();
        // The list endpoint returns { items, total }; older backends returned a bare array
        setRecentSims(Array.isArray(data) ? data : data.items ?? []);
      } else {
        setRecentError(true);
      }
    } catch {
      setRecentError(true);
    } finally {
      setRecentLoading(false);
    }
  };

  return (
    <div className="max-w-5xl page-enter">
      {/* ═══ Hero: the cell under the microscope ═══ */}
      <MicroscopeHero apiStatus={apiStatus} />

      {/* ═══ What the model is made of ═══════════════════════
          One readout strip rather than four cards: these numbers
          describe the model's scale, which is a single fact. */}
      <div className="mb-16 -mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.02]">
        <dl className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-white/[0.06]">
          {Object.values(GENESIS_STATS).map((stat) => (
            <div key={stat.label} className="px-5 py-4">
              <dt className="text-xs text-[#8cc3d4]">{stat.label}</dt>
              <dd className="mt-1 text-xl font-mono-readout text-[#eaffff]">{stat.value}</dd>
              <dd className="mt-0.5 text-[11px] text-[#5c8494]">{stat.source}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* ═══ The run, start to finish ════════════════════════
          A real sequence, so it is drawn as one track with the
          stages sitting on it — not three separate cards. */}
      <section className="mb-16">
        <h2 className="text-lg font-medium text-[#eaffff] mb-1">One run, start to finish</h2>
        <p className="text-sm text-[#8cc3d4] mb-8">Every simulation follows the same three steps.</p>

        <div className="relative">
          {/* The track: horizontal on desktop, vertical on mobile */}
          <div
            aria-hidden="true"
            className="absolute left-[19px] top-2 bottom-2 w-px bg-gradient-to-b from-[#3ef2ff]/40 via-[#3ef2ff]/20 to-transparent
                       sm:left-0 sm:right-0 sm:top-[19px] sm:bottom-auto sm:h-px sm:w-auto
                       sm:bg-gradient-to-r sm:from-[#3ef2ff]/40 sm:via-[#3ef2ff]/20 sm:to-transparent"
          />
          <ol className="relative grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-6">
            {STAGES.map(({ Icon, title, body }) => (
              <li key={title} className="flex gap-4 sm:block">
                {/* Marker sits on the track */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#3ef2ff]/30 bg-[#031722] sm:mb-4">
                  <Icon className="h-[18px] w-[18px] text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
                </div>
                <div className="sm:pr-4">
                  <h3 className="text-[15px] font-medium text-[#eaffff] mb-1.5">{title}</h3>
                  <p className="text-sm text-[#8cc3d4] leading-relaxed">{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ═══ Start a run ═════════════════════════════════════
          Each card names what it changes, so the set reads as a
          group of experiments against one shared control. */}
      <section className="mb-16">
        <h2 className="text-lg font-medium text-[#eaffff] mb-1">Start from a condition</h2>
        <p className="text-sm text-[#8cc3d4] mb-6">
          Each one opens the simulator ready to run. Reference is the control everything else is measured against.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {HOME_PRESET_IDS.map((id) => {
            const preset = PRESETS[id];
            const delta = presetDelta(preset.params);
            const isReference = id === "reference";
            return (
              <Link
                key={id}
                href={`/simulate?${presetToSearchParams(id)}`}
                className={`group rounded-2xl border p-4 transition-colors ${
                  isReference
                    ? "border-[#3ef2ff]/30 bg-[#3ef2ff]/[0.06] hover:bg-[#3ef2ff]/[0.1]"
                    : "border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.14]"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-[#eaffff]">{preset.label}</span>
                  {isReference && <span className="text-[10px] text-[#7dffef]">control</span>}
                </div>
                <p className="mt-2 font-mono-readout text-[13px] text-[#7dffef]">{delta.label}</p>
                <p className="mt-1 text-[11px] text-[#5c8494] leading-snug">{delta.held}</p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ═══ Recent runs ═════════════════════════════════════
          Live data, and the one thing on this page the navbar
          does not already give you. */}
      <section className="mb-12">
        <div className="flex items-baseline justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-medium text-[#eaffff] mb-1">Recent runs</h2>
            <p className="text-sm text-[#8cc3d4]">Growth shown against the reference condition.</p>
          </div>
          <Link
            href="/results"
            className="shrink-0 inline-flex items-center gap-1.5 text-sm text-[#8cc3d4] hover:text-[#7dffef] transition-colors"
          >
            All results
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>

        {recentLoading ? (
          <p className="text-sm text-[#5c8494] py-6">Loading recent runs…</p>
        ) : recentError ? (
          <p className="text-sm text-[#ff8b6e] py-6">
            Could not reach the engine. Check that the backend is running.
          </p>
        ) : recentSims.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/[0.12] px-6 py-10 text-center">
            <p className="text-sm text-[#8cc3d4] mb-4">No runs yet. The first one takes about two seconds.</p>
            <Link
              href="/simulate"
              className="inline-flex items-center gap-2 rounded-full border border-[#3ef2ff]/40 bg-[#3ef2ff]/15 px-5 py-2 text-sm font-medium text-[#7dffef] transition-colors hover:bg-[#3ef2ff]/25"
            >
              Run the reference condition
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <ul className="rounded-2xl border border-white/[0.07] divide-y divide-white/[0.06] overflow-hidden">
            {recentSims.slice(0, 4).map((sim) => {
              const pct = percentOfReference(sim.growth_rate);
              const state = sim.growth_state ?? sim.status;
              return (
                <li key={sim.id}>
                  <Link
                    href={`/results/${sim.id}`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 transition-colors hover:bg-white/[0.03]"
                  >
                    <span className="font-mono-readout text-xs text-[#5c8494] w-12 shrink-0">{runLabel(sim)}</span>

                    <span className="min-w-0 flex-1 text-sm text-[#eaffff] truncate">{simTitle(sim)}</span>

                    {/* Growth as a bar against the reference, so the number has a scale */}
                    <span className="flex items-center gap-2.5 shrink-0" title={`${growthStateLabel(state)} — ${pct ?? "?"}% of reference`}>
                      <span className="hidden sm:block h-1.5 w-20 rounded-full bg-white/[0.07] overflow-hidden">
                        <span
                          className="block h-full rounded-full bg-[#3ef2ff]"
                          style={{ width: `${Math.min(100, Math.max(2, pct ?? 0))}%` }}
                        />
                      </span>
                      <span className="font-mono-readout text-sm text-[#eaffff] w-20 text-right">
                        {formatGrowth(sim.growth_rate)}
                      </span>
                    </span>

                    <span className="hidden md:block w-40 text-right text-xs text-[#5c8494] shrink-0">
                      {formatDateTime(sim.created_at)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}