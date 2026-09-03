'use client';
import { useState, useEffect } from 'react';

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
  { key: null, label: 'All', icon: '📦' },
  { key: 'promoter', label: 'Promoters', icon: '▶️' },
  { key: 'rbs', label: 'RBS', icon: '🔵' },
  { key: 'cds', label: 'CDS', icon: '🧬' },
  { key: 'terminator', label: 'Terminators', icon: '⏹️' },
];

export default function PartsPage() {
  const [parts, setParts] = useState<Part[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedPart, setSelectedPart] = useState<PartDetail | null>(null);

  const loadParts = async (type: string | null = selectedType, searchTerm: string = search) => {
    try {
      const params = new URLSearchParams();
      if (type) params.set('part_type', type);
      if (searchTerm) params.set('search', searchTerm);
      params.set('limit', '50');

      const res = await fetch(`${API_BASE}/parts?${params.toString()}`);
      const data = await res.json();
      setParts(data.parts);
      setTotal(data.total);
    } catch (e) { console.error(e); }
  };

  const loadPartDetail = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/parts/${encodeURIComponent(name)}`);
      if (res.ok) setSelectedPart(await res.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    // Initial load — fetch all parts
    const init = async () => {
      try {
        const res = await fetch(`${API_BASE}/parts?limit=50`);
        const data = await res.json();
        setParts(data.parts);
        setTotal(data.total);
      } catch (e) { console.error(e); }
    };
    init();
  }, []);

  const strengthBar = (strength: number | null) => {
    if (strength === null || strength === undefined) return null;
    return (
      <div className="flex items-center gap-2">
        <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full"
            style={{ width: `${Math.min(strength * 100, 100)}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{(strength * 100).toFixed(0)}%</span>
      </div>
    );
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Parts Library</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        {PART_TYPES.map((t) => (
          <button
            key={t.label}
            onClick={() => { setSelectedType(t.key); loadParts(t.key, search); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              selectedType === t.key
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && loadParts(selectedType, search)}
          placeholder="Search parts by name (e.g., BBa_J23100)"
          className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
        />
        <button
          onClick={() => loadParts(selectedType, search)}
          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
        >
          Search
        </button>
      </div>

      {/* Parts Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-right">Length (bp)</th>
              <th className="px-4 py-3 text-left">Strength</th>
              <th className="px-4 py-3 text-left">Details</th>
            </tr>
          </thead>
          <tbody>
            {parts.map((p) => (
              <tr
                key={p.id}
                onClick={() => loadPartDetail(p.name)}
                className="border-t border-gray-700 hover:bg-gray-700 cursor-pointer"
              >
                <td className="px-4 py-2 font-mono text-green-400 font-medium">{p.name}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    p.part_type === 'promoter' ? 'bg-blue-900 text-blue-300' :
                    p.part_type === 'rbs' ? 'bg-purple-900 text-purple-300' :
                    p.part_type === 'cds' ? 'bg-orange-900 text-orange-300' :
                    'bg-red-900 text-red-300'
                  }`}>
                    {p.part_type.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-300">{p.source || '—'}</td>
                <td className="px-4 py-2 text-right">{p.sequence_length || '—'}</td>
                <td className="px-4 py-2">{strengthBar(p.strength)}</td>
                <td className="px-4 py-2 text-gray-400 text-xs">
                  {p.annotations?.inducer && `Inducer: ${p.annotations.inducer}`}
                  {p.annotations?.RPU !== undefined && `RPU: ${p.annotations.RPU}`}
                  {p.annotations?.protein && `Protein: ${p.annotations.protein}`}
                  {p.annotations?.efficiency !== undefined && `Eff: ${(p.annotations.efficiency * 100).toFixed(0)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4 py-2 bg-gray-700 text-sm text-gray-400">
          {total} parts total — showing {parts.length}
        </div>
      </div>

      {/* Part Detail Modal */}
      {selectedPart && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-bold text-green-400">{selectedPart.name}</h3>
            <button onClick={() => setSelectedPart(null)} className="text-gray-400 hover:text-white">✕</button>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div><span className="text-gray-400">Type:</span> {selectedPart.part_type}</div>
            <div><span className="text-gray-400">Source:</span> {selectedPart.source}</div>
            <div><span className="text-gray-400">Length:</span> {selectedPart.sequence_length ? `${selectedPart.sequence_length} bp` : 'N/A'}</div>
            <div><span className="text-gray-400">Strength:</span> {selectedPart.strength !== null ? `${(selectedPart.strength * 100).toFixed(0)}%` : 'N/A'}</div>
          </div>
          {selectedPart.sequence && selectedPart.sequence !== 'N/A' && (
            <div>
              <p className="text-gray-400 text-xs mb-1">Sequence:</p>
              <pre className="bg-gray-900 p-3 rounded font-mono text-xs text-green-300 break-all whitespace-pre-wrap">
                {selectedPart.sequence}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
