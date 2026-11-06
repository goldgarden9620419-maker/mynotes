/**
 * 구글 애드센스 스크립트. 읽을거리가 충분한 페이지(메인, 가이드, 정책 페이지)에만 넣는다.
 * 사용자 데이터로 화면이 채워지는 페이지(복습)나 오류 화면에는 넣지 않는다.
 */
export default function AdSenseScript() {
  return (
    <script
      async
      src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6636318203503169"
      crossOrigin="anonymous"
    />
  );
}
