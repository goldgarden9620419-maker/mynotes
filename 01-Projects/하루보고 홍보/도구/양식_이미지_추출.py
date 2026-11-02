#!/usr/bin/env python3
"""양식(.xlsx)의 시트 화면을 PNG 후보로 뽑는다 (블로그 글 이미지용).
사용: python3 양식_이미지_추출.py "양식.xlsx" 출력폴더 [dpi=150]
 - LibreOffice로 PDF 변환 → 쪽마다 PNG(여백 trim) 저장 → 쪽별 첫 줄을 목록으로 출력
 - 같은 내용 쪽(빈 쪽·인쇄 반복)은 건너뛴다. 사람이/루틴이 목록을 보고 3~4장을 골라 쓴다.
필요: soffice(LibreOffice), pdftoppm(poppler), convert(ImageMagick), pdftotext
"""
import subprocess, sys, tempfile, pathlib, shutil

def run(*a): return subprocess.run(a, capture_output=True, text=True)

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    xlsx, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    dpi = sys.argv[3] if len(sys.argv) > 3 else "150"
    out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp())
    run("soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(xlsx))
    pdf = next(tmp.glob("*.pdf"))
    n = int([l for l in run("pdfinfo", str(pdf)).stdout.splitlines() if l.startswith("Pages:")][0].split()[1])
    seen = set()
    for p in range(1, min(n, 40) + 1):
        head = run("pdftotext", "-f", str(p), "-l", str(p), str(pdf), "-").stdout.strip().splitlines()
        key = " ".join(head[:3])
        if not key or key in seen:
            continue
        seen.add(key)
        run("pdftoppm", "-f", str(p), "-l", str(p), "-r", dpi, "-png", str(pdf), str(tmp / "pg"))
        src = next(tmp.glob("pg-*.png"))
        dst = out / f"후보{p:02d}.png"
        run("convert", str(src), "-trim", "+repage", "-bordercolor", "white", "-border", "24", str(dst))
        src.unlink()
        print(f"{dst.name}: {key[:70]}")
    shutil.rmtree(tmp, ignore_errors=True)

main()
