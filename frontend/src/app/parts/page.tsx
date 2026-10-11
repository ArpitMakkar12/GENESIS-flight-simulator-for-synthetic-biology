import { redirect } from "next/navigation";

/**
 * Parts moved into the Library. This keeps old links and bookmarks working:
 * /parts → /library?tab=parts (and /parts?part=X → that part).
 */
export default function PartsRedirect({ searchParams }: { searchParams: { part?: string } }) {
  const part = searchParams.part ? `&part=${encodeURIComponent(searchParams.part)}` : "";
  redirect(`/library?tab=parts${part}`);
}