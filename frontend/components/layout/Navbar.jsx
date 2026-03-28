"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/input", label: "Input" },
  { href: "/analysis", label: "Analysis" },
  { href: "/graph", label: "Graph" },
  { href: "/score", label: "Score" },
];

export default function Navbar() {
  const pathname = usePathname();

  // Hide on landing
  if (pathname === "/") return null;

  return (
    <header
      className="sticky top-0 z-50 border-b border-white/[0.06]"
      style={{
        background: "rgba(8,13,26,0.8)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 h-14 flex items-center justify-between">
        {/* Left: brand */}
        <Link href="/" className="flex items-center gap-3 no-underline">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.8">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span className="text-[15px] font-medium text-white tracking-tight">
            CrossShield
          </span>
          <span className="w-px h-4 bg-white/[0.08]" />
          <span className="text-[12px] text-slate-500 tracking-tight hidden sm:inline">
            Fraud Intelligence Platform
          </span>
        </Link>

        {/* Right: nav links */}
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`px-4 py-2 text-[12px] uppercase tracking-[0.08em] font-medium transition-colors border-b-2 ${
                  active
                    ? "text-slate-100 border-accent"
                    : "text-slate-500 border-transparent hover:text-slate-300"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
