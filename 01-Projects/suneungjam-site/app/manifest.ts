import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "수능잼 | 짬 나는 시간에 보는 수능 한 문제",
    short_name: "수능잼",
    description:
      "버스에서, 이동 중에, 짬날 때 1~2분이면 끝나는 영어·수학 수능 유형 문제. 정답을 맞히면 다음 문제로, 틀리면 바로 해설을 확인하세요.",
    start_url: "/",
    display: "standalone",
    background_color: "#0d1117",
    theme_color: "#0d1117",
    orientation: "portrait",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
