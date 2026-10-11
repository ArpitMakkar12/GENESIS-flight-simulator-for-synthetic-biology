"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Blocks, Dna, Network, Workflow, type LucideIcon } from "lucide-react";
import { PartsTab } from "@/components/library/parts-tab";
import { KnowledgeTabs } from "@/components/library/knowledge-tabs";
import { Spinner } from "@/components/ui/loading";

type Tab = "parts" | "genes" | "tfs" | "pathways";

const TABS: { key: Tab; label: string; Icon: LucideIcon; hint: string }[] = [
  { key: "parts",    label: "Parts",                 Icon: Blocks,   hint: "Promoters, RBS, CDS and terminators from iGEM" },
  { key: "genes",    label: "Genes",                 Icon: Dna,      hint: "E. coli K-12 genes" },
  { key: "tfs",      label: "Transcription Factors", Icon: Network,  hint: "Regulators and the genes they control" },
  { key: "pathways", label: "Pathways",              Icon: Workflow, hint: "Metabolic pathways and their reactions" },
];

function isTab(value: string | null): value is Tab {
  return TABS.some((t) => t.key === value);
}

/**
 * The Library: reference data in one place.
 *
 * Everything lives in the URL, so any view can be linked to:
 *   /library?tab=parts&part=BBa_J23100   opens that part
 *   /library?tab=genes&gene=b0903        searches and opens that gene
 *   /library?tab=tfs&tf=FNR              opens that regulator
 *   /library?tab=pathways&pathway=...    opens that pathway
 */
function LibraryContent() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("tab");
  const tab: Tab = isTab(raw) ? raw : "parts";

  // Switching tabs keeps only the tab in the URL, so an old ?gene=... doesn't
  // re-open when you come back. replace() keeps the back button tidy.
  const selectTab = (next: Tab) => {
    router.replace(`/library?tab=${next}`, { scroll: false });
  };

  return (
    <div className="max-w-5xl page-enter">
      <h1 className="text-3xl font-semibold text-[#eaffff] mb-1 glow-text">Library</h1>
      <p className="text-sm text-[#8cc3d4] mb-6">
        Reference data behind every simulation: genetic parts from iGEM, and the E. coli K-12 genes,
        regulators and pathways the model is built on.
      </p>

      {/* Main tabs: an underlined bar, so the smaller filter pills inside a tab read as a second level */}
      <div role="tablist" aria-label="Library sections" className="mb-6 flex items-end gap-1 overflow-x-auto border-b border-white/[0.08]">
        {TABS.map((t, i) => {
          const active = tab === t.key;
          return (
            <div key={t.key} className="flex items-end">
              {/* thin divider between the iGEM parts and the E. coli data */}
              {i === 1 && <span aria-hidden="true" className="mx-2 mb-3 h-4 w-px bg-white/10" />}
              <button
                role="tab"
                aria-selected={active}
                title={t.hint}
                onClick={() => selectTab(t.key)}
                className={`-mb-px inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-[#3ef2ff] text-[#eaffff]"
                    : "border-transparent text-[#8cc3d4] hover:text-[#d9f7ff] hover:border-white/20"
                }`}
              >
                <t.Icon className={`h-4 w-4 shrink-0 ${active ? "text-[#7dffef]" : ""}`} strokeWidth={1.75} aria-hidden="true" />
                {t.label}
              </button>
            </div>
          );
        })}
      </div>

      {tab === "parts" ? (
        <PartsTab initialPart={params.get("part")} />
      ) : (
        // One component for the three E. coli tabs, so a search you typed in
        // Genes is still there after a look at Pathways
        <KnowledgeTabs
          tab={tab}
          initialGene={params.get("gene")}
          initialTf={params.get("tf")}
          initialPathway={params.get("pathway")}
        />
      )}
    </div>
  );
}

// useSearchParams needs a Suspense boundary in the Next.js App Router
export default function LibraryPage() {
  return (
    <Suspense fallback={<div className="py-16"><Spinner /></div>}>
      <LibraryContent />
    </Suspense>
  );
}