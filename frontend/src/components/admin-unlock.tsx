"use client";

/*
 * The admin's way in on the live site: enter the key once, and this browser
 * may rename and delete saved runs. Shows nothing when no key is set on the
 * server (local development), because then nothing is locked.
 */
import { useState } from "react";
import { Lock, LockOpen } from "lucide-react";
import { fetchAdminStatus, setAdminKey, useAdmin } from "@/lib/admin";

export function AdminUnlock() {
  const { status } = useAdmin();
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!status?.locked) return null;

  const pill = "inline-flex items-center gap-1.5 px-3 py-1 text-xs rounded-xl border transition-colors";

  if (status.unlocked) {
    return (
      <button
        type="button"
        onClick={() => setAdminKey(null)}
        className={`${pill} bg-[#3ef2ff]/10 text-[#7dffef] border-[#3ef2ff]/30 hover:bg-[#3ef2ff]/20`}
        title="Forget the admin key in this browser"
      >
        <LockOpen className="h-3.5 w-3.5" aria-hidden="true" />
        Admin · Lock
      </button>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`${pill} bg-white/[0.04] text-[#8cc3d4] border-white/10 hover:bg-white/[0.08]`}
        title="Rename and delete saved runs"
      >
        <Lock className="h-3.5 w-3.5" aria-hidden="true" />
        Admin
      </button>
    );
  }

  const unlock = async () => {
    setChecking(true);
    setError(null);
    try {
      const result = await fetchAdminStatus(key.trim());
      if (result.unlocked) {
        setAdminKey(key.trim());
        setOpen(false);
        setKey("");
      } else {
        setError("Wrong key");
      }
    } catch {
      setError("Could not reach the server");
    } finally {
      setChecking(false);
    }
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); unlock(); }}
      className="inline-flex items-center gap-2 flex-wrap"
    >
      <input
        type="password"
        autoFocus
        value={key}
        onChange={(e) => setKey(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}
        placeholder="Admin key"
        aria-label="Admin key"
        className="w-44 px-3 py-1 rounded-xl bg-[#01070c]/60 border border-white/10 text-[#eaffff] text-xs focus:border-[#3ef2ff]/60 focus:outline-none"
      />
      <button
        type="submit"
        disabled={checking || !key.trim()}
        className={`${pill} bg-[#3ef2ff]/10 text-[#7dffef] border-[#3ef2ff]/30 hover:bg-[#3ef2ff]/20 disabled:opacity-40`}
      >
        {checking ? "Checking…" : "Unlock"}
      </button>
      <button type="button" onClick={() => setOpen(false)} className="text-xs text-[#5c8494] hover:text-[#eaffff]">
        Cancel
      </button>
      {error && <span className="w-full text-xs text-[#ff8b6e]">{error}</span>}
    </form>
  );
}