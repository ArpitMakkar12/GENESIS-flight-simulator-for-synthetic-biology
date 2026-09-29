"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/simulate", label: "Simulate" },
  { href: "/results", label: "Results" },
  { href: "/parts", label: "Parts" },
  { href: "/knowledge", label: "Knowledge" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top nav bar ───────────────────────────── */}
      <header className="sticky top-0 z-50 w-full bg-[#01070c]/80 backdrop-blur-xl border-b border-white/[0.07]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2" onClick={() => setMobileOpen(false)}>
            <span className="text-lg font-semibold tracking-[0.08em] text-[#eaffff]">GENESIS</span>
          </Link>

          {/* Desktop nav pill */}
          <nav className="hidden sm:flex items-center gap-1 rounded-full px-1.5 py-1 border border-white/10 bg-white/[0.06] backdrop-blur-lg">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3.5 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                    isActive
                      ? "bg-white/[0.14] text-white shadow-sm"
                      : "text-[#8cc3d4] hover:text-[#d9f7ff] hover:bg-white/[0.06]"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="sm:hidden text-[#8cc3d4] hover:text-white p-1 transition-colors"
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div className="sm:hidden border-t border-white/10 bg-[#031722]/90 backdrop-blur-xl">
            <div className="flex flex-col px-4 py-3 gap-1">
              {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? "bg-[#3ef2ff]/10 text-[#7dffef] border border-[#3ef2ff]/25"
                        : "text-[#8cc3d4] hover:bg-white/[0.05] hover:text-white border border-transparent"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
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
