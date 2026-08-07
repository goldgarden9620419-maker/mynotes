import { XMLParser } from "fast-xml-parser";

const RSS_URL = "https://goldjade0419.com/rss";

export type BlogPost = {
  title: string;
  link: string;
  excerpt: string;
  tag: string;
  pubDate: string;
};

function stripHtml(input: string): string {
  return input
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function truncate(input: string, max: number): string {
  if (input.length <= max) return input;
  return `${input.slice(0, max).trimEnd()}…`;
}

function formatDate(pubDate: string): string {
  const date = new Date(pubDate);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ko-KR", {
    month: "long",
    day: "numeric",
  });
}

export async function getLatestPosts(limit = 2): Promise<BlogPost[]> {
  try {
    const res = await fetch(RSS_URL, {
      next: { revalidate: 3600 },
      headers: { "User-Agent": "WellLog-Landing/1.0" },
    });

    if (!res.ok) return [];

    const xml = await res.text();
    const parser = new XMLParser({
      ignoreAttributes: false,
      cdataPropName: "#cdata",
    });
    const data = parser.parse(xml);

    const rawItems = data?.rss?.channel?.item;
    const items = Array.isArray(rawItems) ? rawItems : rawItems ? [rawItems] : [];

    return items.slice(0, limit).map((item): BlogPost => {
      const title = stripHtml(String(item.title ?? ""));
      const descriptionRaw =
        typeof item.description === "object"
          ? (item.description?.["#cdata"] ?? "")
          : (item.description ?? "");
      const category = Array.isArray(item.category)
        ? item.category[0]
        : (item.category ?? "블로그");

      return {
        title,
        link: String(item.link ?? "https://goldjade0419.com/"),
        excerpt: truncate(stripHtml(String(descriptionRaw)), 90),
        tag: stripHtml(String(category)),
        pubDate: formatDate(String(item.pubDate ?? "")),
      };
    });
  } catch {
    return [];
  }
}
