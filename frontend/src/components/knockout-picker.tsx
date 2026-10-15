"use client";

/*
 * Pick genes to knock out. Searches only genes in the metabolic model,
 * because a knockout works by switching off the reactions a gene's enzyme
 * runs; a gene with no metabolic role has nothing to switch off.
 */

import { useEffect, useRef, useState } from "react";
import { Search, X, Plus } from "lucide-react";
import { KnockoutGene, MAX_KNOCKOUTS, geneLabel, labLabel } from "@/lib/knockout";

const API = "http://localhost:8000/api/v1";

export function KnockoutPicker({ value, onChange }: {
  value: KnockoutGene[];
  onChange: (genes: KnockoutGene[]) => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<KnockoutGene[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  // Search 250 ms after typing stops, so each keystroke is not a request
  useEffect(() => {
    const q = query.trim();
    if (!q) { setItems([]); setTotal(0); return; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch(`${API}/knockout/genes?search=${encodeURIComponent(q)}&limit=8`, { signal: controller.signal })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
        .then((data: { items: KnockoutGene[]; total: number }) => { setItems(data.items); setTotal(data.total); setError(null); })
        .catch((e) => { if (e.name !== "AbortError") setError("Gene search failed. Is the backend running?"); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query]);

  // Close the list when clicking anywhere else
  useEffect(() => {
    const close = (e: MouseEvent) => { if (!boxRef.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const chosen = new Set(value.map((g) => g.locus_tag));
  const full = value.length >= MAX_KNOCKOUTS;

  const add = (gene: KnockoutGene) => {
    if (chosen.has(gene.locus_tag) || full) return;
    onChange([...value, gene]);
    setQuery("");
    setOpen(false);
  };
  const remove = (tag: string) => onChange(value.filter((g) => g.locus_tag !== tag));

  return (
    <div ref={boxRef}>
      {/* Chosen genes */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {value.map((g) => (
            <span key={g.locus_tag} className="inline-flex items-center gap-1.5 rounded-full border border-[#ff8b6e]/35 bg-[#ff5a36]/10 pl-3 pr-1.5 py-1 text-xs text-[#ffd2c4]">
              <span className="font-medium">Δ{geneLabel(g)}</span>
              {g.name && <span className="font-mono-readout text-[#ff8b6e]/70">{g.locus_tag}</span>}
              <button type="button" onClick={() => remove(g.locus_tag)} aria-label={`Remove ${geneLabel(g)}`}
                className="rounded-full p-0.5 text-[#ff8b6e] hover:bg-white/10 hover:text-[#eaffff]">
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search box + results */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#5c8494]" aria-hidden="true" />
        <input
          value={query}
          disabled={full}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder={full ? `Up to ${MAX_KNOCKOUTS} genes per run` : "Search a gene: pflB, b0903, kinase…"}
          aria-label="Search genes to knock out"
          className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 disabled:opacity-50"
        />
        {open && query.trim() && (
          <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-white/10 bg-[#031722] shadow-[0_12px_32px_-8px_rgba(0,0,0,0.9)]">
            {error && <p className="px-4 py-3 text-xs text-[#ff8b6e]">{error}</p>}
            {!error && items.length === 0 && (
              <p className="px-4 py-3 text-xs text-[#5c8494]">No metabolic gene matches &quot;{query.trim()}&quot;. Only genes in the metabolic model can be knocked out.</p>
            )}
            {items.map((g) => {
              const taken = chosen.has(g.locus_tag);
              const lab = labLabel(g.record);
              return (
                <button key={g.locus_tag} type="button" onClick={() => add(g)} disabled={taken}
                  className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-[#3ef2ff]/[0.07] disabled:opacity-40 disabled:hover:bg-transparent border-b border-white/[0.05] last:border-0">
                  <Plus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#3ef2ff]" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      <span className="text-sm text-[#eaffff]">{geneLabel(g)}</span>
                      <span className="font-mono-readout text-[11px] text-[#5c8494]">{g.locus_tag}</span>
                      {lab && (
                        <span className={`ml-auto shrink-0 text-[10px] ${g.record?.lab_essential ? "text-[#ffcf66]" : "text-[#5c8494]"}`}>{lab}</span>
                      )}
                    </span>
                    {g.product && <span className="block truncate text-xs text-[#8cc3d4]">{g.product}</span>}
                  </span>
                </button>
              );
            })}
            {total > items.length && (
              <p className="px-4 py-2 text-[11px] text-[#5c8494] bg-white/[0.02]">Showing {items.length} of {total} — type more to narrow it down.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}