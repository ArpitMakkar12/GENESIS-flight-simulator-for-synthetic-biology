'use client';
import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/loading';
import {
  ReferenceDetailPanel,
  DetailEmptyState,
} from '@/components/reference/detail-panel';
import {
  getGeneFields,
  getTFFields,
  getPathwayFields,
  populated,
} from '@/components/reference/field-config';
import { Dna, Network, Workflow, SearchX, ChevronLeft, ChevronRight } from "lucide-react";
import { LibrarySearch } from '@/components/library/library-search';

export type KnowledgeTab = 'genes' | 'tfs' | 'pathways';

import { API as API_BASE } from "@/lib/api";

/** Rows per page (Genes and Transcription Factors) and the Prev/Next button style — both match the Results page. */
const PAGE_SIZE = 25;
const PAGE_BTN =
  "inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-xl bg-white/[0.05] text-[#8cc3d4] border border-white/10 hover:bg-white/[0.08] transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

/* ─── Types ──────────────────────────────────────────── */

interface Gene {
  id: string;
  locus_tag: string;
  name: string | null;
  product: string | null;
  start_pos: number;
  end_pos: number;
  strand: string;
  gc_content: number | null;
  length_bp: number | null;
}

interface TF {
  id: string;
  name: string;
  tf_family: string | null;
  sensing_signal: string | null;
  active_form: string | null;
  regulated_gene_count: number;
}

interface TFDetail extends TF {
  regulated_genes: {
    gene_locus_tag: string;
    gene_name: string | null;
    regulation_type: string;
    confidence_score: number | null;
  }[];
}

interface Pathway {
  subsystem: string;
  reaction_count: number;
}

interface Reaction {
  id: string;
  bigg_id: string;
  name: string | null;
  subsystem: string | null;
  reaction_formula: string | null;
  is_reversible: boolean;
  ec_number: string | null;
}

interface PathwayDetail {
  subsystem: string;
  reaction_count: number;
  reactions: Reaction[];
}

/* ─── Regulation type badge ──────────────────────────── */

function RegTypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    activator: 'bg-[#3ef2ff]/10 text-[#7dffef] border-[#3ef2ff]/25',
    repressor: 'bg-[#ff5a36]/10 text-[#ff8b6e] border-[#ff5a36]/25',
    unknown: 'bg-white/[0.05] text-[#5c8494] border-white/10',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 text-[10px] rounded-full border ${styles[type] || styles.unknown}`}>
      {type}
    </span>
  );
}

/* ─── Genes / Transcription Factors / Pathways tabs ──── */

/**
 * The three E. coli tabs of the Library. The Library page decides which tab
 * is showing (`tab`). The `initial…` props come from links such as
 * /library?tab=genes&gene=b0903 and open that item's details straight away.
 */
export function KnowledgeTabs({
  tab: activeTab,
  initialGene,
  initialTf,
  initialPathway,
}: {
  tab: KnowledgeTab;
  initialGene?: string | null;
  initialTf?: string | null;
  initialPathway?: string | null;
}) {

  // ── Genes state ──
  // geneSearch is what's in the box; geneQuery is the search actually applied
  // (it follows geneSearch 300 ms after typing stops).
  const [geneSearch, setGeneSearch] = useState('');
  const [geneQuery, setGeneQuery] = useState('');
  const [genePage, setGenePage] = useState(0);
  const [genes, setGenes] = useState<Gene[]>([]);
  const [geneTotal, setGeneTotal] = useState(0);
  const [geneLoading, setGeneLoading] = useState(false);
  const [geneLoaded, setGeneLoaded] = useState(false);  // first page has arrived
  const [geneError, setGeneError] = useState<string | null>(null);
  const [selectedGene, setSelectedGene] = useState<Gene | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const geneRequestRef = useRef(0);                      // ignore answers to old requests
  const selectExactRef = useRef<string | null>(null);    // gene to open after following a link
  const geneTableRef = useRef<HTMLDivElement | null>(null);

  // ── TFs state ──
  const [tfs, setTfs] = useState<TF[]>([]);
  const [tfLoading, setTfLoading] = useState(false);
  const [tfLoaded, setTfLoaded] = useState(false);
  const [selectedTF, setSelectedTF] = useState<TFDetail | null>(null);
  const [tfDetailLoading, setTfDetailLoading] = useState(false);
  const [tfSearch, setTfSearch] = useState('');
  const [tfPage, setTfPage] = useState(0);
  const tfTableRef = useRef<HTMLDivElement | null>(null);
  const [tfGeneFilter, setTfGeneFilter] = useState('');

  // ── Pathways state ──
  const [pathways, setPathways] = useState<Pathway[]>([]);
  const [pwLoading, setPwLoading] = useState(false);
  const [pwLoaded, setPwLoaded] = useState(false);
  const [selectedPathway, setSelectedPathway] = useState<PathwayDetail | null>(null);
  const [pwDetailLoading, setPwDetailLoading] = useState(false);
  const [pwReactionFilter, setPwReactionFilter] = useState('');
  const [pwSearch, setPwSearch] = useState('');
  const [pwPage, setPwPage] = useState(0);
  const pwTableRef = useRef<HTMLDivElement | null>(null);

  /* ─── Genes: one page at a time, narrowed by the search ─── */

  // Load the current page whenever the Genes tab is open and the page or the
  // applied search changes. With an empty search this pages through every gene,
  // so the full list is there as soon as you open the tab.
  useEffect(() => {
    if (activeTab !== 'genes') return;
    const id = ++geneRequestRef.current;
    setGeneLoading(true);
    setGeneError(null);

    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(genePage * PAGE_SIZE),
    });
    if (geneQuery) params.set('search', geneQuery);

    fetch(`${API_BASE}/genes?${params}`)
      .then(res => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: { items: Gene[]; total: number }) => {
        if (id !== geneRequestRef.current) return;
        setGenes(data.items);
        setGeneTotal(data.total);
        setGeneLoaded(true);
        // Followed a link such as ?gene=b0903: open that gene's details
        const wanted = selectExactRef.current?.toLowerCase();
        if (wanted) {
          const exact = data.items.find(
            g => g.locus_tag.toLowerCase() === wanted || (g.name || '').toLowerCase() === wanted
          );
          if (exact) setSelectedGene(exact);
          selectExactRef.current = null;
        }
      })
      .catch(() => {
        if (id === geneRequestRef.current) setGeneError('Could not load genes. Is the backend running?');
      })
      .finally(() => {
        if (id === geneRequestRef.current) setGeneLoading(false);
      });
  }, [activeTab, geneQuery, genePage]);

  // Typing: wait 300 ms, then apply the search and go back to page 1
  const onGeneSearchChange = (val: string) => {
    setGeneSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setGeneQuery(val.trim());
      setGenePage(0);
    }, 300);
  };

  // Changing page: if the top of the table has scrolled out of sight,
  // bring it back so the new page starts at the top
  const goToGenePage = (next: number) => {
    setGenePage(next);
    const top = geneTableRef.current?.getBoundingClientRect().top;
    if (top !== undefined && top < 80) {
      window.scrollTo({ top: window.scrollY + top - 90, behavior: 'smooth' });
    }
  };

  const genePageCount = Math.max(1, Math.ceil(geneTotal / PAGE_SIZE));
  const geneFirstRow = geneTotal === 0 ? 0 : genePage * PAGE_SIZE + 1;
  const geneLastRow = Math.min(geneTotal, (genePage + 1) * PAGE_SIZE);

  /* ─── TF loading ─────────────────────────────────── */

  const loadTFs = async () => {
    if (tfLoaded) return;
    setTfLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tfs`);
      if (res.ok) setTfs(await res.json());
      setTfLoaded(true);
    } catch (e) { console.error(e); }
    setTfLoading(false);
  };

  const loadTFDetail = async (name: string) => {
    if (selectedTF?.name === name) return; // don't refetch same TF
    setTfGeneFilter('');
    setTfDetailLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tfs/${encodeURIComponent(name)}`);
      if (res.ok) setSelectedTF(await res.json());
    } catch (e) { console.error(e); }
    setTfDetailLoading(false);
  };

  /* ─── Pathway loading ────────────────────────────── */

  const loadPathways = async () => {
    if (pwLoaded) return;
    setPwLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pathways`);
      if (res.ok) setPathways(await res.json());
      setPwLoaded(true);
    } catch (e) { console.error(e); }
    setPwLoading(false);
  };

  const loadPathwayDetail = async (subsystem: string) => {
    if (selectedPathway?.subsystem === subsystem) return; // don't refetch
    setPwDetailLoading(true);
    setPwReactionFilter('');
    try {
      const res = await fetch(`${API_BASE}/pathways/${encodeURIComponent(subsystem)}`);
      if (res.ok) setSelectedPathway(await res.json());
    } catch (e) { console.error(e); }
    setPwDetailLoading(false);
  };

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'tfs') loadTFs();
    if (activeTab === 'pathways') loadPathways();
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Opened from a link: search for that gene / open that TF or pathway
  useEffect(() => {
    if (!initialGene) return;
    selectExactRef.current = initialGene;
    setGeneSearch(initialGene);
    setGeneQuery(initialGene);
    setGenePage(0);
  }, [initialGene]);
  useEffect(() => {
    if (initialTf) loadTFDetail(initialTf);
  }, [initialTf]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialPathway) loadPathwayDetail(initialPathway);
  }, [initialPathway]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ─── Filtered TFs, one page at a time ───────────── */
  // All TFs are already loaded, so filtering and paging happen right here in
  // the browser — no extra requests, and it reacts instantly as you type.

  const filteredTFs = tfSearch
    ? tfs.filter(tf => tf.name.toLowerCase().includes(tfSearch.toLowerCase()))
    : tfs;

  const tfPageCount = Math.max(1, Math.ceil(filteredTFs.length / PAGE_SIZE));
  const tfPageRows = filteredTFs.slice(tfPage * PAGE_SIZE, (tfPage + 1) * PAGE_SIZE);
  const tfFirstRow = filteredTFs.length === 0 ? 0 : tfPage * PAGE_SIZE + 1;
  const tfLastRow = Math.min(filteredTFs.length, (tfPage + 1) * PAGE_SIZE);

  // Typing a filter starts again from page 1
  const onTfSearchChange = (val: string) => {
    setTfSearch(val);
    setTfPage(0);
  };

  // Same as Genes: bring the table top back into view when changing page
  const goToTfPage = (next: number) => {
    setTfPage(next);
    const top = tfTableRef.current?.getBoundingClientRect().top;
    if (top !== undefined && top < 80) {
      window.scrollTo({ top: window.scrollY + top - 90, behavior: 'smooth' });
    }
  };

  // Followed a link like ?tab=tfs&tf=FNR: jump to the page that row is on
  useEffect(() => {
    if (!initialTf || tfs.length === 0) return;
    const index = tfs.findIndex(tf => tf.name.toLowerCase() === initialTf.toLowerCase());
    if (index >= 0) setTfPage(Math.floor(index / PAGE_SIZE));
  }, [initialTf, tfs]);

  /* ─── Pathways list, one page at a time ─────────── */
  // Like TFs, the full list is already in the browser, so filter and page here.

  const filteredPathways = pwSearch
    ? pathways.filter(p => p.subsystem.toLowerCase().includes(pwSearch.toLowerCase()))
    : pathways;

  // Bars are scaled to the biggest pathway overall, so a bar means the same
  // length on every page and while filtering
  const pwMaxCount = Math.max(1, ...pathways.map(p => p.reaction_count));
  // Every reaction belongs to exactly one pathway, so the sum is the model size
  const pwTotalReactions = Math.max(1, pathways.reduce((sum, p) => sum + p.reaction_count, 0));

  const pwPageCount = Math.max(1, Math.ceil(filteredPathways.length / PAGE_SIZE));
  const pwPageRows = filteredPathways.slice(pwPage * PAGE_SIZE, (pwPage + 1) * PAGE_SIZE);
  const pwFirstRow = filteredPathways.length === 0 ? 0 : pwPage * PAGE_SIZE + 1;
  const pwLastRow = Math.min(filteredPathways.length, (pwPage + 1) * PAGE_SIZE);

  // Typing a filter starts again from page 1
  const onPwSearchChange = (val: string) => {
    setPwSearch(val);
    setPwPage(0);
  };

  // Bring the list top back into view when changing page
  const goToPwPage = (next: number) => {
    setPwPage(next);
    const top = pwTableRef.current?.getBoundingClientRect().top;
    if (top !== undefined && top < 80) {
      window.scrollTo({ top: window.scrollY + top - 90, behavior: 'smooth' });
    }
  };

  // Followed a link like ?tab=pathways&pathway=Citric%20Acid%20Cycle: jump to its page
  useEffect(() => {
    if (!initialPathway || pathways.length === 0) return;
    const index = pathways.findIndex(p => p.subsystem.toLowerCase() === initialPathway.toLowerCase());
    if (index >= 0) setPwPage(Math.floor(index / PAGE_SIZE));
  }, [initialPathway, pathways]);

  /* ─── Filtered pathway reactions ─────────────────── */

  const filteredReactions = selectedPathway
    ? (pwReactionFilter
        ? selectedPathway.reactions.filter(r =>
            (r.name || '').toLowerCase().includes(pwReactionFilter.toLowerCase()) ||
            r.bigg_id.toLowerCase().includes(pwReactionFilter.toLowerCase())
          )
        : selectedPathway.reactions)
    : [];

  return (
    <div>
      {/* ═══════════════════════════════════════════════════ */}
      {/* GENES TAB                                          */}
      {/* ═══════════════════════════════════════════════════ */}
      {activeTab === 'genes' && (
        <div>
          {/* Search bar — results update as you type */}
          <div className="mb-4">
            <LibrarySearch
              value={geneSearch}
              onChange={onGeneSearchChange}
              busy={geneLoading}
              label="Search genes"
              placeholder="Search by gene name, locus tag, or product (e.g. lacZ, b0344, polymerase)"
            />
          </div>

          {geneError ? (
            <Card className="p-6 text-center text-sm text-[#ff8b6e]">{geneError}</Card>
          ) : !geneLoaded ? (
            <div className="py-8"><Spinner /></div>
          ) : genes.length === 0 ? (
            /* Nothing matched the search */
            <Card className="p-8 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-white/[0.04] ring-1 ring-white/10">
                <SearchX className="h-7 w-7 text-[#5c8494]" strokeWidth={1.5} aria-hidden="true" />
              </div>
              <p className="text-[#8cc3d4]">No genes match &lsquo;{geneQuery}&rsquo;</p>
              <p className="text-xs text-[#5c8494] mt-1">Try a different name, locus tag, or product keyword</p>
            </Card>
          ) : (
            /* The list: one page at a time */
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2" ref={geneTableRef}>
                <Card className="overflow-hidden">
                  {/* Dimmed while the next page loads, so the layout doesn't jump */}
                  <div className={`overflow-x-auto transition-opacity ${geneLoading ? 'opacity-50' : ''}`}>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                          <th className="text-left p-3 font-medium uppercase tracking-wider">Locus Tag</th>
                          <th className="text-left p-3 font-medium uppercase tracking-wider">Gene Name</th>
                          <th className="text-left p-3 font-medium uppercase tracking-wider">Product</th>
                          <th className="text-right p-3 font-medium uppercase tracking-wider">Length (bp)</th>
                          <th className="text-right p-3 font-medium uppercase tracking-wider">GC%</th>
                          <th className="text-center p-3 font-medium uppercase tracking-wider">Strand</th>
                        </tr>
                      </thead>
                      <tbody>
                        {genes.map((g) => (
                          <tr
                            key={g.id}
                            onClick={() => setSelectedGene(g)}
                            className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${
                              selectedGene?.id === g.id ? 'bg-[#3ef2ff]/[0.07] shadow-[inset_2px_0_0_0_#3ef2ff]' : ''
                            }`}
                          >
                            <td className="p-3 font-mono-readout text-[#3ef2ff]">{g.locus_tag}</td>
                            <td className="p-3 font-medium text-[#eaffff]">
                              {g.name || <span className="text-[#5c8494] text-xs italic">Not yet catalogued</span>}
                            </td>
                            <td className="p-3 text-[#8cc3d4] truncate max-w-xs">
                              {g.product || <span className="text-[#5c8494] text-xs italic">Not yet catalogued</span>}
                            </td>
                            <td className="p-3 text-right text-[#8cc3d4] font-mono-readout">{g.length_bp?.toLocaleString()}</td>
                            <td className="p-3 text-right text-[#8cc3d4] font-mono-readout">
                              {g.gc_content ? (g.gc_content * 100).toFixed(1) + '%' : <span className="text-[#5c8494] text-xs italic">pending</span>}
                            </td>
                            <td className="p-3 text-center font-mono-readout text-[#8cc3d4]">{g.strand}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pages: same look as the Results list */}
                  <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-white/[0.06] text-xs text-[#8cc3d4]">
                    <span>
                      Showing {geneFirstRow.toLocaleString()}–{geneLastRow.toLocaleString()} of{' '}
                      {geneTotal.toLocaleString()} genes
                      {geneQuery && <> matching &lsquo;{geneQuery}&rsquo;</>}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        className={PAGE_BTN}
                        disabled={genePage === 0 || geneLoading}
                        onClick={() => goToGenePage(genePage - 1)}
                      >
                        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
                      </button>
                      <span className="px-1 text-[#5c8494]">
                        Page {(genePage + 1).toLocaleString()} of {genePageCount.toLocaleString()}
                      </span>
                      <button
                        className={PAGE_BTN}
                        disabled={genePage + 1 >= genePageCount || geneLoading}
                        onClick={() => goToGenePage(genePage + 1)}
                      >
                        Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Gene Detail Panel */}
              <div>
                {selectedGene ? (
                  <ReferenceDetailPanel
                    title={selectedGene.name || selectedGene.locus_tag}
                    fields={getGeneFields(selectedGene)}
                    onClose={() => setSelectedGene(null)}
                  />
                ) : (
                  <DetailEmptyState icon={Dna} text="Click a gene to view details" />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════ */}
      {/* TRANSCRIPTION FACTORS TAB                          */}
      {/* ═══════════════════════════════════════════════════ */}
      {activeTab === 'tfs' && (
        <div>
          {/* Dataset note */}
          <div className="text-[11px] text-[#5c8494] italic mb-3">
            This dataset (PRECISE-1K) includes classic transcription factors, sigma factors (e.g. RpoD), and global regulators (e.g. ppGpp).
          </div>

          {/* Filter bar — narrows the list as you type */}
          <div className="mb-4">
            <LibrarySearch
              value={tfSearch}
              onChange={onTfSearchChange}
              label="Filter transcription factors"
              placeholder="Filter transcription factors by name…"
            />
          </div>

          {tfLoading ? (
            <div className="py-8"><Spinner /></div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2" ref={tfTableRef}>
                <Card className="overflow-hidden">
                  {filteredTFs.length === 0 ? (
                    <p className="p-8 text-center text-sm text-[#8cc3d4]">
                      No transcription factors match &lsquo;{tfSearch}&rsquo;
                    </p>
                  ) : (
                  <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                          <th className="text-left p-3 font-medium uppercase tracking-wider">TF Name</th>
                          <th className="text-right p-3 font-medium uppercase tracking-wider">Regulated Genes</th>
                          <th className="text-center p-3 font-medium uppercase tracking-wider">Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tfPageRows.map((tf) => (
                          <tr
                            key={tf.id}
                            onClick={() => loadTFDetail(tf.name)}
                            className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${
                              selectedTF?.name === tf.name ? 'bg-[#3ef2ff]/[0.07] shadow-[inset_2px_0_0_0_#3ef2ff]' : ''
                            }`}
                          >
                            <td className="p-3 font-medium text-[#3ef2ff]">{tf.name}</td>
                            <td className="p-3 text-right font-mono-readout text-[#8cc3d4]">
                              {tf.regulated_gene_count.toLocaleString()}
                            </td>
                            <td className="p-3 text-center">
                              <span className="px-2.5 py-0.5 text-[11px] rounded-full bg-[#3ef2ff]/10 text-[#7dffef] border border-[#3ef2ff]/25">
                                PRECISE-1K
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pages: same look as Genes and the Results list */}
                  <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-white/[0.06] text-xs text-[#8cc3d4]">
                    <span>
                      Showing {tfFirstRow}–{tfLastRow} of {filteredTFs.length.toLocaleString()} transcription factors
                      {tfSearch && <> matching &lsquo;{tfSearch}&rsquo;</>}
                    </span>
                    <div className="flex items-center gap-2">
                      <button className={PAGE_BTN} disabled={tfPage === 0} onClick={() => goToTfPage(tfPage - 1)}>
                        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
                      </button>
                      <span className="px-1 text-[#5c8494]">Page {tfPage + 1} of {tfPageCount}</span>
                      <button className={PAGE_BTN} disabled={tfPage + 1 >= tfPageCount} onClick={() => goToTfPage(tfPage + 1)}>
                        Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                  </>
                  )}
                </Card>
              </div>

              {/* TF Detail Panel */}
              <div>
                {tfDetailLoading ? (
                  <Card className="p-8 text-center"><Spinner /></Card>
                ) : selectedTF ? (
                  <ReferenceDetailPanel
                    title={selectedTF.name}
                    fields={getTFFields(selectedTF)}
                    onClose={() => setSelectedTF(null)}
                  >
                    {/* Regulated genes list */}
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs text-[#8cc3d4]">
                          Regulated Genes ({selectedTF.regulated_gene_count.toLocaleString()})
                        </div>
                        {selectedTF.regulated_genes.length > 20 && (
                          <input
                            type="text"
                            value={tfGeneFilter}
                            onChange={(e) => setTfGeneFilter(e.target.value)}
                            placeholder="Filter genes…"
                            className="px-2 py-1 text-[10px] rounded-lg bg-[#01070c]/60 border border-white/10 text-[#eaffff] placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 w-32"
                          />
                        )}
                      </div>
                      <div className="max-h-60 overflow-auto rounded-lg bg-[#01070c]/60 border border-white/[0.08]">
                        <table className="w-full text-xs">
                          <thead className="sticky top-0 bg-[#070d14]">
                            <tr className="border-b border-white/10 text-[#5c8494]">
                              <th className="text-left p-2 font-medium">Gene</th>
                              <th className="text-left p-2 font-medium">Name</th>
                              <th className="text-center p-2 font-medium">Type</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(() => {
                              const filtered = tfGeneFilter
                                ? selectedTF.regulated_genes.filter(rg =>
                                    rg.gene_locus_tag.toLowerCase().includes(tfGeneFilter.toLowerCase()) ||
                                    (rg.gene_name || '').toLowerCase().includes(tfGeneFilter.toLowerCase())
                                  )
                                : selectedTF.regulated_genes;
                              const displayed = filtered.slice(0, 100);
                              return (
                                <>
                                  {displayed.map((rg) => (
                                    <tr key={rg.gene_locus_tag} className="border-b border-white/[0.04]">
                                      <td className="p-2 font-mono-readout text-[#3ef2ff]">{rg.gene_locus_tag}</td>
                                      <td className="p-2 text-[#8cc3d4]">
                                        {rg.gene_name || <span className="text-[#5c8494] italic text-[10px]">Not yet catalogued</span>}
                                      </td>
                                      <td className="p-2 text-center"><RegTypeBadge type={rg.regulation_type} /></td>
                                    </tr>
                                  ))}
                                  {filtered.length > 100 && (
                                    <tr>
                                      <td colSpan={3} className="p-2 text-center text-[10px] text-[#5c8494]">
                                        Showing 100 of {filtered.length.toLocaleString()} — use the filter above to narrow results
                                      </td>
                                    </tr>
                                  )}
                                  {tfGeneFilter && filtered.length === 0 && (
                                    <tr>
                                      <td colSpan={3} className="p-3 text-center text-[10px] text-[#5c8494] italic">
                                        No genes match &lsquo;{tfGeneFilter}&rsquo;
                                      </td>
                                    </tr>
                                  )}
                                </>
                              );
                            })()}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </ReferenceDetailPanel>
                ) : (
                  <DetailEmptyState icon={Network} text="Click a transcription factor to view regulated genes" />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════ */}
      {/* PATHWAYS TAB                                       */}
      {/* ═══════════════════════════════════════════════════ */}
      {activeTab === 'pathways' && (
        <div>
          {/* Filter bar — same box as every other tab */}
          <div className="mb-4">
            <LibrarySearch
              value={pwSearch}
              onChange={onPwSearchChange}
              label="Filter pathways"
              placeholder="Filter pathways by name… (e.g. glycolysis, citric, transport)"
            />
          </div>

          {pwLoading ? (
            <div className="py-8"><Spinner /></div>
          ) : (
            // Same two-thirds / one-third split as Parts, Genes and TFs
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Pathway list — left */}
              <div className="lg:col-span-2" ref={pwTableRef}>
                <Card className="overflow-hidden">
                  {filteredPathways.length === 0 ? (
                    <p className="p-8 text-center text-sm text-[#8cc3d4]">
                      No pathways match &lsquo;{pwSearch}&rsquo;
                    </p>
                  ) : (
                    <>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                            <th className="text-left p-3 font-medium uppercase tracking-wider">Pathway</th>
                            <th className="text-left p-3 font-medium uppercase tracking-wider w-[45%]">Reactions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pwPageRows.map((p) => (
                            <tr
                              key={p.subsystem}
                              onClick={() => loadPathwayDetail(p.subsystem)}
                              className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${
                                selectedPathway?.subsystem === p.subsystem ? 'bg-[#3ef2ff]/[0.07] shadow-[inset_2px_0_0_0_#3ef2ff]' : ''
                              }`}
                            >
                              <td className="p-3 font-medium text-[#eaffff]">{p.subsystem}</td>
                              <td className="p-3">
                                {/* Bar length = size compared with the biggest pathway */}
                                <div className="flex items-center gap-3" title={`${p.reaction_count} reactions`}>
                                  <div className="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-[#3ef2ff] rounded-full"
                                      style={{ width: `${Math.max(2, (p.reaction_count / pwMaxCount) * 100)}%` }}
                                    />
                                  </div>
                                  <span className="w-10 text-right font-mono-readout text-xs text-[#8cc3d4]">
                                    {p.reaction_count.toLocaleString()}
                                  </span>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {/* Pages: same look as the other tabs */}
                      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-white/[0.06] text-xs text-[#8cc3d4]">
                        <span>
                          Showing {pwFirstRow}–{pwLastRow} of {filteredPathways.length} pathways
                          {pwSearch && <> matching &lsquo;{pwSearch}&rsquo;</>}
                        </span>
                        <div className="flex items-center gap-2">
                          <button className={PAGE_BTN} disabled={pwPage === 0} onClick={() => goToPwPage(pwPage - 1)}>
                            <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
                          </button>
                          <span className="px-1 text-[#5c8494]">Page {pwPage + 1} of {pwPageCount}</span>
                          <button className={PAGE_BTN} disabled={pwPage + 1 >= pwPageCount} onClick={() => goToPwPage(pwPage + 1)}>
                            Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </Card>
              </div>

              {/* Pathway details — right. Sticks while you scroll the list. */}
              <div className="lg:sticky lg:top-24 lg:self-start">
                {pwDetailLoading ? (
                  <Card className="p-8 text-center"><Spinner /></Card>
                ) : selectedPathway ? (
                  <ReferenceDetailPanel
                    title={selectedPathway.subsystem}
                    fields={[
                      // "Subsystem" would only repeat the title, so it is left out
                      ...getPathwayFields(selectedPathway).filter(f => f.label !== 'Subsystem'),
                      populated('Share of model', pwTotalReactions, () => (
                        <span>
                          <span className="font-mono-readout">
                            {((selectedPathway.reaction_count / pwTotalReactions) * 100).toFixed(1)}%
                          </span>
                          <span className="ml-1.5 text-xs text-[#5c8494]">of {pwTotalReactions.toLocaleString()} reactions</span>
                        </span>
                      )),
                    ]}
                    onClose={() => setSelectedPathway(null)}
                  >
                    {/* Reactions: one stacked row each, so nothing scrolls sideways */}
                    <div className="mt-4">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs text-[#8cc3d4]">
                          Reactions ({filteredReactions.length.toLocaleString()})
                        </span>
                        {selectedPathway.reactions.length > 10 && (
                          <input
                            type="text"
                            value={pwReactionFilter}
                            onChange={(e) => setPwReactionFilter(e.target.value)}
                            placeholder="Filter reactions…"
                            aria-label="Filter reactions"
                            className="px-2.5 py-1 rounded-lg bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-xs placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 w-36"
                          />
                        )}
                      </div>
                      <ul className="max-h-[26rem] overflow-y-auto rounded-lg bg-[#01070c]/60 border border-white/[0.08] divide-y divide-white/[0.05]">
                        {filteredReactions.map((r) => (
                          <li key={r.id} className="px-3 py-2 hover:bg-white/[0.02]">
                            {/* line 1: ID, direction, EC number */}
                            <div className="flex items-baseline justify-between gap-2">
                              <span className="font-mono-readout text-xs text-[#3ef2ff]">
                                {r.bigg_id}
                                <span
                                  className="ml-2 text-[#8cc3d4]"
                                  title={r.is_reversible ? 'Reversible' : 'One direction only'}
                                >
                                  {r.is_reversible ? '⇌' : '→'}
                                </span>
                              </span>
                              {r.ec_number && (
                                <span className="font-mono-readout text-[10px] text-[#5c8494]">EC {r.ec_number}</span>
                              )}
                            </div>
                            {/* line 2: readable name */}
                            <div className="text-xs text-[#d9f7ff] mt-0.5">
                              {r.name || <span className="text-[#5c8494] italic">Not yet catalogued</span>}
                            </div>
                            {/* line 3: formula, wraps instead of scrolling */}
                            {r.reaction_formula && (
                              <div className="font-mono-readout text-[10px] text-[#7dffef]/80 mt-0.5 break-words">
                                {r.reaction_formula}
                              </div>
                            )}
                          </li>
                        ))}
                        {filteredReactions.length === 0 && (
                          <li className="px-3 py-4 text-center text-xs italic text-[#5c8494]">
                            No reactions match &lsquo;{pwReactionFilter}&rsquo;
                          </li>
                        )}
                      </ul>
                    </div>
                  </ReferenceDetailPanel>
                ) : (
                  <DetailEmptyState icon={Workflow} text="Click a pathway to view its reactions" />
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default KnowledgeTabs;