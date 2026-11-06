import type { MetadataRoute } from "next";

const BASE_URL = "https://suneungjam.com";

const paths = ["", "/about", "/guide", "/guide/study-tips", "/guide/english-grammar", "/guide/english-blank", "/guide/english-order", "/guide/english-insertion", "/guide/english-main-idea", "/guide/math-sequence", "/guide/math-differentiation", "/guide/math-integration", "/guide/math-probability", "/guide/math-trigonometry", "/privacy-policy", "/terms"];

export default function sitemap(): MetadataRoute.Sitemap {
  return paths.map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
  }));
}
