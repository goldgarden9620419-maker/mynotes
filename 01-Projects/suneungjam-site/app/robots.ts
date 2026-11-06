import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/review"] },
    sitemap: "https://suneungjam.com/sitemap.xml",
  };
}
