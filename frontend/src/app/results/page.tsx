"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Card, StatusBadge } from "@/components/ui/card";
import { EmptyState, ErrorBanner } from "@/components/ui/loading";
import { ChartColumn, Trash2 } from "lucide-react";

const API = "http://localhost:8000/api/v1";

interface SimSummary {
  id: string; status: string; temperature: number; ph: number;
  oxygen_level: string; carbon_source: string; nitrogen_source: string;
  growth_rate: number | null; doubling_time: number | null;
  viability_score: number | null; compute_time_ms: number | null;
  created_at: string | null; completed_at: string | null;
}

type SortKey = "created_at" | "growth_rate" | "viability_score";

export default function ResultsPage() {
  const router = useRouter();
  const [sims, setSims] = useState<SimSummary[]>([]);
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [filterOxygen, setFilterOxygen] = useState<string>("");
  const [filterCarbon, setFilterCarbon] = useState<string>("");
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  useEffect(() => { fetchList(); }, []);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/results?limit=50`);
      if (!res.ok) throw new Error("Failed to fetch");
      setSims(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally { setLoading(false); }
  };

  const deleteSim = async (id: string) => {
    try {
      await fetch(`${API}/results/${id}`, { method: "DELETE" });
      setSims((prev) => prev.filter((s) => s.id !== id));
      setDeleteConfirm(null);
      // Remove from compare set if selected
      setCompareIds((prev) => { const next = new Set(prev); next.delete(id); return next; });
    } catch { /* ignore */ }
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else if (next.size < 4) { next.add(id); }
      return next;
    });
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };
  const sortIcon = (key: SortKey) => sortKey === key ? (sortAsc ? " ↑" : " ↓") : "";

  const oxygenOptions = useMemo(() => Array.from(new Set(sims.map((s) => s.oxygen_level))), [sims]);
  const carbonOptions = useMemo(() => Array.from(new Set(sims.map((s) => s.carbon_source))), [sims]);

  const filtered = useMemo(() => {
    let list = [...sims];
    if (filterOxygen) list = list.filter((s) => s.oxygen_level === filterOxygen);
    if (filterCarbon) list = list.filter((s) => s.carbon_source === filterCarbon);
    list.sort((a, b) => {
      const av = a[sortKey] ?? 0, bv = b[sortKey] ?? 0;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
    return list;
  }, [sims, filterOxygen, filterCarbon, sortKey, sortAsc]);

  const fmt = (d: string | null) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";

  if (error) return <div className="max-w-5xl page-enter"><ErrorBanner message={error} /></div>;

  return (
    <div className="max-w-5xl page-enter">
      <div className="flex items-baseline justify-between mb-1">
        <h1 className="text-3xl font-semibold text-[#eaffff] glow-text">Simulation Results</h1>
        <span className="text-sm text-[#5c8494]">{sims.length} simulations recorded</span>
      </div>
      <p className="text-sm text-[#8cc3d4] mb-6">Click a row to view full detail · Select 2–4 to compare</p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select value={filterOxygen} onChange={(e) => setFilterOxygen(e.target.value)}
          className="px-3 py-1.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm focus:border-[#3ef2ff]/60 focus:outline-none">
          <option value="">All Oxygen</option>
          {oxygenOptions.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select value={filterCarbon} onChange={(e) => setFilterCarbon(e.target.value)}
          className="px-3 py-1.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm focus:border-[#3ef2ff]/60 focus:outline-none">
          <option value="">All Carbon</option>
          {carbonOptions.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Table - FULL WIDTH, no side rail */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                <th className="p-3 w-10"></th>
                <th className="text-left p-3 cursor-pointer hover:text-[#7dffef] select-none font-medium uppercase tracking-wider transition-colors" onClick={() => toggleSort("created_at")}>Date{sortIcon("created_at")}</th>
                <th className="text-left p-3 font-medium uppercase tracking-wider">Conditions</th>
                <th className="text-left p-3 cursor-pointer hover:text-[#7dffef] select-none font-medium uppercase tracking-wider transition-colors" onClick={() => toggleSort("growth_rate")}>Growth{sortIcon("growth_rate")}</th>
                <th className="text-left p-3 cursor-pointer hover:text-[#7dffef] select-none font-medium uppercase tracking-wider transition-colors" onClick={() => toggleSort("viability_score")}>Viability{sortIcon("viability_score")}</th>
                <th className="text-left p-3 font-medium uppercase tracking-wider">Status</th>
                <th className="p-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading && [1,2,3].map((i) => (
                <tr key={i} className="border-b border-white/[0.06] animate-pulse">
                  {Array.from({ length: 7 }).map((_, j) => <td key={j} className="p-3"><div className="h-4 bg-white/[0.06] rounded w-3/4" /></td>)}
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={7}>
                  <EmptyState icon={ChartColumn} title="No simulations found" description="Run your first simulation to see results here." actionLabel="Go to Simulate" actionHref="/simulate" />
                </td></tr>
              )}
              {filtered.map((sim) => (
                <tr key={sim.id}
                  onClick={() => router.push(`/results/${sim.id}`)}
                  className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${compareIds.has(sim.id) ? "bg-[#3ef2ff]/[0.05]" : ""}`}>
                  <td className="p-3" onClick={(e) => { e.stopPropagation(); toggleCompare(sim.id); }}>
                    <input type="checkbox" checked={compareIds.has(sim.id)}
                      readOnly
                      className="accent-[#3ef2ff] cursor-pointer pointer-events-none" />
                  </td>
                  <td className="p-3 text-[#8cc3d4] text-xs">{fmt(sim.created_at)}</td>
                  <td className="p-3 text-xs text-[#8cc3d4]">{sim.temperature}°C · pH {sim.ph} · {sim.oxygen_level} · {sim.carbon_source}</td>
                  <td className="p-3 font-mono-readout text-[#eaffff]">{sim.growth_rate != null ? `${sim.growth_rate} hr⁻¹` : "—"}</td>
                  <td className="p-3">{sim.viability_score != null ? (
                    <span className={sim.viability_score > 0.5 ? "text-[#7dffef]" : "text-[#ff8b6e]"}>{(sim.viability_score * 100).toFixed(0)}%</span>
                  ) : "—"}</td>
                  <td className="p-3"><StatusBadge status={sim.status} /></td>
                  <td className="p-3 text-center" onClick={(e) => { e.stopPropagation(); setDeleteConfirm(sim.id); }}>
                    <button className="text-[#5c8494] hover:text-[#ff5a36] transition-colors text-sm p-1" title="Delete"><Trash2 className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Delete confirmation modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setDeleteConfirm(null)}>
          <div className="p-6 max-w-sm mx-4 bg-white/[0.04] border border-white/[0.07] rounded-2xl backdrop-blur-md" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-[#d9f7ff] mb-2">Delete Simulation?</h3>
            <p className="text-xs text-[#8cc3d4] mb-4">This action cannot be undone. The simulation data will be permanently removed.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteConfirm(null)}
                className="px-4 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors">Cancel</button>
              <button onClick={() => deleteSim(deleteConfirm)}
                className="px-4 py-1.5 text-xs rounded-xl bg-[#ff5a36]/20 text-[#ff5a36] border border-[#ff5a36]/30 hover:bg-[#ff5a36]/30 transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Fixed bottom compare bar */}
      {compareIds.size >= 2 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 px-4 py-3 bg-[#031722]/90 backdrop-blur-md border-t border-[#3ef2ff]/20">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <span className="text-sm text-[#8cc3d4]">
              {compareIds.size} selected {compareIds.size > 4 ? "(max 4)" : ""}
            </span>
            <div className="flex gap-3">
              <button onClick={() => setCompareIds(new Set())}
                className="px-4 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors">Clear</button>
              <button
                onClick={() => router.push(`/results/compare?ids=${Array.from(compareIds).join(",")}`)}
                className="px-5 py-1.5 text-xs rounded-xl bg-[#b98bff]/20 text-[#d4bcff] border border-[#b98bff]/30 hover:bg-[#b98bff]/30 transition-all font-medium">
                Compare Selected ({compareIds.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
