"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";

export function AppChrome({ children }: { children: ReactNode }) {
  const path = usePathname();
  const isAdmin = path.startsWith("/admin");
  const isMap = path === "/map";
  if (isAdmin) {
    return <>{children}</>;
  }
  if (isMap) {
    return (
      <div className="flex h-dvh flex-col overflow-hidden">
        <SiteHeader compact />
        <main className="relative min-h-0 flex-1">{children}</main>
      </div>
    );
  }
  return (
    <>
      <SiteHeader />
      <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-8">{children}</main>
      <SiteFooter />
    </>
  );
}
