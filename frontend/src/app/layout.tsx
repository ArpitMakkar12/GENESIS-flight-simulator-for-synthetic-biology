import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "BioSandbox",
  description: "AI-powered E. coli simulation platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <nav className="w-64 border-r border-gray-800 bg-gray-900 p-6 flex flex-col gap-2">
            <Link href="/" className="text-xl font-bold text-green-400 mb-8">
              🧬 BioSandbox
            </Link>
            <NavLink href="/simulate">▶ Simulate</NavLink>
            <NavLink href="/parts">📦 Parts Library</NavLink>
            <NavLink href="/results">📊 Results</NavLink>
            <NavLink href="/knowledge">🧠 Knowledge Base</NavLink>
            <div className="mt-auto text-xs text-gray-600">
              v0.1.0 — E. coli K-12
            </div>
          </nav>
          {/* Main content */}
          <main className="flex-1 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="block px-4 py-2 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
    >
      {children}
    </Link>
  );
}
