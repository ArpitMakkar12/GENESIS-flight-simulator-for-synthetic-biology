'use client';
import { useState } from 'react';

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

  const lookupGene = async (identifier: string) => {
    try {
      const res = await fetch(`${API_BASE}/genes/${encodeURIComponent(identifier)}`);
      if (res.ok) setSelectedGene(await res.json());
    } catch (e) { console.error(e); }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Knowledge Base</h1>

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
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === tab
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
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
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
            />
            <button
              onClick={searchGenes}
              disabled={loading}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {genes.length > 0 && (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left">Locus Tag</th>
                    <th className="px-4 py-3 text-left">Gene Name</th>
                    <th className="px-4 py-3 text-left">Product</th>
                    <th className="px-4 py-3 text-right">Length (bp)</th>
                    <th className="px-4 py-3 text-right">GC%</th>
                    <th className="px-4 py-3 text-center">Strand</th>
                  </tr>
                </thead>
                <tbody>
                  {genes.map((g) => (
                    <tr
                      key={g.id}
                      onClick={() => setSelectedGene(g)}
                      className="border-t border-gray-700 hover:bg-gray-750 cursor-pointer hover:bg-gray-700"
                    >
                      <td className="px-4 py-2 font-mono text-green-400">{g.locus_tag}</td>
                      <td className="px-4 py-2 font-medium">{g.name || '—'}</td>
                      <td className="px-4 py-2 text-gray-300 truncate max-w-xs">{g.product || '—'}</td>
                      <td className="px-4 py-2 text-right">{g.length_bp?.toLocaleString()}</td>
                      <td className="px-4 py-2 text-right">{g.gc_content ? (g.gc_content * 100).toFixed(1) + '%' : '—'}</td>
                      <td className="px-4 py-2 text-center font-mono">{g.strand}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-2 bg-gray-700 text-sm text-gray-400">
                {genes.length} results found
              </div>
            </div>
          )}

          {/* Gene Detail Panel */}
          {selectedGene && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-bold text-green-400">
                  {selectedGene.name || selectedGene.locus_tag}
                </h3>
                <button onClick={() => setSelectedGene(null)} className="text-gray-400 hover:text-white">✕</button>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-400">Locus Tag:</span> <span className="font-mono">{selectedGene.locus_tag}</span></div>
                <div><span className="text-gray-400">Product:</span> {selectedGene.product}</div>
                <div><span className="text-gray-400">Position:</span> {selectedGene.start_pos.toLocaleString()} – {selectedGene.end_pos.toLocaleString()}</div>
                <div><span className="text-gray-400">Strand:</span> {selectedGene.strand === '+' ? 'Forward (+)' : 'Reverse (−)'}</div>
                <div><span className="text-gray-400">Length:</span> {selectedGene.length_bp?.toLocaleString()} bp</div>
                <div><span className="text-gray-400">GC Content:</span> {selectedGene.gc_content ? (selectedGene.gc_content * 100).toFixed(1) + '%' : 'N/A'}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TFs Tab */}
      {activeTab === 'tfs' && (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left">TF Name</th>
                <th className="px-4 py-3 text-left">Family</th>
                <th className="px-4 py-3 text-left">Sensing Signal</th>
                <th className="px-4 py-3 text-left">Active Form</th>
              </tr>
            </thead>
            <tbody>
              {tfs.map((tf) => (
                <tr key={tf.id} className="border-t border-gray-700 hover:bg-gray-700">
                  <td className="px-4 py-2 font-medium text-green-400">{tf.name}</td>
                  <td className="px-4 py-2 text-gray-300">{tf.tf_family || '—'}</td>
                  <td className="px-4 py-2 text-gray-300">{tf.sensing_signal || '—'}</td>
                  <td className="px-4 py-2 text-gray-300">{tf.active_form || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-2 bg-gray-700 text-sm text-gray-400">
            {tfs.length} transcription factors
          </div>
        </div>
      )}

      {/* Pathways Tab */}
      {activeTab === 'pathways' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {pathways.map((p) => (
            <div key={p.subsystem} className="p-4 bg-gray-800 rounded-lg border border-gray-700 hover:border-green-600 transition cursor-pointer">
              <h3 className="font-medium text-sm mb-1">{p.subsystem}</h3>
              <p className="text-2xl font-bold text-green-400">{p.reaction_count}</p>
              <p className="text-xs text-gray-400">reactions</p>
            </div>
          ))}
          {pathways.length === 0 && !loading && (
            <p className="text-gray-400 col-span-3">No pathways loaded</p>
          )}
        </div>
      )}
    </div>
  );
}
