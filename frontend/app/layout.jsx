import "./globals.css";
import { AnalysisProvider } from "@/context/AnalysisContext";
import Navbar from "@/components/layout/Navbar";

export const metadata = {
  title: "CrossShield — Fraud Intelligence Platform",
  description: "Multi-signal fraud campaign detection and out-of-band verification",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased" style={{ background: "#080d1a", color: "#e2e8f0" }}>
        <AnalysisProvider>
          <div className="relative min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1">
              {children}
            </main>
          </div>
        </AnalysisProvider>
      </body>
    </html>
  );
}
