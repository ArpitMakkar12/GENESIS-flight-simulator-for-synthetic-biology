'use client';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Spinner, EmptyState } from '@/components/ui/loading';
import {
  ReferenceDetailPanel,
  DetailEmptyState,
} from '@/components/reference/detail-panel';
import { getPartFields, partStrength } from '@/components/reference/field-config';

import { Blocks, LayoutGrid, CornerUpRight, CircleDot, ArrowBigRight, ArrowRightToLine, PackageOpen, Play, ChevronLeft, ChevronRight } from "lucide-react";
import { LibrarySearch } from '@/components/library/library-search';

import { API as API_BASE } from "@/lib/api";

/** Parts per page, and the Prev/Next button style — the look matches every other list in the app. */
const PAGE_SIZE = 12;
const PAGE_BTN =
  "inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

interface Part {
  id: string;
  name: string;
  part_type: string;
  sequence_length: number | null;
  source: string | null;
  strength: number | null;
  annotations: Record<string, string | number | boolean> | null;
}

interface PartDetail extends Part {
  sequence: string | null;
  registry_id: string | null;
}

const PART_TYPES = [
  { key: null,         label: 'All',         icon: LayoutGrid },
  { key: 'promoter',   label: 'Promoters',   icon: CornerUpRight },
  { key: 'rbs',        label: 'RBS',         icon: CircleDot },
  { key: 'cds',        label: 'CDS',         icon: ArrowBigRight },
  { key: 'terminator', label: 'Terminators', icon: ArrowRightToLine },
];

/** Treat "N/A" as missing for display purposes */
function realSequence(seq: string | null): string | null {
  if (!seq || seq.toUpperCase() === 'N/A') return null;
  return seq;
}

/**
 * The "Strength / role" cell. Each part type gets the measure that fits it
 * (see partStrength in field-config.tsx); hover shows the full explanation.
 */
function PartActivity({ part }: { part: Part }) {
  const s = partStrength(part.part_type, part.strength, part.annotations);

  if (s.kind === 'value') {
    return (
      <div className="flex items-center gap-2" title={`${s.percent}% ${s.basis}`}>
        <div className="flex-1 h-1.5 min-w-12 bg-white/[0.08] rounded-full overflow-hidden">
          <div className="h-full bg-[#3ef2ff] rounded-full" style={{ width: `${Math.min(s.percent, 100)}%` }} />
        </div>
        <span className="text-xs text-[#8cc3d4] font-mono-readout w-9 text-right">{s.percent}%</span>
      </div>
    );
  }
  if (s.kind === 'conditional') {
    // inducible promoter: output depends on the inducer, so no single number
    return (
      <span title={s.detail} className="inline-flex whitespace-nowrap px-2 py-0.5 text-[11px] rounded-full border border-[#9b6ff1]/35 bg-[#9b6ff1]/[0.10] text-[#c4b0ff]">
        {s.label}
      </span>
    );
  }
  if (s.kind === 'requires') {
    // phage promoter: silent without its own polymerase
    return (
      <span title={s.detail} className="inline-flex whitespace-nowrap px-2 py-0.5 text-[11px] rounded-full border border-[#ffcf66]/30 bg-[#ffcf66]/[0.08] text-[#ffdc8a]">
        {s.label}
      </span>
    );
  }
  if (s.kind === 'encodes') {
    // CDS: the protein it makes, then its role
    const [protein, role] = s.label.split(' · ');
    return (
      <span title={s.detail} className="text-xs whitespace-nowrap">
        <span className="text-[#eaffff]">{protein}</span>
        {role && <span className="text-[#5c8494]"> · {role}</span>}
      </span>
    );
  }
  return <span className="text-[#5c8494] text-xs italic">{s.reason.toLowerCase()}</span>;
}

/**
 * The Parts tab of the Library (iGEM promoters, RBS, CDS, terminators).
 * `initialPart` comes from a link like /library?tab=parts&part=BBa_J23100:
 * that part's details open straight away and its row is scrolled into view.
 */
export function PartsTab({ initialPart }: { initialPart?: string | null }) {
  const [parts, setParts] = useState<Part[]>([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<PartDetail | null>(null);
  const [page, setPage] = useState(0);
  const tableRef = useRef<HTMLDivElement | null>(null);

  // Reload when the type filter changes, or 300 ms after typing stops —
  // same as every other search in the app, so there is no button to press
  useEffect(() => {
    const t = setTimeout(() => loadParts(), search ? 300 : 0);
    return () => clearTimeout(t);
  }, [typeFilter, search]); // eslint-disable-line react-hooks/exhaustive-deps

  // Opened from a link: show that part's details
  useEffect(() => {
    if (initialPart) loadDetail(initialPart);
  }, [initialPart]); // eslint-disable-line react-hooks/exhaustive-deps

  // Bring the selected row into view once both the list and the part are loaded
  useEffect(() => {
    if (!selected || loading) return;
    document.getElementById(`part-row-${selected.id}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selected, loading]);

  const loadParts = async () => {
    setLoading(true);
    try {
      const url = new URL(`${API_BASE}/parts`);
      if (typeFilter) url.searchParams.set('part_type', typeFilter);
      if (search) url.searchParams.set('search', search);
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setParts(Array.isArray(data) ? data : data.parts || []);
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadDetail = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/parts/${encodeURIComponent(name)}`);
      if (res.ok) setSelected(await res.json());
    } catch (e) { console.error(e); }
  };

  const filtered = parts.filter(p =>
    !search || p.name.toLowerCase().includes(search.toLowerCase())
  );

  /* ─── Pages ──────────────────────────────────────────
   * Part rows are taller than gene rows (badges and bars), so a smaller
   * page keeps a whole page on screen without scrolling.
   */
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const firstRow = filtered.length === 0 ? 0 : page * PAGE_SIZE + 1;
  const lastRow = Math.min(filtered.length, (page + 1) * PAGE_SIZE);

  // Searching or switching type starts again from page 1
  useEffect(() => { setPage(0); }, [search, typeFilter]);

  // Keep the page in range if the list shrinks underneath it
  useEffect(() => {
    if (page > 0 && page >= pageCount) setPage(pageCount - 1);
  }, [page, pageCount]);

  // Bring the table top back into view when changing page
  const goToPage = (next: number) => {
    setPage(next);
    const top = tableRef.current?.getBoundingClientRect().top;
    if (top !== undefined && top < 80) {
      window.scrollTo({ top: window.scrollY + top - 90, behavior: 'smooth' });
    }
  };

  return (
    <div>
      <p className="text-xs text-[#5c8494] mb-4">Characterized genetic parts from the iGEM Registry.</p>

      {/* Type filter */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {PART_TYPES.map((t) => (
          <button
            key={t.label}
            onClick={() => setTypeFilter(t.key)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all border ${
              typeFilter === t.key
                ? 'bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40'
                : 'bg-white/[0.04] text-[#8cc3d4] border-white/10 hover:bg-white/[0.07] hover:text-[#d9f7ff]'
            }`}
          >
            <t.icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} aria-hidden="true" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Search — results update as you type */}
      <div className="mb-5">
        <LibrarySearch
          value={search}
          onChange={setSearch}
          busy={loading}
          label="Search parts"
          placeholder="Search parts by name…"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table */}
        <div className="lg:col-span-2" ref={tableRef}>
          <Card className="overflow-hidden">
            {loading ? (
              <div className="py-8"><Spinner /></div>
            ) : filtered.length === 0 ? (
              <EmptyState icon={PackageOpen} title="No parts found" description="Try a different search or filter." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Name</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Type</th>
                      <th className="text-right p-3 font-medium uppercase tracking-wider">Length (bp)</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Source</th>
                      <th
                        className="text-left p-3 font-medium uppercase tracking-wider"
                        title="Promoters: % of BBa_J23100 · RBS: % of BBa_B0034 · Terminators: termination efficiency · CDS: the protein it encodes"
                      >
                        Strength / role
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((p) => (
                      <tr key={p.id} id={`part-row-${p.id}`} onClick={() => loadDetail(p.name)}
                        className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${
                          selected?.id === p.id ? 'bg-[#3ef2ff]/[0.07] shadow-[inset_2px_0_0_0_#3ef2ff]' : ''
                        }`}>
                        <td className="p-3 text-[#3ef2ff] font-medium">{p.name}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 text-[11px] rounded-full border border-[#3ef2ff]/20 bg-[#3ef2ff]/[0.06] text-[#7dffef]">
                            {p.part_type}
                          </span>
                        </td>
                        <td className="p-3 text-right font-mono-readout">
                          {p.sequence_length != null
                            ? <span className="text-[#8cc3d4]">{p.sequence_length.toLocaleString()}</span>
                            : <span className="text-[#5c8494] text-xs italic">pending</span>}
                        </td>
                        <td className="p-3 text-[#5c8494] text-xs">
                          {p.source || <span className="italic">pending</span>}
                        </td>
                        <td className="p-3">
                          <PartActivity part={p} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pages: same look as Genes and Transcription Factors */}
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-white/[0.06] text-xs text-[#8cc3d4]">
                  <span>
                    Showing {firstRow}–{lastRow} of {filtered.length} parts
                    {search && <> matching &lsquo;{search}&rsquo;</>}
                  </span>
                  <div className="flex items-center gap-2">
                    <button className={PAGE_BTN} disabled={page === 0} onClick={() => goToPage(page - 1)}>
                      <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
                    </button>
                    <span className="px-1 text-[#5c8494]">Page {page + 1} of {pageCount}</span>
                    <button className={PAGE_BTN} disabled={page + 1 >= pageCount} onClick={() => goToPage(page + 1)}>
                      Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Detail panel */}
        <div>
          {selected ? (
            <ReferenceDetailPanel
              title={selected.name}
              fields={getPartFields(selected)}
              onClose={() => setSelected(null)}
            >
              {/* Sequence block */}
              {realSequence(selected.sequence) ? (
                <div className="mt-4">
                  {/* Send this part to the Simulate page; it fills the DNA box there */}
                  <Link
                    href={`/simulate?part=${encodeURIComponent(selected.name)}`}
                    className="mb-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[#3ef2ff]/40 bg-[#3ef2ff]/15 px-4 py-2 text-sm font-medium text-[#7dffef] transition-colors hover:bg-[#3ef2ff]/25"
                  >
                    <Play className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                    Use in a simulation
                  </Link>
                  <div className="text-xs text-[#8cc3d4] mb-2">Sequence</div>
                  <div className="p-3 rounded-lg bg-[#01070c]/60 border border-white/[0.08] text-[10px] text-[#7dffef] font-mono-readout break-all max-h-40 overflow-auto leading-relaxed">
                    {selected.sequence}
                  </div>
                </div>
              ) : (
                <div className="mt-4">
                  <div className="text-xs text-[#8cc3d4] mb-2">Sequence</div>
                  <div className="p-3 rounded-lg bg-[#01070c]/60 border border-white/[0.08] text-xs">
                    <span className="inline-flex px-2 py-0.5 text-[10px] rounded-full bg-white/[0.05] text-[#5c8494] border border-white/10">
                      Not yet catalogued
                    </span>
                  </div>
                </div>
              )}
            </ReferenceDetailPanel>
          ) : (
            <DetailEmptyState icon={Blocks} text="Click a part to view details" />
          )}
        </div>
      </div>
    </div>
  );
}

export default PartsTab;