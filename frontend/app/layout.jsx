import "./globals.css";
import { AnalysisProvider } from "@/context/AnalysisContext";
import ConditionalNavbar from "@/components/ConditionalNavbar";
import ConditionalMain from "@/components/ConditionalMain";
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
          <div className="ambient-bg" />
          <div className="relative z-10 flex flex-col min-h-screen">
            <ConditionalNavbar />
            <ConditionalMain>{children}</ConditionalMain>
          </div>
          <OOBModal />
        </AnalysisProvider>
      </body>
    </html>
  );
}