export default function HomePage() {
  return (
    <div className="max-w-4xl">
      <h1 className="text-4xl font-bold text-white mb-4">
        Welcome to BioSandbox
      </h1>
      <p className="text-lg text-gray-400 mb-8">
        AI-powered in-silico simulation platform for{" "}
        <span className="text-green-400 font-semibold">E. coli</span> gene
        expression and metabolic behavior prediction.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DashCard
          title="🧪 Run Simulation"
          description="Input DNA constructs, set environmental conditions, and predict gene expression + metabolic flux."
          href="/simulate"
        />
        <DashCard
          title="📦 Parts Library"
          description="Browse characterized genetic parts from iGEM Registry and EcoCyc."
          href="/parts"
        />
        <DashCard
          title="📊 Results History"
          description="View and compare past simulation results."
          href="/results"
        />
        <DashCard
          title="🧠 Knowledge Base"
          description="Explore E. coli genes, regulatory networks, and metabolic pathways."
          href="/knowledge"
        />
      </div>

      <div className="mt-12 p-6 rounded-xl border border-gray-800 bg-gray-900">
        <h2 className="text-lg font-semibold text-gray-200 mb-3">
          System Status
        </h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <StatusItem label="API" status="checking" />
          <StatusItem label="Database" status="checking" />
          <StatusItem label="AI Models" status="not loaded" />
        </div>
      </div>
    </div>
  );
}

function DashCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="block p-6 rounded-xl border border-gray-800 bg-gray-900 hover:border-green-600 hover:bg-gray-800 transition-all"
    >
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-gray-400">{description}</p>
    </a>
  );
}

function StatusItem({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  const color = status === "online" ? "text-green-400" : "text-yellow-400";
  return (
    <div>
      <div className="text-gray-500">{label}</div>
      <div className={`font-mono ${color}`}>{status}</div>
    </div>
  );
}
