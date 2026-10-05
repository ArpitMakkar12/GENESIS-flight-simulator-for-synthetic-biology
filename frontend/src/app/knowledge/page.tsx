'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/loading';
import {
  ReferenceDetailPanel,
  DetailEmptyState,
  ResultCount,
} from '@/components/reference/detail-panel';
import {
  getGeneFields,
  getTFFields,
  getPathwayFields,
} from '@/components/reference/field-config';
import { Dna, Network, Workflow, SearchX, type LucideIcon } from "lucide-react";

const TAB_META: Record<'genes' | 'tfs' | 'pathways', { label: string; Icon: LucideIcon }> = {
  genes:    { label: 'Genes',                 Icon: Dna },
  tfs:      { label: 'Transcription Factors', Icon: Network },
  pathways: { label: 'Pathways',              Icon: Workflow },
};

const API_BASE = 'http://localhost:8000/api/v1';

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

/* ─── Main Page ──────────────────────────────────────── */

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<'genes' | 'tfs' | 'pathways'>('genes');

  // ── Genes state ──
  const [geneSearch, setGeneSearch] = useState('');
  const [genes, setGenes] = useState<Gene[]>([]);
  const [geneLoading, setGeneLoading] = useState(false);
  const [geneSearched, setGeneSearched] = useState(false);
  const [selectedGene, setSelectedGene] = useState<Gene | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── TFs state ──
  const [tfs, setTfs] = useState<TF[]>([]);
  const [tfLoading, setTfLoading] = useState(false);
  const [tfLoaded, setTfLoaded] = useState(false);
  const [selectedTF, setSelectedTF] = useState<TFDetail | null>(null);
  const [tfDetailLoading, setTfDetailLoading] = useState(false);
  const [tfSearch, setTfSearch] = useState('');
  const [tfGeneFilter, setTfGeneFilter] = useState('');

  // ── Pathways state ──
  const [pathways, setPathways] = useState<Pathway[]>([]);
  const [pwLoading, setPwLoading] = useState(false);
  const [pwLoaded, setPwLoaded] = useState(false);
  const [selectedPathway, setSelectedPathway] = useState<PathwayDetail | null>(null);
  const [pwDetailLoading, setPwDetailLoading] = useState(false);
  const [pwReactionFilter, setPwReactionFilter] = useState('');

  /* ─── Gene search with debounce ──────────────────── */

  const searchGenes = useCallback(async (query: string) => {
    if (!query.trim()) { setGenes([]); setGeneSearched(false); return; }
    setGeneLoading(true);
    setGeneSearched(true);
    try {
      const res = await fetch(`${API_BASE}/genes?search=${encodeURIComponent(query)}&limit=50`);
      if (res.ok) setGenes(await res.json());
    } catch (e) { console.error(e); }
    setGeneLoading(false);
  }, []);

  const onGeneSearchChange = (val: string) => {
    setGeneSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchGenes(val), 400);
  };

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

  /* ─── Filtered TFs ───────────────────────────────── */

  const filteredTFs = tfSearch
    ? tfs.filter(tf => tf.name.toLowerCase().includes(tfSearch.toLowerCase()))
    : tfs;

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
    <div className="max-w-5xl page-enter">
      <h1 className="text-3xl font-semibold text-[#eaffff] mb-1 glow-text">Knowledge Base</h1>
      <p className="text-sm text-[#8cc3d4] mb-6">Explore E. coli K-12 genes, transcription factors, and metabolic pathways</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {(['genes', 'tfs', 'pathways'] as const).map((tab) => {
          const { label, Icon } = TAB_META[tab];
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all border ${
                activeTab === tab
                  ? 'bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40'
                  : 'bg-white/[0.04] text-[#8cc3d4] border-white/10 hover:bg-white/[0.07] hover:text-[#d9f7ff]'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* GENES TAB                                          */}
      {/* ═══════════════════════════════════════════════════ */}
      {activeTab === 'genes' && (
        <div>
          {/* Search bar */}
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={geneSearch}
              onChange={(e) => onGeneSearchChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchGenes(geneSearch)}
              placeholder="Search by gene name, locus tag, or product (e.g. lacZ, b0344, polymerase)"
              className="flex-1 px-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 transition-colors"
            />
            <button
              onClick={() => searchGenes(geneSearch)}
              disabled={geneLoading}
              className="px-5 py-2 rounded-full bg-[#3ef2ff]/15 text-[#7dffef] border border-[#3ef2ff]/40 text-sm font-medium hover:bg-[#3ef2ff]/25 transition-all disabled:opacity-50 shadow-[0_0_16px_-4px_rgba(62,242,255,0.3)]"
            >
              {geneLoading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {/* Prompt / Loading / Empty / Results */}
          {!geneSearched ? (
            /* Initial prompt state */
            <Card className="p-8 text-center border-dashed">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#3ef2ff]/10 ring-1 ring-[#3ef2ff]/25">
                <Dna className="h-7 w-7 text-[#7dffef]" strokeWidth={1.5} aria-hidden="true" />
              </div>
              <p className="text-[#8cc3d4] mb-3">Search 4,651 genes by name, locus tag, or product</p>
              <div className="flex gap-2 justify-center flex-wrap">
                {['lacZ', 'b0344', 'polymerase'].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setGeneSearch(q); searchGenes(q); }}
                    className="px-3 py-1 rounded-full text-xs bg-[#3ef2ff]/10 text-[#7dffef] border border-[#3ef2ff]/25 hover:bg-[#3ef2ff]/20 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </Card>
          ) : geneLoading ? (
            <div className="py-8"><Spinner /></div>
          ) : genes.length === 0 ? (
            /* Zero results — distinct from prompt state */
            <Card className="p-8 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-white/[0.04] ring-1 ring-white/10">
                <SearchX className="h-7 w-7 text-[#5c8494]" strokeWidth={1.5} aria-hidden="true" />
              </div>
              <p className="text-[#8cc3d4]">No genes match &lsquo;{geneSearch}&rsquo;</p>
              <p className="text-xs text-[#5c8494] mt-1">Try a different name, locus tag, or product keyword</p>
            </Card>
          ) : (
            /* Results */
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="overflow-hidden">
                  <div className="overflow-x-auto">
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
                    <ResultCount>{genes.length} genes found</ResultCount>
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

          {/* Search bar */}
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={tfSearch}
              onChange={(e) => setTfSearch(e.target.value)}
              placeholder="Filter transcription factors by name..."
              className="flex-1 px-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 transition-colors"
            />
          </div>

          {tfLoading ? (
            <div className="py-8"><Spinner /></div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="overflow-hidden">
                  <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-[#0a1018] z-10">
                        <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                          <th className="text-left p-3 font-medium uppercase tracking-wider">TF Name</th>
                          <th className="text-right p-3 font-medium uppercase tracking-wider">Regulated Genes</th>
                          <th className="text-center p-3 font-medium uppercase tracking-wider">Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredTFs.map((tf) => (
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
                    <ResultCount>
                      {filteredTFs.length === tfs.length
                        ? `${tfs.length} transcription factors`
                        : `${filteredTFs.length} of ${tfs.length} transcription factors`}
                    </ResultCount>
                  </div>
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
          {pwLoading ? (
            <div className="py-8"><Spinner /></div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Card grid — left */}
              <div className="lg:col-span-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {pathways.map((p) => (
                    <div
                      key={p.subsystem}
                      onClick={() => loadPathwayDetail(p.subsystem)}
                      className="cursor-pointer"
                    >
                      <Card
                        hover
                        className={`p-4 transition-all ${
                          selectedPathway?.subsystem === p.subsystem
                            ? 'ring-1 ring-[#3ef2ff]/40 shadow-[0_0_20px_-8px_rgba(62,242,255,0.3)]'
                            : ''
                        }`}
                      >
                        <h3 className="font-medium text-sm mb-1 text-[#eaffff]">{p.subsystem}</h3>
                        <p className="text-2xl font-semibold text-[#3ef2ff] font-mono-readout glow-text">{p.reaction_count}</p>
                        <p className="text-xs text-[#5c8494]">reactions</p>
                      </Card>
                    </div>
                  ))}
                </div>
                <div className="mt-3 px-1 text-xs text-[#5c8494]">{pathways.length} pathways</div>
              </div>

              {/* Pathway Detail Panel — right */}
              <div className="lg:col-span-2">
                {pwDetailLoading ? (
                  <Card className="p-8 text-center"><Spinner /></Card>
                ) : selectedPathway ? (
                  <ReferenceDetailPanel
                    title={selectedPathway.subsystem}
                    fields={getPathwayFields(selectedPathway)}
                    onClose={() => setSelectedPathway(null)}
                  >
                    {/* Reaction list with filter */}
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-[#8cc3d4]">
                          Reactions ({filteredReactions.length})
                        </span>
                        {selectedPathway.reactions.length > 10 && (
                          <input
                            type="text"
                            value={pwReactionFilter}
                            onChange={(e) => setPwReactionFilter(e.target.value)}
                            placeholder="Filter..."
                            className="px-2 py-1 rounded-md bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-xs placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 w-28"
                          />
                        )}
                      </div>
                      <div className="max-h-72 overflow-auto rounded-lg bg-[#01070c]/60 border border-white/[0.08]">
                        <div className="min-w-[600px]">
                        <table className="w-full text-xs">
                          <thead className="sticky top-0 bg-[#070d14]">
                            <tr className="border-b border-white/10 text-[#5c8494]">
                              <th className="text-left p-2 font-medium whitespace-nowrap">ID</th>
                              <th className="text-left p-2 font-medium whitespace-nowrap">Name</th>
                              <th className="text-left p-2 font-medium whitespace-nowrap">Formula</th>
                              <th className="text-center p-2 font-medium whitespace-nowrap">Rev?</th>
                              <th className="text-left p-2 font-medium whitespace-nowrap">EC</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredReactions.map((r) => (
                              <tr key={r.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                                <td className="p-2 font-mono-readout text-[#3ef2ff] whitespace-nowrap">{r.bigg_id}</td>
                                <td className="p-2 text-[#8cc3d4]">
                                  {r.name || <span className="text-[#5c8494] italic text-[10px]">Not yet catalogued</span>}
                                </td>
                                <td className="p-2 text-[#7dffef] font-mono-readout text-[10px] max-w-[200px]">
                                  {r.reaction_formula ? (
                                    <span className="break-all">{r.reaction_formula}</span>
                                  ) : (
                                    <span className="text-[#5c8494] italic">pending</span>
                                  )}
                                </td>
                                <td className="p-2 text-center text-[#8cc3d4]">{r.is_reversible ? '⇌' : '→'}</td>
                                <td className="p-2 font-mono-readout text-[#5c8494] whitespace-nowrap">
                                  {r.ec_number || <span className="text-[10px] italic">pending</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        </div>
                      </div>
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
