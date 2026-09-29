'use client';
import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Spinner, EmptyState } from '@/components/ui/loading';

const API_BASE = 'http://localhost:8000/api/v1';

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
  { key: null, label: 'All', icon: '\ud83d\udce6' },
  { key: 'promoter', label: 'Promoters', icon: '\u25b6\ufe0f' },
  { key: 'rbs', label: 'RBS', icon: '\ud83d\udfe2' },
  { key: 'cds', label: 'CDS', icon: '\ud83e\uddec' },
  { key: 'terminator', label: 'Terminators', icon: '\u23f9\ufe0f' },
];

export default function PartsPage() {
  const [parts, setParts] = useState<Part[]>([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<PartDetail | null>(null);

  useEffect(() => { loadParts(); }, [typeFilter]);

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

  return (
    <div className="max-w-5xl page-enter">
      <h1 className="text-3xl font-semibold text-[#eaffff] mb-1 glow-text">Parts Library</h1>
      <p className="text-sm text-[#8cc3d4] mb-6">Browse characterized genetic parts from iGEM Registry</p>

      {/* Type filter tabs */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {PART_TYPES.map((t) => (
          <button
            key={t.label}
            onClick={() => setTypeFilter(t.key)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all border ${
              typeFilter === t.key
                ? 'bg-[#3ef2ff]/15 text-[#7dffef] border-[#3ef2ff]/40'
                : 'bg-white/[0.04] text-[#8cc3d4] border-white/10 hover:bg-white/[0.07] hover:text-[#d9f7ff]'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-5">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && loadParts()}
          placeholder="Search parts by name..."
          className="flex-1 px-4 py-2.5 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-sm placeholder-[#5c8494] focus:outline-none focus:border-[#3ef2ff]/60 transition-colors"
        />
        <button onClick={loadParts} disabled={loading}
          className="px-5 py-2 rounded-full bg-[#3ef2ff]/15 text-[#7dffef] border border-[#3ef2ff]/40 text-sm font-medium hover:bg-[#3ef2ff]/25 transition-all disabled:opacity-50 shadow-[0_0_16px_-4px_rgba(62,242,255,0.3)]">
          {loading ? 'Loading...' : 'Search'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table */}
        <div className="lg:col-span-2">
          <Card className="overflow-hidden">
            {loading ? (
              <div className="py-8"><Spinner /></div>
            ) : filtered.length === 0 ? (
              <EmptyState icon="\ud83d\udce6" title="No parts found" description="Try a different search or filter." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-[#8cc3d4] text-xs">
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Name</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Type</th>
                      <th className="text-right p-3 font-medium uppercase tracking-wider">Length (bp)</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Source</th>
                      <th className="text-left p-3 font-medium uppercase tracking-wider">Strength</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((p) => (
                      <tr key={p.id} onClick={() => loadDetail(p.name)}
                        className={`border-b border-white/[0.06] cursor-pointer transition-colors hover:bg-white/[0.04] ${
                          selected?.id === p.id ? 'bg-[#3ef2ff]/[0.07] shadow-[inset_2px_0_0_0_#3ef2ff]' : ''
                        }`}>
                        <td className="p-3 text-[#3ef2ff] font-medium">{p.name}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 text-[11px] rounded-full border border-[#3ef2ff]/20 bg-[#3ef2ff]/[0.06] text-[#7dffef]">
                            {p.part_type}
                          </span>
                        </td>
                        <td className="p-3 text-right text-[#8cc3d4] font-mono-readout">{p.sequence_length?.toLocaleString() || '—'}</td>
                        <td className="p-3 text-[#5c8494] text-xs">{p.source || '—'}</td>
                        <td className="p-3">
                          {p.strength != null ? (
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                                <div className="h-full bg-[#3ef2ff] rounded-full" style={{ width: `${Math.min(p.strength * 100, 100)}%` }} />
                              </div>
                              <span className="text-xs text-[#8cc3d4] font-mono-readout w-8 text-right">{(p.strength * 100).toFixed(0)}%</span>
                            </div>
                          ) : <span className="text-[#5c8494]">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-4 py-2 border-t border-white/[0.06] text-xs text-[#5c8494]">
                  {filtered.length} parts
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Detail panel */}
        <div>
          {selected ? (
            <Card className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-[#3ef2ff]">{selected.name}</h3>
                <button onClick={() => setSelected(null)} className="text-[#5c8494] hover:text-white transition-colors">\u2715</button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                  <span className="text-[#8cc3d4]">Type</span>
                  <span className="text-[#eaffff]">{selected.part_type}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                  <span className="text-[#8cc3d4]">Length</span>
                  <span className="text-[#eaffff] font-mono-readout">{selected.sequence_length?.toLocaleString()} bp</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                  <span className="text-[#8cc3d4]">Source</span>
                  <span className="text-[#eaffff]">{selected.source || '\u2014'}</span>
                </div>
                {selected.registry_id && (
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-[#8cc3d4]">Registry ID</span>
                    <span className="text-[#3ef2ff] font-mono-readout">{selected.registry_id}</span>
                  </div>
                )}
                {selected.strength != null && (
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-[#8cc3d4]">Strength</span>
                    <span className="text-[#eaffff] font-mono-readout">{(selected.strength * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
              {selected.sequence && (
                <div className="mt-4">
                  <div className="text-xs text-[#8cc3d4] mb-2">Sequence</div>
                  <div className="p-3 rounded-lg bg-[#01070c]/60 border border-white/[0.08] text-[10px] text-[#7dffef] font-mono-readout break-all max-h-40 overflow-auto leading-relaxed">
                    {selected.sequence}
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card className="p-8 text-center border-dashed">
              <div className="text-3xl mb-3 opacity-30">\ud83e\uddec</div>
              <p className="text-sm text-[#5c8494]">Click a part to view details</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
