"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/",         label: "Input",    icon: "01" },
  { href: "/analysis", label: "Analysis", icon: "02" },
  { href: "/graph",    label: "Graph",    icon: "03" },
  { href: "/score",    label: "Score",    icon: "04" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="relative z-20 glass-card-subtle border-b border-white/[0.04] rounded-none">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 flex items-center justify-between h-16">
        {/* Brand */}
        <div className="flex items-center gap-3">
          {/* Shield icon */}
          <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[15px] font-semibold tracking-[-0.01em] text-white">
              CrossShield
            </h1>
            <div className="hidden sm:block h-4 w-px bg-white/10" />
            <span className="hidden sm:block text-[11px] font-medium text-slate-500 tracking-wide uppercase">
              Fraud Intelligence
            </span>
          </div>
        </div>

        {/* Navigation — underline style */}
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href} className="relative group">
                <div
                  className={`px-4 py-2 text-[13px] font-medium transition-colors flex items-center gap-2 ${
                    active ? "text-white" : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <span className={`text-[10px] font-mono ${active ? "text-accent" : "text-slate-600"}`}>
                    {icon}
                  </span>
                  {label}
                </div>
                {/* Active underline */}
                <div
                  className={`absolute bottom-0 left-2 right-2 h-[2px] rounded-full transition-all ${
                    active
                      ? "bg-accent opacity-100"
                      : "bg-transparent opacity-0 group-hover:bg-slate-700 group-hover:opacity-100"
                  }`}
                />
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
