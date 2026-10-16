/*
 * Admin key for the live site.
 *
 * When the backend has ADMIN_KEY set, renaming and deleting saved runs needs
 * that key; everything else stays open to every visitor. Locally no key is
 * set, so nothing is locked.
 *
 * The key is kept in this browser only (localStorage), never in the code.
 */
import { useEffect, useState } from "react";
import { API } from "@/lib/api";

const STORAGE = "genesis-admin-key";
const CHANGED = "genesis-admin-changed";   // tells every open component to re-check

export interface AdminStatus {
  locked: boolean;     // the server has an admin key
  unlocked: boolean;   // this browser may rename and delete
}

/** Shown when a rename or delete is refused (HTTP 401). */
export const LOCKED_MESSAGE = "Saved runs are protected on the live site. Unlock them with the admin key on the Results page.";

export function getAdminKey(): string {
  try {
    return localStorage.getItem(STORAGE) ?? "";
  } catch {
    return "";   // private window or blocked storage
  }
}

export function setAdminKey(key: string | null): void {
  try {
    if (key) localStorage.setItem(STORAGE, key);
    else localStorage.removeItem(STORAGE);
  } catch {
    /* storage blocked: the key just isn't remembered */
  }
  window.dispatchEvent(new Event(CHANGED));
}

/** Headers to add to a rename or delete request. */
export function adminHeaders(): Record<string, string> {
  const key = getAdminKey();
  return key ? { "X-Admin-Key": key } : {};
}

export async function fetchAdminStatus(key: string = getAdminKey()): Promise<AdminStatus> {
  const res = await fetch(`${API}/admin/status`, { headers: key ? { "X-Admin-Key": key } : {} });
  if (!res.ok) throw new Error(`Status check failed (${res.status})`);
  return res.json();
}

/** Is editing locked here, and may this browser edit? Re-checks after unlock/lock. */
export function useAdmin(): { status: AdminStatus | null; canEdit: boolean } {
  const [status, setStatus] = useState<AdminStatus | null>(null);

  useEffect(() => {
    let alive = true;
    const check = () =>
      fetchAdminStatus()
        .then((s) => { if (alive) setStatus(s); })
        .catch(() => { if (alive) setStatus(null); });
    check();
    window.addEventListener(CHANGED, check);
    return () => { alive = false; window.removeEventListener(CHANGED, check); };
  }, []);

  // Hidden until the answer arrives, so visitors never see buttons flash
  return { status, canEdit: status?.unlocked ?? false };
}