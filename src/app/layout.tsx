import type { Metadata, Viewport } from "next";
import { Onest, Unbounded } from "next/font/google";
import type { ReactNode } from "react";
import "@/styles/base.css";
import "@/styles/type.css";
import "@/styles/controls.css";

const unbounded = Unbounded({ subsets: ["latin"], weight: ["800"], variable: "--font-unbounded", display: "swap" });
const onest = Onest({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-onest", display: "swap" });

export const metadata: Metadata = {
  title: "Wako Beans",
};

export const viewport: Viewport = {
  themeColor: "#9c1220",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${unbounded.variable} ${onest.variable}`}>
      <body>
        <main id="main">{children}</main>
      </body>
    </html>
  );
}
