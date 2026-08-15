import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const host = process.env.NEXT_PUBLIC_CANONICAL_HOST ?? "findgood.food";
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/admin"] },
    host: `https://${host}`,
    sitemap: `https://${host}/sitemap.xml`,
  };
}
