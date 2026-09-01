# AI AD CREATIVE STUDIO — 앱 소스 백업

Claude 아티팩트로 게시된 광고 제작 앱의 소스입니다.
- 게시 URL: https://claude.ai/code/artifact/7266ddce-d6a2-42c3-a6b9-0dedb25b37cd
- 빌드: `npm install react@18 react-dom@18 esbuild` 후
  `esbuild app.jsx --bundle --minify --define:process.env.NODE_ENV='"production"' --outfile=bundle.js`
  → bundle.js와 style.css를 `<title>+<style>+<div id="root">+<script>` 형태의 단일 HTML로 감싸 게시 (published.html 참고)
- 구성: 1~8단계(프로젝트~Export) + 9단계 후반 작업(BGM/대사/Voice(Minimax)/립싱크/믹스/렌더, Higgsfield MCP 연동)
