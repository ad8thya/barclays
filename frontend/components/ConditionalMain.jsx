"use client";
import { usePathname } from "next/navigation";

export default function ConditionalMain({ children }) {
  const pathname = usePathname();
  if (pathname === "/") return <>{children}</>;
  return (
    <main className="flex-1 w-full max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
      {children}
    </main>
  );
}