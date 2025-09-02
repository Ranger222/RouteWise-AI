import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RouteWise AI",
  description: "Plan smarter trips with multi-agent intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900 text-slate-800 dark:text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
