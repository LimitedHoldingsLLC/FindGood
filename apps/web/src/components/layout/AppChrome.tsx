"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";

export function AppChrome({ children }: { children: ReactNode }) {
  const path = usePathname();
  const isAdmin = path.startsWith("/admin");
  if (isAdmin) {
    return <>{children}</>;
  }
  return (
    <>
      <SiteHeader />
      <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-8">{children}</main>
      <SiteFooter />
    </>
  );
}
