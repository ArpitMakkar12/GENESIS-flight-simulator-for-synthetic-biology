export default function PartsPage() {
  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Parts Library</h1>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <FilterButton label="All" active />
        <FilterButton label="Promoters" />
        <FilterButton label="RBS" />
        <FilterButton label="CDS" />
        <FilterButton label="Terminators" />
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search parts by name..."
        className="w-full p-3 rounded-lg bg-gray-900 border border-gray-700 text-white placeholder-gray-500 mb-6 focus:border-green-500 focus:outline-none"
      />

      {/* Parts table placeholder */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="text-left p-4">Name</th>
              <th className="text-left p-4">Type</th>
              <th className="text-left p-4">Source</th>
              <th className="text-left p-4">Strength</th>
              <th className="text-left p-4">Length</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={5} className="p-8 text-center text-gray-500">
                Parts library will be populated after data seeding.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterButton({
  label,
  active = false,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`px-4 py-2 rounded-lg text-sm transition-colors ${
        active
          ? "bg-green-600 text-white"
          : "bg-gray-800 text-gray-400 hover:bg-gray-700"
      }`}
    >
      {label}
    </button>
  );
}
