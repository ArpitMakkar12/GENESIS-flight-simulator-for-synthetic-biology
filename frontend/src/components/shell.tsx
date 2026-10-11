"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Library } from "lucide-react";

// The main path through the app: run a simulation, then look at results
const NAV_ITEMS = [
  { href: "/simulate", label: "Simulate" },
  { href: "/results", label: "Results" },
];

// Reference data, kept apart on the right (Parts, Genes, TFs, Pathways)
const LIBRARY = { href: "/library", label: "Library" };

function isActivePath(pathname: string | null, href: string) {
  return pathname === href || (href !== "/" && !!pathname?.startsWith(href));
}

/**
 * The GENESIS mark: a small rod-shaped cell with its flagellum, the same
 * organism that drifts across the home page hero. It ties every page
 * back to the thing being simulated.
 */
function CellMark() {
  return (
    <svg
      viewBox="-2 0 34 16"
      className="h-[18px] w-auto overflow-visible"
      aria-hidden="true"
      style={{ filter: "drop-shadow(0 0 4px rgba(62, 242, 255, 0.55))" }}
    >
      {/* flagellum */}
      <path d="M8 8 C5 4.5 3 11.5 0 8" fill="none" stroke="#7dffef" strokeOpacity="0.7" strokeWidth="1" strokeLinecap="round" />
      {/* cell wall */}
      <rect x="8" y="2" width="22" height="12" rx="6" fill="rgba(62, 242, 255, 0.10)" stroke="#3ef2ff" strokeWidth="1.3" />
      {/* DNA inside */}
      <path d="M12 8 C14 5 16 11 18.5 8 S23 5 26 8" fill="none" stroke="#c9fff9" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

/** Desktop nav link. The active page gets a glowing bar on the header's bottom edge. */
function NavLink({
  href,
  active,
  children,
  title,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <Link
      href={href}
      title={title}
      aria-current={active ? "page" : undefined}
      className={`group relative flex h-full items-center gap-2 px-3.5 text-[13px] font-medium transition-colors
        focus-visible:outline-none focus-visible:text-[#eaffff] ${
        active ? "text-[#eaffff]" : "text-[#8cc3d4] hover:text-[#eaffff]"
      }`}
    >
      {/* hover / keyboard-focus wash, kept inside the bar so it never touches the edge */}
      <span
        aria-hidden="true"
        className="absolute inset-x-1 inset-y-3 rounded-lg bg-white/[0.05] opacity-0 transition-opacity
                   group-hover:opacity-100 group-focus-visible:opacity-100 group-focus-visible:ring-1 group-focus-visible:ring-[#3ef2ff]/50"
      />
      <span className="relative flex items-center gap-2">{children}</span>
      {/* the active indicator: sits exactly on the header's bottom border */}
      <span
        aria-hidden="true"
        className={`absolute inset-x-3 -bottom-px h-[2px] rounded-full bg-[#3ef2ff] shadow-[0_0_10px_rgba(62,242,255,0.8)] transition-opacity ${
          active ? "opacity-100" : "opacity-0"
        }`}
      />
    </Link>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const onHome = pathname === "/";

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top nav bar ───────────────────────────── */}
      <header className="sticky top-0 z-50 w-full bg-[#01070c]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-6xl items-stretch justify-between px-4 sm:px-6">
          {/* Brand: the cell mark + wordmark */}
          <Link
            href="/"
            onClick={() => setMobileOpen(false)}
            aria-current={onHome ? "page" : undefined}
            className="flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#3ef2ff]/50"
          >
            <CellMark />
            <span className="text-[17px] font-semibold tracking-[0.14em] text-[#eaffff]">GENESIS</span>
          </Link>

          {/* Desktop: the main path, a divider, then the Library */}
          <div className="hidden sm:flex items-stretch">
            <nav aria-label="Main" className="flex items-stretch">
              {NAV_ITEMS.map((item) => (
                <NavLink key={item.href} href={item.href} active={isActivePath(pathname, item.href)}>
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <span aria-hidden="true" className="mx-2 my-auto h-5 w-px bg-white/15" />

            <NavLink
              href={LIBRARY.href}
              active={isActivePath(pathname, LIBRARY.href)}
              title="Parts, genes, transcription factors and pathways"
            >
              <Library className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              {LIBRARY.label}
            </NavLink>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="sm:hidden my-auto rounded-lg p-1.5 text-[#8cc3d4] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#3ef2ff]/50"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              {mobileOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>

        {/* Bottom edge: a cyan hairline that fades out at both ends */}
        <div
          aria-hidden="true"
          className="h-px w-full bg-gradient-to-r from-transparent via-[#3ef2ff]/25 to-transparent"
        />

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div className="sm:hidden border-b border-white/10 bg-[#031722]/95 backdrop-blur-xl">
            <nav aria-label="Main" className="flex flex-col px-4 py-3 gap-1">
              {[...NAV_ITEMS, LIBRARY].map((item) => {
                const isActive = isActivePath(pathname, item.href);
                const isLibrary = item.href === LIBRARY.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    aria-current={isActive ? "page" : undefined}
                    className={`relative flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
                      isLibrary ? "mt-2 before:absolute before:-top-1.5 before:left-4 before:right-4 before:h-px before:bg-white/10" : ""
                    } ${
                      isActive
                        ? "bg-[#3ef2ff]/10 text-[#eaffff]"
                        : "text-[#8cc3d4] hover:bg-white/[0.05] hover:text-white"
                    }`}
                  >
                    {/* same glowing indicator as desktop, standing upright on the left */}
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-[#3ef2ff] shadow-[0_0_8px_rgba(62,242,255,0.8)]"
                      />
                    )}
                    {isLibrary && <Library className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />}
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </header>

      {/* ── Main content ──────────────────────────── */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {children}
      </main>

      {/* ── Footer ────────────────────────────────── */}
      <footer className="w-full max-w-6xl mx-auto px-4 sm:px-6 pb-6">
        <div className="text-[10px] text-[#5c8494] text-center">
          GENESIS v1.0.0 · E. coli K-12 MG1655 · iML1515
        </div>
      </footer>
    </div>
  );
}