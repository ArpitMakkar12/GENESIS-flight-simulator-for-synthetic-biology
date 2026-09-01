export default function KnowledgePage() {
  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Knowledge Base</h1>
      <p className="text-gray-400 mb-8">
        Explore E. coli genes, transcription factors, regulatory networks, and
        metabolic pathways.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <KnowledgeCard
          title="🧬 Genes"
          count="~4,700"
          description="E. coli K-12 MG1655 genome — all coding and non-coding genes with annotations."
          endpoint="/api/v1/genes"
        />
        <KnowledgeCard
          title="🔌 Transcription Factors"
          count="~300"
          description="Regulatory proteins from RegulonDB with sensing signals and active conditions."
          endpoint="/api/v1/tfs"
        />
        <KnowledgeCard
          title="⚗️ Reactions"
          count="~2,712"
          description="Metabolic reactions from the iML1515 genome-scale model."
          endpoint="/api/v1/pathways"
        />
        <KnowledgeCard
          title="🚪 Transporters"
          count="~400"
          description="Membrane transport proteins classified by TCDB with substrate and ATP cost data."
          endpoint="/api/v1/transporters"
        />
      </div>

      {/* Gene search */}
      <div className="mt-8 p-6 rounded-xl border border-gray-800 bg-gray-900">
        <h2 className="text-lg font-semibold text-gray-200 mb-4">
          Gene Lookup
        </h2>
        <input
          type="text"
          placeholder="Search by locus tag (e.g. b0001) or gene name (e.g. lacZ)..."
          className="w-full p-3 rounded-lg bg-gray-950 border border-gray-700 text-white placeholder-gray-500 focus:border-green-500 focus:outline-none"
        />
        <p className="mt-2 text-xs text-gray-500">
          Database will be populated after running seed scripts.
        </p>
      </div>
    </div>
  );
}

function KnowledgeCard({
  title,
  count,
  description,
  endpoint,
}: {
  title: string;
  count: string;
  description: string;
  endpoint: string;
}) {
  return (
    <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <span className="text-xs font-mono text-green-400 bg-green-400/10 px-2 py-1 rounded">
          {count}
        </span>
      </div>
      <p className="text-sm text-gray-400 mb-3">{description}</p>
      <code className="text-xs text-gray-600">{endpoint}</code>
    </div>
  );
}
