"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, StatusBadge } from "@/components/ui/card";
import MicroscopeHero from "@/components/microscope-hero";
import { PRESETS, GENESIS_STATS, presetToSearchParams } from "@/lib/presets";
import { Dna, FlaskConical, ChartColumn, Blocks, BookOpen } from "lucide-react";
import { runLabel, simTitle, formatDateTime, formatGrowth } from "@/lib/sim-format";

const API = "http://localhost:8000/api/v1";

/* ─── Types ───────────────────────────────────────────────── */

interface RecentSim {
  id: string;
  run_number: number | null;
  name: string | null;
  status: string;
  temperature: number;
  ph: number;
  oxygen_level: string;
  carbon_source: string;
  growth_rate: number | null;
  viability_score: number | null;
  created_at: string | null;
}

/* ─── Home presets (subset of the shared PRESETS) ─────────── */

const HOME_PRESET_IDS = ["reference", "anaerobic", "heatShock", "glycerolFeed"] as const;

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
      const res = await fetch(`${API}/results?limit=2`);
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
      {/* ═══ HERO — Microscope Field ═══ */}
      <MicroscopeHero apiStatus={apiStatus} />

      {/* ═══ HOW IT WORKS (unchanged) ═══ */}
      <div className="mb-10">
        <h2 className="text-xs font-semibold text-[#5c8494] uppercase tracking-[0.15em] mb-5">
          How it works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="p-5 relative overflow-hidden">
            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[#3ef2ff]/10 ring-1 ring-[#3ef2ff]/20">
              <Dna className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <h3 className="text-sm font-semibold text-[#eaffff] mb-1">1 — Design</h3>
            <p className="text-xs text-[#8cc3d4] leading-relaxed">
              Input a DNA construct or pick from {GENESIS_STATS.parts.value} characterized parts (promoters, RBS, CDS, terminators).
            </p>
            <div className="absolute -bottom-1 -right-1 text-[64px] opacity-[0.03] leading-none">1</div>
          </Card>
          <Card className="p-5 relative overflow-hidden">
            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[#3ef2ff]/10 ring-1 ring-[#3ef2ff]/20">
              <FlaskConical className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <h3 className="text-sm font-semibold text-[#eaffff] mb-1">2 — Simulate</h3>
            <p className="text-xs text-[#8cc3d4] leading-relaxed">
              Set temperature, pH, oxygen, and carbon source. The FBA solver predicts growth and flux through 40+ pathways.
            </p>
            <div className="absolute -bottom-1 -right-1 text-[64px] opacity-[0.03] leading-none">2</div>
          </Card>
          <Card className="p-5 relative overflow-hidden">
            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[#3ef2ff]/10 ring-1 ring-[#3ef2ff]/20">
              <ChartColumn className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <h3 className="text-sm font-semibold text-[#eaffff] mb-1">3 — Analyze</h3>
            <p className="text-xs text-[#8cc3d4] leading-relaxed">
              Compare conditions side by side, see pathway activation, export results as markdown lab reports.
            </p>
            <div className="absolute -bottom-1 -right-1 text-[64px] opacity-[0.03] leading-none">3</div>
          </Card>
        </div>
      </div>

      {/* ═══ TRY IT NOW (shared PRESETS source) ═══ */}
      <div className="mb-10">
        <h2 className="text-xs font-semibold text-[#5c8494] uppercase tracking-[0.15em] mb-5">
          Try it now
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {HOME_PRESET_IDS.map((id) => {
            const preset = PRESETS[id];
            const p = preset.params;
            const desc = `${p.temperature}°C · ${p.carbon} · ${p.oxygen === "anaerobic" ? "no O₂" : p.oxygen}`;
            return (
              <Link key={id} href={`/simulate?${presetToSearchParams(id)}`}>
                <Card hover className="p-4 h-full">
                  <div className="text-sm font-semibold text-[#eaffff] mb-0.5">
                    {preset.label}
                  </div>
                  <div className="text-[11px] text-[#5c8494] font-mono-readout">{desc}</div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ═══ BY THE NUMBERS (all cyan — single color rule) ═══ */}
      <div className="mb-10">
        <h2 className="text-xs font-semibold text-[#5c8494] uppercase tracking-[0.15em] mb-5">
          By the numbers
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.values(GENESIS_STATS).map((stat) => (
            <Card key={stat.label} className="p-4 text-center">
              <div className="text-2xl font-semibold text-[#3ef2ff] font-mono-readout glow-text mb-1">
                {stat.value}
              </div>
              <div className="text-[10px] text-[#5c8494] uppercase tracking-wider">
                {stat.label}
              </div>
              <div className="text-[10px] text-[#5c8494]">{stat.source}</div>
            </Card>
          ))}
        </div>
      </div>

      {/* ═══ EXPLORE (all 4 areas, equal treatment) ═══ */}
      <div className="mb-10">
        <h2 className="text-xs font-semibold text-[#5c8494] uppercase tracking-[0.15em] mb-5">
          Explore
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link href="/simulate">
            <Card hover className="p-5 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-2">
                <FlaskConical className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
                <h3 className="text-[15px] font-semibold text-[#eaffff]">Simulate</h3>
              </div>
              <p className="text-xs text-[#8cc3d4] leading-relaxed flex-1">
                Set environment parameters and predict E. coli growth, flux, and gene expression.
              </p>
              <div className="text-[10px] text-[#5c8494] pt-2">Open →</div>
            </Card>
          </Link>

          {/* Results card — with live 1–2 row preview */}
          <Link href="/results">
            <Card hover className="p-5 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-2">
                <ChartColumn className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
                <h3 className="text-[15px] font-semibold text-[#eaffff]">Results</h3>
              </div>
              <div className="flex-1">
                {recentLoading ? (
                  <p className="text-xs text-[#5c8494] italic">Loading recent simulations…</p>
                ) : recentError ? (
                  <p className="text-xs text-[#5c8494] italic">Could not load recent results.</p>
                ) : recentSims.length === 0 ? (
                  <p className="text-xs text-[#8cc3d4] leading-relaxed">
                    No simulations yet — <span className="text-[#7dffef]">run your first one</span> to see results here.
                  </p>
                ) : (
                  <div className="space-y-1.5 mt-1">
                    {recentSims.slice(0, 2).map((sim) => (
                      <div
                        key={sim.id}
                        className="flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <StatusBadge status={sim.status} />
                          <span className="font-mono-readout text-[#5c8494]">{runLabel(sim)}</span>
                          <span className="text-[#8cc3d4] truncate">{simTitle(sim)}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="font-mono-readout text-[#eaffff]">
                            {formatGrowth(sim.growth_rate)}
                          </span>
                          <span className="text-[#5c8494] hidden sm:inline">
                            {formatDateTime(sim.created_at)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="text-[10px] text-[#5c8494] pt-2">Open →</div>
            </Card>
          </Link>

          <Link href="/parts">
            <Card hover className="p-5 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-2">
                <Blocks className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
                <h3 className="text-[15px] font-semibold text-[#eaffff]">Parts Library</h3>
              </div>
              <p className="text-xs text-[#8cc3d4] leading-relaxed flex-1">
                Browse characterized promoters, RBS, CDS, and terminators. See strengths and sequences from iGEM.
              </p>
              <div className="text-[10px] text-[#5c8494] pt-2">Open →</div>
            </Card>
          </Link>

          <Link href="/knowledge">
            <Card hover className="p-5 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-2">
                <BookOpen className="h-5 w-5 text-[#7dffef]" strokeWidth={1.75} aria-hidden="true" />
                <h3 className="text-[15px] font-semibold text-[#eaffff]">Knowledge Base</h3>
              </div>
              <p className="text-xs text-[#8cc3d4] leading-relaxed flex-1">
                Search {GENESIS_STATS.genes.value} genes, explore TF regulatory networks, and discover 40+ metabolic pathways.
              </p>
              <div className="text-[10px] text-[#5c8494] pt-2">Open →</div>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
}