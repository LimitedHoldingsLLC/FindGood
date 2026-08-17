import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import type { ReactNode } from "react";

import { AppChrome } from "@/components/layout/AppChrome";

import "./globals.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const canonicalHost = process.env.NEXT_PUBLIC_CANONICAL_HOST ?? "findgood.food";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "FindGood.Food — good food and drink deals near you",
    template: "%s · FindGood.Food",
  },
  description: "Find good food and drink deals happening near you.",
  alternates: {
    canonical: `https://${canonicalHost}`,
  },
  openGraph: {
    title: "FindGood.Food",
    description: "What's good near you?",
    siteName: "FindGood.Food",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${outfit.variable} ${fraunces.variable}`}>
      <body className={outfit.className}>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
