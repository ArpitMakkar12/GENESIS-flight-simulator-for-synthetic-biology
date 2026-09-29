'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/loading';

const API_BASE = 'http://localhost:8000/api/v1';

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
}

interface Pathway {
  subsystem: string;
  reaction_count: number;
}

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<'genes' | 'tfs' | 'pathways'>('genes');
  const [geneSearch, setGeneSearch] = useState('');
  const [genes, setGenes] = useState<Gene[]>([]);
  const [tfs, setTfs] = useState<TF[]>([]);
  const [pathways, setPathways] = useState<Pathway[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedGene, setSelectedGene] = useState<Gene | null>(null);

  const searchGenes = async () => {
    if (!geneSearch.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/genes?search=${encodeURIComponent(geneSearch)}&limit=50`);
      const data = await res.json();
      setGenes(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadTFs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tfs`);
      setTfs(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadPathways = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pathways`);
      setPathways(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  return (
    <div className="max-w-5xl page-enter">
      <h1 className="text-3xl font-semibold text-[#eaffff] mb-1 glow-text">Knowledge Base</h1>
      <p className="text-sm text-[#8cc3d4] mb-6">Explore E. coli K-12 genes, transcription factors, and metabolic pathways</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {(['genes', 'tfs', 'pathways'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              if (tab === 'tfs') loadTFs();
              if (tab === 'pathways') loadPathways();
            }}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all border ${
              activeTab === tab
                ? 'bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40'
                : 'bg-white/[0.04] text-[#8cc3d4] border-white/10 hover:bg-white/[0.07] hover:text-[#d9f7ff]'
            }`}
          >
            {tab === 'genes' ? '🧬 Genes' : tab === 'tfs' ? '🎛️ Transcription Factors' : '🔄 Pathways'}
          </button>
        ))}
      </div>

      {/* Gene Search Tab */}
      {activeTab === 'genes' && (
        <div>
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={geneSearch}
              onChange={(e) => setGeneSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchGenes()}
              placeholder="Search by gene name, locus tag, or product (e.g. lacZ, b0344, polymerase)"
              className="flex-1 px-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 transition-colors"
            />
            <button
              onClick={searchGenes}
              disabled={loading}
              className="px-5 py-2 rounded-full bg-[#3ef2ff]/15 text-[#7dffef] border border-[#3ef2ff]/40 text-sm font-medium hover:bg-[#3ef2ff]/25 transition-all disabled:opacity-50 shadow-[0_0_16px_-4px_rgba(62,242,255,0.3)]"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {genes.length > 0 && (
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
                        <td className="p-3 font-medium text-[#eaffff]">{g.name || '—'}</td>
                        <td className="p-3 text-[#8cc3d4] truncate max-w-xs">{g.product || '—'}</td>
                        <td className="p-3 text-right text-[#8cc3d4] font-mono-readout">{g.length_bp?.toLocaleString()}</td>
                        <td className="p-3 text-right text-[#8cc3d4] font-mono-readout">{g.gc_content ? (g.gc_content * 100).toFixed(1) + '%' : '—'}</td>
                        <td className="p-3 text-center font-mono-readout text-[#8cc3d4]">{g.strand}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-2 border-t border-white/[0.06] text-xs text-[#5c8494]">
                {genes.length} results found
              </div>
            </Card>
          )}

          {/* Gene Detail Panel */}
          {selectedGene && (
            <Card className="mt-4 p-5">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-[#3ef2ff]">
                  {selectedGene.name || selectedGene.locus_tag}
                </h3>
                <button onClick={() => setSelectedGene(null)} className="text-[#5c8494] hover:text-white transition-colors">✕</button>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-[#8cc3d4]">Locus Tag:</span> <span className="font-mono-readout text-[#eaffff]">{selectedGene.locus_tag}</span></div>
                <div><span className="text-[#8cc3d4]">Product:</span> <span className="text-[#eaffff]">{selectedGene.product}</span></div>
                <div><span className="text-[#8cc3d4]">Position:</span> <span className="font-mono-readout text-[#eaffff]">{selectedGene.start_pos.toLocaleString()} – {selectedGene.end_pos.toLocaleString()}</span></div>
                <div><span className="text-[#8cc3d4]">Strand:</span> <span className="text-[#eaffff]">{selectedGene.strand === '+' ? 'Forward (+)' : 'Reverse (−)'}</span></div>
                <div><span className="text-[#8cc3d4]">Length:</span> <span className="font-mono-readout text-[#eaffff]">{selectedGene.length_bp?.toLocaleString()} bp</span></div>
                <div><span className="text-[#8cc3d4]">GC Content:</span> <span className="font-mono-readout text-[#eaffff]">{selectedGene.gc_content ? (selectedGene.gc_content * 100).toFixed(1) + '%' : 'N/A'}</span></div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TFs Tab */}
      {activeTab === 'tfs' && (
        <div>
          {loading ? <div className="py-8"><Spinner /></div> : (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                      <th className="text-left p-3 font-medium uppercase tracking-wider">TF Name</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Family</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Sensing Signal</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Active Form</th>
                      <th className="text-center p-3 font-medium uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tfs.map((tf) => (
                      <tr key={tf.id} className="border-b border-white/[0.06] hover:bg-white/[0.04] transition-colors">
                        <td className="p-3 font-medium text-[#3ef2ff]">{tf.name}</td>
                        <td className="p-3">{tf.tf_family ? <span className="text-[#eaffff]">{tf.tf_family}</span> : <span className="text-[#5c8494] text-xs italic">—</span>}</td>
                        <td className="p-3">{tf.sensing_signal ? <span className="text-[#eaffff]">{tf.sensing_signal}</span> : <span className="text-[#5c8494] text-xs italic">—</span>}</td>
                        <td className="p-3">{tf.active_form ? <span className="text-[#eaffff]">{tf.active_form}</span> : <span className="text-[#5c8494] text-xs italic">—</span>}</td>
                        <td className="p-3 text-center">
                          {tf.tf_family || tf.sensing_signal || tf.active_form
                            ? <span className="px-2.5 py-0.5 text-[11px] rounded-full bg-[#3ef2ff]/10 text-[#7dffef] border border-[#3ef2ff]/25">Characterized</span>
                            : <span className="px-2.5 py-0.5 text-[11px] rounded-full bg-white/[0.05] text-[#5c8494] border border-white/10">Mapped</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-2 border-t border-white/[0.06] text-xs text-[#5c8494] flex justify-between">
                <span>{tfs.length} transcription factors</span>
                <span>Source: PRECISE-1K regulatory network</span>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Pathways Tab */}
      {activeTab === 'pathways' && (
        <div>
          {loading ? <div className="py-8"><Spinner /></div> : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {pathways.map((p) => (
                <Card key={p.subsystem} hover className="p-4">
                  <h3 className="font-medium text-sm mb-1 text-[#eaffff]">{p.subsystem}</h3>
                  <p className="text-2xl font-semibold text-[#3ef2ff] font-mono-readout glow-text">{p.reaction_count}</p>
                  <p className="text-xs text-[#5c8494]">reactions</p>
                </Card>
              ))}
              {pathways.length === 0 && !loading && (
                <p className="text-[#5c8494] col-span-3">No pathways loaded</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
