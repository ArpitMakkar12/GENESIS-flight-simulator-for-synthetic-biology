import type { Metadata } from "next";
import "./globals.css";
import Shell from "@/components/shell";

export const metadata: Metadata = {
  title: "GENESIS \u2014 A Flight Simulator for Synthetic Biology",
  description: "AI-powered in-silico simulation platform for E. coli gene expression and metabolic behavior prediction.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen text-[#eaffff] antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
