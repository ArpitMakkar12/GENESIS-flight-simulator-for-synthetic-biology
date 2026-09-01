export default function ResultsPage() {
  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Simulation Results</h1>

      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="text-left p-4">Date</th>
              <th className="text-left p-4">Construct</th>
              <th className="text-left p-4">Conditions</th>
              <th className="text-left p-4">Growth Rate</th>
              <th className="text-left p-4">Viability</th>
              <th className="text-left p-4">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} className="p-8 text-center text-gray-500">
                No simulations yet. Go to{" "}
                <a href="/simulate" className="text-green-400 hover:underline">
                  Simulate
                </a>{" "}
                to run your first simulation.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
