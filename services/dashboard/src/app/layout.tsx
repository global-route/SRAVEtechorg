import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "SRAVE Municipal Dashboard",
  description: "Spatial Revenue & Asset Verification Engine",
};

const NAV = [
  { href: "/",             label: "Overview" },
  { href: "/buildings",    label: "Buildings" },
  { href: "/assessments",  label: "Assessments" },
  { href: "/ingest",       label: "Ingest" },
  { href: "/audit",        label: "Audit Chain" },
  { href: "/reports",      label: "Reports" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-gray-50 text-gray-900">
        <aside className="w-56 shrink-0 bg-green-800 text-white flex flex-col">
          <div className="px-5 py-6 text-xl font-bold tracking-tight border-b border-green-700">
            SRAVE
          </div>
          <nav className="flex-1 py-4">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className="block px-5 py-3 text-sm hover:bg-green-700 transition-colors"
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="px-5 py-4 text-xs text-green-300 border-t border-green-700">
            Atlantic Tech Innovations
          </div>
        </aside>
        <main className="flex-1 p-8 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
