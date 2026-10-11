import { redirect } from "next/navigation";

/**
 * The Knowledge Base moved into the Library (Genes, Transcription Factors and
 * Pathways tabs). This keeps old links and bookmarks working:
 * /knowledge → /library?tab=genes (and /knowledge?gene=X → that gene).
 */
export default function KnowledgeRedirect({ searchParams }: { searchParams: { gene?: string } }) {
  const gene = searchParams.gene ? `&gene=${encodeURIComponent(searchParams.gene)}` : "";
  redirect(`/library?tab=genes${gene}`);
}