import "./globals.css";
import { AnalysisProvider } from "@/context/AnalysisContext";
import Navbar from "@/components/Navbar";
import OOBModal from "@/components/OOBModal";

export const metadata = {
  title: "CrossShield — Fraud Intelligence Platform",
  description: "Multi-signal fraud campaign detection and out-of-band verification",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased relative">
        <AnalysisProvider>
          {/* Ambient animated background */}
          <div className="ambient-bg" />

          {/* App shell */}
          <div className="relative z-10 flex flex-col min-h-screen">
            <Navbar />
            <main className="flex-1 w-full max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
              {children}
            </main>
          </div>

          <OOBModal />
        </AnalysisProvider>
      </body>
    </html>
  );
}
