"use client";

import { useEffect, useRef, useState } from "react";
import { Search, X, Dna, LoaderCircle } from "lucide-react";
import { Card } from "@/components/ui/card";

const API = "http://localhost:8000/api/v1";
const FIRST_PAGE = 10;   // rows shown before "Show more"
const MORE_PAGE = 25;    // rows added per "Show more" click

export interface GeneRow {
  gene_id: string;
  gene_name?: string | null;
  relative_expression: number;
  confidence: number;
  prediction_source?: string | null;
  source?: string | null;          // legacy field name in older runs
  reference_tpm?: number | null;
  rbs_score?: number | null;
}

export interface ExpressionSummary {
  genes_up: number;
  genes_down: number;
  total_genes_evaluated: number;
  genes_with_changed_expression: number;
  custom_sequence_bp?: number | null;
}

type Direction = "up" | "down" | "all";

interface GenesResponse {
  items: GeneRow[];
  total: number;
  counts: { up: number; down: number; all: number };
  complete: boolean;
  searched: number;
  uniform_confidence: number | null;
  uniform_source: string | null;
}

/** Fold change as "2.67×" / "0.375×". */
export function formatFold(value: number): string {
  if (value >= 1) return `${value.toFixed(2)}×`;
  return `${value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}×`;
}

const UP = "#3ef2ff";
const DOWN = "#fcd34d"; // amber-300, same as before

/**
 * Small bar showing how strong the change is, on a log scale so that
 * 2× up and 0.5× down are the same length. Full width = 8× either way.
 */
function FoldBar({ fold }: { fold: number }) {
  const log = Math.log2(fold > 0 ? fold : 1);
  const width = Math.min(Math.abs(log) / 3, 1) * 50; // % of the whole bar
  if (width < 0.5) {
    return <div className="relative h-1.5 w-20 rounded-full bg-white/[0.05]"><div className="absolute left-1/2 top-0 h-full w-px bg-white/20" /></div>;
  }
  return (
    <div className="relative h-1.5 w-20 rounded-full bg-white/[0.05]" aria-hidden="true">
      <div className="absolute left-1/2 top-0 h-full w-px bg-white/20" />
      <div
        className="absolute top-0 h-full rounded-full"
        style={{
          left: log > 0 ? "50%" : `${50 - width}%`,
          width: `${width}%`,
          background: log > 0 ? UP : DOWN,
        }}
      />
    </div>
  );
}

function sourceOf(g: GeneRow) {
  return g.prediction_source ?? g.source ?? "prediction";
}

/**
 * Gene expression for one run: Up / Down / All tabs, a search box that
 * looks through every gene the model scored, and a short list that grows
 * with "Show more" instead of one very long table.
 */
export function GeneExpression({
  simId,
  summary,
  customPart,
}: {
  simId: string;
  summary?: ExpressionSummary;
  customPart?: GeneRow;
}) {
  const [tab, setTab] = useState<Direction>("up");
  const [searchText, setSearchText] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState<GenesResponse | null>(null);
  const [items, setItems] = useState<GeneRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0); // ignore answers to old requests

  // Wait until typing pauses before searching. Starting a search jumps to
  // "All" so unchanged genes (e.g. lacZ at 1.00×) can be found too.
  useEffect(() => {
    const t = setTimeout(() => {
      const next = searchText.trim();
      if (next && !query) setTab("all");
      setQuery(next);
    }, 300);
    return () => clearTimeout(t);
  }, [searchText, query]);

  const fetchPage = async (offset: number, limit: number) => {
    const params = new URLSearchParams({ direction: tab, limit: String(limit), offset: String(offset) });
    if (query) params.set("q", query);
    const res = await fetch(`${API}/results/${simId}/genes?${params}`);
    if (!res.ok) throw new Error(`Could not load genes (HTTP ${res.status})`);
    return (await res.json()) as GenesResponse;
  };

  // First page whenever the tab or search changes
  useEffect(() => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    fetchPage(0, FIRST_PAGE)
      .then((d) => {
        if (id !== requestId.current) return;
        setData(d);
        setItems(d.items);
      })
      .catch((e: unknown) => {
        if (id !== requestId.current) return;
        setError(e instanceof Error ? e.message : "Could not load genes");
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simId, tab, query]);

  const showMore = async () => {
    const id = requestId.current;
    setLoadingMore(true);
    try {
      const d = await fetchPage(items.length, MORE_PAGE);
      if (id === requestId.current) setItems((prev) => [...prev, ...d.items]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not load more genes");
    } finally {
      setLoadingMore(false);
    }
  };

  const collapse = () => setItems((prev) => prev.slice(0, FIRST_PAGE));

  const counts = data?.counts;
  const total = data?.total ?? 0;
  const showConfidence = data?.uniform_confidence == null;
  const showSource = data?.uniform_source == null;
  const evaluated = summary?.total_genes_evaluated ?? data?.searched ?? 0;

  const tabs: { key: Direction; label: string; count?: number; color?: string }[] = [
    { key: "up", label: "▲ Up", count: counts?.up, color: UP },
    { key: "down", label: "▼ Down", count: counts?.down, color: DOWN },
    { key: "all", label: "All", count: counts?.all },
  ];

  return (
    <Card className="p-5">
      {/* Title + totals for the whole run */}
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <h3 className="text-sm font-semibold text-[#d9f7ff]">Expression Predictions</h3>
        {evaluated > 0 && (
          <span className="text-xs text-[#5c8494] font-mono-readout">
            {evaluated.toLocaleString()} genes evaluated
          </span>
        )}
      </div>

      {/* The user's own DNA part, pinned so it never gets lost in the list */}
      {customPart && (
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-[#9b6ff1]/30 bg-[#9b6ff1]/[0.07] px-4 py-2.5 text-sm">
          <span className="inline-flex items-center gap-2 text-[#eaffff]">
            <Dna className="h-4 w-4 text-[#b9a0ff]" strokeWidth={1.75} aria-hidden="true" />
            Your DNA part
            {summary?.custom_sequence_bp ? (
              <span className="text-xs text-[#8cc3d4] font-mono-readout">{summary.custom_sequence_bp.toLocaleString()} bp</span>
            ) : null}
          </span>
          <span className="font-mono-readout text-[#eaffff]">{formatFold(customPart.relative_expression)}</span>
          {customPart.rbs_score != null && (
            <span className="text-xs text-[#8cc3d4]">RBS score <span className="font-mono-readout text-[#eaffff]">{customPart.rbs_score.toFixed(2)}</span></span>
          )}
          {customPart.confidence != null && (
            <span className="text-xs text-[#8cc3d4]">confidence <span className="font-mono-readout text-[#eaffff]">{(customPart.confidence * 100).toFixed(0)}%</span></span>
          )}
          <span className="text-xs text-[#5c8494]">{sourceOf(customPart)}</span>
        </div>
      )}

      {/* Tabs + search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <div role="tablist" aria-label="Which genes to show" className="inline-flex rounded-xl border border-white/[0.07] bg-white/[0.03] p-0.5 text-xs">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                tab === t.key ? "bg-white/[0.09] text-[#eaffff]" : "text-[#8cc3d4] hover:text-[#eaffff]"
              }`}
            >
              <span style={t.color && tab === t.key ? { color: t.color } : undefined}>{t.label}</span>
              {t.count != null && <span className="ml-1.5 font-mono-readout text-[#5c8494]">{t.count.toLocaleString()}</span>}
            </button>
          ))}
        </div>

        <div className="relative sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#5c8494]" aria-hidden="true" />
          <input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Escape") setSearchText(""); }}
            maxLength={50}
            placeholder="Search gene: pflB, nuo, b0903…"
            aria-label="Search genes"
            className="w-full rounded-xl border border-white/[0.07] bg-[#01070c]/60 py-1.5 pl-8 pr-8 text-sm text-[#eaffff] placeholder:text-[#5c8494] focus:border-[#3ef2ff]/60 focus:outline-none"
          />
          {searchText && (
            <button
              onClick={() => setSearchText("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-[#5c8494] hover:text-[#eaffff]"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Values that are the same for every gene, said once */}
      {data && (!showConfidence || !showSource) && (
        <p className="mb-2 text-[11px] text-[#5c8494]">
          Every prediction in this run
          {!showSource && <> comes from <span className="text-[#8cc3d4]">{data.uniform_source}</span></>}
          {!showSource && !showConfidence && " with"}
          {!showConfidence && data.uniform_confidence != null && (
            <> <span className="font-mono-readout text-[#8cc3d4]">{(data.uniform_confidence * 100).toFixed(0)}%</span> confidence</>
          )}
          .
        </p>
      )}

      {/* Older runs only saved their top genes */}
      {data && !data.complete && (
        <p className="mb-3 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs text-[#8cc3d4]">
          This run was made before full gene search was added, so only its {data.searched.toLocaleString()} saved genes
          (the most changed){summary ? ` of ${summary.genes_up.toLocaleString()} up and ${summary.genes_down.toLocaleString()} down` : ""} can be listed and searched. New runs keep all {evaluated > data.searched ? evaluated.toLocaleString() : "~1,500"} genes.
        </p>
      )}

      {error ? (
        <p className="text-sm text-[#ff8b6e]">{error}</p>
      ) : loading && !data ? (
        <div className="flex items-center gap-2 py-6 text-sm text-[#5c8494]">
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading genes…
        </div>
      ) : items.length === 0 ? (
        <p className="py-4 text-sm italic text-[#5c8494]">
          {query
            ? tab !== "all" && (counts?.all ?? 0) > 0
              ? <>No {tab === "up" ? "up-regulated" : "down-regulated"} genes match “{query}”. <button className="not-italic text-[#7dffef] underline-offset-2 hover:underline" onClick={() => setTab("all")}>See {counts?.all} in All</button></>
              : <>No genes match “{query}”{data && !data.complete ? " among the saved genes" : ""}.</>
            : tab === "all"
              ? "No expression predictions available for this simulation."
              : `No genes are ${tab === "up" ? "up" : "down"}-regulated vs the reference.`}
        </p>
      ) : (
        <div className={`overflow-x-auto transition-opacity ${loading ? "opacity-50" : ""}`}>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/[0.07] text-[#5c8494] text-[11px] uppercase tracking-wider">
                <th className="pb-1.5 font-medium">Gene</th>
                <th className="pb-1.5 font-medium">Fold vs reference</th>
                <th className="pb-1.5 font-medium text-right">Reference TPM</th>
                {showConfidence && <th className="pb-1.5 font-medium text-right">Confidence</th>}
                {showSource && <th className="pb-1.5 font-medium pl-4">Source</th>}
              </tr>
            </thead>
            <tbody className="text-sm">
              {items.map((g) => {
                const source = sourceOf(g);
                const isStub = g.confidence === 0 && source === "stub";
                const fold = g.relative_expression;
                const changed = Math.abs(fold - 1) > 0.01;
                const color = !changed ? "text-[#8cc3d4]" : fold > 1 ? "text-[#3ef2ff]" : "text-amber-300";
                return (
                  <tr key={g.gene_id} className="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02]">
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {g.gene_name && <span className="text-[#eaffff] italic mr-2">{g.gene_name}</span>}
                      <span className={`font-mono-readout ${g.gene_name ? "text-xs text-[#5c8494]" : "text-[#8cc3d4]"}`}>{g.gene_id}</span>
                    </td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {isStub ? (
                        <span className="text-[#5c8494] italic text-xs">model not yet trained</span>
                      ) : (
                        <span className="flex items-center gap-3">
                          <span className={`${color} font-mono-readout w-20`}>
                            {changed ? (fold > 1 ? "▲ " : "▼ ") : ""}
                            {formatFold(fold)}
                          </span>
                          <span className="hidden sm:block"><FoldBar fold={fold} /></span>
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 font-mono-readout text-right text-[#5c8494]">
                      {g.reference_tpm != null ? g.reference_tpm.toLocaleString() : "–"}
                    </td>
                    {showConfidence && (
                      <td className="py-1.5 font-mono-readout text-right text-[#7dffef]">
                        {isStub || g.confidence == null ? "–" : `${(g.confidence * 100).toFixed(0)}%`}
                      </td>
                    )}
                    {showSource && <td className="py-1.5 pl-4 text-[#5c8494]">{source}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer: how many are showing, and grow / shrink the list */}
      {!error && items.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.05] pt-3 text-xs">
          <span className="text-[#5c8494]">
            Showing <span className="font-mono-readout text-[#8cc3d4]">{items.length.toLocaleString()}</span> of{" "}
            <span className="font-mono-readout text-[#8cc3d4]">{total.toLocaleString()}</span>
            {tab === "up" ? " up-regulated" : tab === "down" ? " down-regulated" : ""} genes
            {query && <> matching “{query}”</>}
            {" · strongest change first"}
          </span>
          <span className="flex items-center gap-2">
            {items.length > FIRST_PAGE && (
              <button onClick={collapse} className="px-3 py-1 rounded-lg text-[#8cc3d4] hover:text-[#eaffff] transition-colors">
                Show fewer
              </button>
            )}
            {items.length < total && (
              <button
                onClick={showMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/[0.05] border border-white/[0.08] text-[#eaffff] hover:bg-white/[0.09] transition-colors disabled:opacity-60"
              >
                {loadingMore && <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
                Show {Math.min(MORE_PAGE, total - items.length)} more
              </button>
            )}
          </span>
        </div>
      )}
    </Card>
  );
}

export default GeneExpression;