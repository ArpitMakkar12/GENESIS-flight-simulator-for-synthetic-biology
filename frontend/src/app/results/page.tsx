"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Card, StatusBadge } from "@/components/ui/card";
import { EmptyState, ErrorBanner } from "@/components/ui/loading";
import { ChartColumn, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import { runLabel, simTitle, conditionLine, formatDateTime, formatGrowth } from "@/lib/sim-format";
import { MAX_COMPARE } from "@/lib/pathway-diff";

const API = "http://localhost:8000/api/v1";
const PAGE_SIZE = 25;

interface SimSummary {
  id: string; run_number: number | null; name: string | null; status: string;
  temperature: number; ph: number;
  oxygen_level: string; carbon_source: string; nitrogen_source: string;
  growth_rate: number | null; doubling_time: number | null;
  viability_score: number | null; compute_time_ms: number | null;
  created_at: string | null; completed_at: string | null;
}

interface ListResponse { items: SimSummary[]; total: number; limit: number; offset: number }

type SortKey = "run_number" | "created_at" | "growth_rate" | "viability_score";

export default function ResultsPage() {
  const router = useRouter();
  const [sims, setSims] = useState<SimSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0); // 0 = first page
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("run_number");
  const [sortAsc, setSortAsc] = useState(false);
  const [filterOxygen, setFilterOxygen] = useState<string>("");
  const [filterCarbon, setFilterCarbon] = useState<string>("");
  const [oxygenOptions, setOxygenOptions] = useState<string[]>([]);
  const [carbonOptions, setCarbonOptions] = useState<string[]>([]);
  const [reloadKey, setReloadKey] = useState(0); // bump to re-fetch the current page
  // Ids waiting for confirmation: one row (trash icon) or every selected row.
  const [deleteConfirm, setDeleteConfirm] = useState<string[] | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const selectAllRef = useRef<HTMLInputElement>(null);

  // Filter dropdowns list every value ever used, not just the ones on this page
  useEffect(() => {
    fetch(`${API}/results/filters`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setOxygenOptions(d.oxygen_levels ?? []);
        setCarbonOptions(d.carbon_sources ?? []);
      })
      .catch(() => {});
  }, [reloadKey]);

  // The server does the filtering, sorting and paging, so they cover every simulation
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
      sort: sortKey,
      order: sortAsc ? "asc" : "desc",
    });
    if (filterOxygen) params.set("oxygen", filterOxygen);
    if (filterCarbon) params.set("carbon", filterCarbon);

    setLoading(true);
    fetch(`${API}/results?${params}`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to fetch");
        const data = (await res.json()) as ListResponse;
        // A delete can empty the last page: step back one page instead of showing nothing
        if (data.items.length === 0 && page > 0 && data.total > 0) {
          setPage(Math.max(0, Math.ceil(data.total / PAGE_SIZE) - 1));
          return;
        }
        setSims(data.items);
        setTotal(data.total);
        setError(null);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return; // a newer request replaced this one
        setError(e instanceof Error ? e.message : "Unknown error");
        setLoading(false);
      });
    return () => controller.abort();
  }, [page, sortKey, sortAsc, filterOxygen, filterCarbon, reloadKey]);

  // One request for any number of rows. Afterwards the page is re-fetched,
  // so rows from the next page slide up to fill the gap.
  const deleteSims = async (ids: string[]) => {
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API}/results/bulk-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      const { deleted } = (await res.json()) as { deleted: string[] };
      const gone = new Set(deleted);
      setSelectedIds((prev) => new Set(Array.from(prev).filter((id) => !gone.has(id))));
      setDeleteConfirm(null);
      setReloadKey((k) => k + 1);
    } catch (e: unknown) {
      setDeleteError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  const closeConfirm = () => { if (!deleting) { setDeleteConfirm(null); setDeleteError(null); } };

  // No cap on selection: compare needs 2 to MAX_COMPARE (4), delete takes any number.
  // Selection is kept while you move between pages.
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
    setPage(0);
  };
  const sortIcon = (key: SortKey) => sortKey === key ? (sortAsc ? " ↑" : " ↓") : "";

  // Header checkbox acts on the rows on this page.
  const allVisibleSelected = sims.length > 0 && sims.every((s) => selectedIds.has(s.id));
  const someVisibleSelected = sims.some((s) => selectedIds.has(s.id));
  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = someVisibleSelected && !allVisibleSelected;
  }, [someVisibleSelected, allVisibleSelected]);

  const toggleSelectAllVisible = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) sims.forEach((s) => next.delete(s.id));
      else sims.forEach((s) => next.add(s.id));
      return next;
    });
  };

  const canCompare = selectedIds.size >= 2 && selectedIds.size <= MAX_COMPARE;
  const filtering = !!(filterOxygen || filterCarbon);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const firstRow = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const lastRow = Math.min(total, (page + 1) * PAGE_SIZE);

  const thSort = "text-left p-3 cursor-pointer hover:text-[#7dffef] select-none font-medium uppercase tracking-wider transition-colors";
  const selectCls = "px-3 py-1.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm focus:border-[#3ef2ff]/60 focus:outline-none";
  const pageBtn = "inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

  if (error) return <div className="max-w-5xl page-enter"><ErrorBanner message={error} /></div>;

  return (
    <div className="max-w-5xl page-enter pb-20">
      <div className="flex items-baseline justify-between mb-1">
        <h1 className="text-3xl font-semibold text-[#eaffff] glow-text">Simulation Results</h1>
        <span className="text-sm text-[#5c8494]">
          {total} {filtering ? "matching" : total === 1 ? "simulation" : "simulations"}
        </span>
      </div>
      <p className="text-sm text-[#8cc3d4] mb-6">Click a row to view full detail · Select 2–{MAX_COMPARE} to compare, or any number to delete</p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select value={filterOxygen} onChange={(e) => { setFilterOxygen(e.target.value); setPage(0); }} className={selectCls} aria-label="Filter by oxygen">
          <option value="">All Oxygen</option>
          {oxygenOptions.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select value={filterCarbon} onChange={(e) => { setFilterCarbon(e.target.value); setPage(0); }} className={selectCls} aria-label="Filter by carbon source">
          <option value="">All Carbon</option>
          {carbonOptions.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {filtering && (
          <button onClick={() => { setFilterOxygen(""); setFilterCarbon(""); setPage(0); }}
            className="px-3 py-1.5 text-xs text-[#8cc3d4] hover:text-[#eaffff] transition-colors">Clear filters</button>
        )}
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                <th className="p-3 w-10">
                  <input ref={selectAllRef} type="checkbox" aria-label="Select all simulations on this page"
                    checked={allVisibleSelected} onChange={toggleSelectAllVisible}
                    disabled={loading || sims.length === 0}
                    className="accent-[#3ef2ff] cursor-pointer disabled:cursor-default" />
                </th>
                <th className={`${thSort} w-16`} onClick={() => toggleSort("run_number")}>#{sortIcon("run_number")}</th>
                <th className="text-left p-3 font-medium uppercase tracking-wider">Simulation</th>
                <th className={thSort} onClick={() => toggleSort("created_at")}>Date{sortIcon("created_at")}</th>
                <th className={thSort} onClick={() => toggleSort("growth_rate")}>Growth{sortIcon("growth_rate")}</th>
                <th className={thSort} onClick={() => toggleSort("viability_score")}>Viability{sortIcon("viability_score")}</th>
                <th className="text-left p-3 font-medium uppercase tracking-wider" title="Growth compared with the reference run: glucose · aerobic · 37 °C · pH 7">Vs reference</th>
                <th className="p-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading && sims.length === 0 && [1, 2, 3].map((i) => (
                <tr key={i} className="border-b border-white/[0.06] animate-pulse">
                  {Array.from({ length: 8 }).map((_, j) => <td key={j} className="p-3"><div className="h-4 bg-white/[0.06] rounded w-3/4" /></td>)}
                </tr>
              ))}
              {!loading && sims.length === 0 && (
                <tr><td colSpan={8}>
                  {filtering ? (
                    <p className="p-8 text-center text-sm text-[#8cc3d4]">No simulations match these filters.</p>
                  ) : (
                    <EmptyState icon={ChartColumn} title="No simulations yet" description="Run your first simulation to see results here." actionLabel="Go to Simulate" actionHref="/simulate" />
                  )}
                </td></tr>
              )}
              {sims.map((sim) => (
                <tr key={sim.id}
                  onClick={() => router.push(`/results/${sim.id}`)}
                  className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${selectedIds.has(sim.id) ? "bg-[#3ef2ff]/[0.05]" : ""} ${loading ? "opacity-60" : ""}`}>
                  <td className="p-3" onClick={(e) => { e.stopPropagation(); toggleSelect(sim.id); }}>
                    <input type="checkbox" checked={selectedIds.has(sim.id)} readOnly
                      aria-label={`Select ${runLabel(sim)}`}
                      className="accent-[#3ef2ff] cursor-pointer pointer-events-none" />
                  </td>
                  <td className="p-3 font-mono-readout text-[#5c8494]">{runLabel(sim)}</td>
                  <td className="p-3">
                    <div className="text-[#eaffff]">{simTitle(sim)}</div>
                    {sim.name && <div className="text-xs text-[#5c8494] mt-0.5">{conditionLine(sim)}</div>}
                  </td>
                  <td className="p-3 text-[#8cc3d4] text-xs whitespace-nowrap">{formatDateTime(sim.created_at)}</td>
                  <td className="p-3 font-mono-readout text-[#eaffff] whitespace-nowrap">{formatGrowth(sim.growth_rate)}</td>
                  <td className="p-3">{sim.viability_score != null ? (
                    <span className={sim.viability_score > 0.5 ? "text-[#7dffef]" : "text-[#ff8b6e]"}>{(sim.viability_score * 100).toFixed(0)}%</span>
                  ) : "—"}</td>
                  <td className="p-3"><StatusBadge status={sim.status} growthRate={sim.growth_rate} /></td>
                  <td className="p-3 text-center" onClick={(e) => { e.stopPropagation(); setDeleteConfirm([sim.id]); }}>
                    <button className="text-[#5c8494] hover:text-[#ff5a36] transition-colors text-sm p-1" title="Delete" aria-label={`Delete ${runLabel(sim)}`}>
                      <Trash2 className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-white/[0.06] text-xs text-[#8cc3d4]">
            <span>Showing {firstRow}–{lastRow} of {total}</span>
            <div className="flex items-center gap-2">
              <button className={pageBtn} disabled={page === 0 || loading} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
              </button>
              <span className="px-1 text-[#5c8494]">Page {page + 1} of {pageCount}</span>
              <button className={pageBtn} disabled={page + 1 >= pageCount || loading} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Delete confirmation modal: one row or many */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={closeConfirm}>
          <div className="p-6 max-w-sm mx-4 bg-[#031722] border border-white/[0.07] rounded-2xl" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-[#d9f7ff] mb-2">
              {deleteConfirm.length === 1 ? "Delete Simulation?" : `Delete ${deleteConfirm.length} Simulations?`}
            </h3>
            <p className="text-xs text-[#8cc3d4] mb-4">This action cannot be undone. The simulation data will be permanently removed.</p>
            {deleteError && <p className="text-xs text-[#ff8b6e] mb-3">{deleteError}. Nothing was removed; try again.</p>}
            <div className="flex gap-2 justify-end">
              <button onClick={closeConfirm} disabled={deleting}
                className="px-4 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors disabled:opacity-50">Cancel</button>
              <button onClick={() => deleteSims(deleteConfirm)} disabled={deleting}
                className="px-4 py-1.5 text-xs rounded-xl bg-[#ff5a36]/20 text-[#ff5a36] border border-[#ff5a36]/30 hover:bg-[#ff5a36]/30 transition-colors disabled:opacity-50">
                {deleting ? "Deleting…" : deleteConfirm.length === 1 ? "Delete" : `Delete ${deleteConfirm.length}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fixed bottom action bar: appears as soon as one row is selected */}
      {selectedIds.size >= 1 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 px-4 py-3 bg-[#031722]/90 backdrop-blur-md border-t border-[#3ef2ff]/20">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <span className="text-sm text-[#8cc3d4]">
              {selectedIds.size} selected
              {!canCompare && <span className="text-xs text-[#5c8494]"> · compare needs 2–{MAX_COMPARE}</span>}
            </span>
            <div className="flex gap-3">
              <button onClick={() => setSelectedIds(new Set())}
                className="px-4 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors">Clear</button>
              <button onClick={() => setDeleteConfirm(Array.from(selectedIds))}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs rounded-xl bg-[#ff5a36]/15 text-[#ff8b6e] border border-[#ff5a36]/30 hover:bg-[#ff5a36]/25 transition-colors font-medium">
                <Trash2 className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
                Delete ({selectedIds.size})
              </button>
              <button
                onClick={() => router.push(`/results/compare?ids=${Array.from(selectedIds).join(",")}`)}
                disabled={!canCompare}
                className="px-5 py-1.5 text-xs rounded-xl bg-[#b98bff]/20 text-[#d4bcff] border border-[#b98bff]/30 hover:bg-[#b98bff]/30 transition-all font-medium disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-[#b98bff]/20">
                Compare Selected ({selectedIds.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}