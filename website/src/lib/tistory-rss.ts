const RSS_URL = "https://goldjade0419.com/rss";

export type BlogPost = {
  title: string;
  link: string;
  excerpt: string;
  tag: string;
  pubDate: string;
};

const NAMED_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
  middot: "·",
  hellip: "…",
  mdash: "—",
  ndash: "–",
  lsquo: "'",
  rsquo: "'",
  ldquo: '"',
  rdquo: '"',
};

function decodeEntities(input: string): string {
  return input.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (match, entity) => {
    if (entity[0] === "#") {
      const code =
        entity[1] === "x" || entity[1] === "X"
          ? parseInt(entity.slice(2), 16)
          : parseInt(entity.slice(1), 10);
      return Number.isNaN(code) ? match : String.fromCodePoint(code);
    }
    return NAMED_ENTITIES[entity] ?? match;
  });
}

function stripHtml(input: string): string {
  return decodeEntities(input.replace(/<[^>]*>/g, " "))
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
  return date.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

function extractTag(block: string, tag: string): string {
  const match = block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`));
  if (!match) return "";
  return match[1].replace(/^<!\[CDATA\[([\s\S]*)\]\]>$/, "$1");
}

export async function getLatestPosts(limit = 2): Promise<BlogPost[]> {
  try {
    const res = await fetch(RSS_URL, {
      next: { revalidate: 3600 },
      headers: { "User-Agent": "GoldGarden-Landing/1.0" },
    });

    if (!res.ok) return [];

    const xml = await res.text();
    const itemBlocks = xml.match(/<item>[\s\S]*?<\/item>/g) ?? [];

    return itemBlocks.slice(0, limit).map((block): BlogPost => {
      const title = stripHtml(extractTag(block, "title"));
      const link = decodeEntities(extractTag(block, "link")).trim();
      const description = stripHtml(extractTag(block, "description"));
      const category = stripHtml(extractTag(block, "category"));
      const pubDate = extractTag(block, "pubDate");

      return {
        title,
        link: link || "https://goldjade0419.com/",
        excerpt: truncate(description, 90),
        tag: category || "블로그",
        pubDate: formatDate(pubDate),
      };
    });
  } catch {
    return [];
  }
}
