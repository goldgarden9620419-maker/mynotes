# (주)에이팜건강 주간 자금계획 자동화

팀별 주간 지출계획과 농협·우리은행·국민은행 거래내역을 매주 월요일
오전 9시 10분(Asia/Seoul)에 자동 취합·대조·예측하여
Excel 자금계획과 대표 보고용 PDF를 생성하는 Windows 상주 프로그램입니다.

- Windows 작업 스케줄러를 쓰지 않고 프로그램 내부 APScheduler로 실행
- PyInstaller EXE + 시작프로그램 등록으로 PC를 켜면 자동 시작
- 시스템 트레이에서 상태 확인·즉시 실행·변경자료 반영 등 조작

## 폴더 배치 (운영 PC)

```
자금계획_자동화\
├─ 00_프로그램\            cashflow_automation.exe, config.yaml, state.json,
│                          version.txt, classify_rules.json(자동생성),
│                          install_startup.bat, uninstall_startup.bat
├─ 01_일반팀_지출계획\      6개 일반팀 주간지출계획.xlsx
├─ 02_경영지원_대외비\      경영지원팀_대외비_지출계획.xlsx
├─ 03_은행거래내역\농협·우리은행·국민은행\   최근 14일 거래내역
├─ 04_기준파일\            에이팜건강_자금계획_기준파일.xlsx (카드결제기준 포함)
├─ 05_결과\  06_확인필요\  07_실행로그\  08_백업\  99_지난자료\
```

폴더는 최초 실행 시 자동 생성되며, 한글·공백 경로에서도 동작합니다.
경로는 `config.yaml`의 `folders:` 항목에서 변경할 수 있습니다.

## 실행 방법

```bat
python app.py               :: 트레이 + 스케줄러 상주 실행
python app.py --run-now     :: 지금 1회 실행 후 종료
python app.py --once        :: 미실행 보완 검사 1회
python app.py --status      :: 이번 주 실행상태 출력
python app.py --headless    :: 트레이 없이 상주 실행
```

EXE로 빌드하면 `cashflow_automation.exe` 실행이 `python app.py`와 같습니다.

## 빌드·설치 (요약)

1. `build_exe.bat` 실행 → `dist\cashflow_automation.exe` 생성
   (설치 → 테스트 → 빌드 순으로 자동 진행)
2. EXE를 `자금계획_자동화\00_프로그램\` 으로 복사
3. `install_startup.bat` 실행 → 시작프로그램 등록
4. 자세한 내용은 `docs/설치안내서.md`

## 프로그램 구조

| 파일 | 역할 |
|---|---|
| app.py | 파이프라인 오케스트레이터, CLI |
| scheduler.py | APScheduler, 미실행 보완, 재시도, 변경 감지 |
| tray_app.py | 시스템 트레이 메뉴 |
| config.py / config.yaml | 설정·폴더 관리 |
| state_manager.py | state.json 주간 실행상태, lock 파일 |
| logger.py | 일자별 실행 로그(대외비 마스킹) |
| file_validator.py | 필수 입력파일 검사 |
| request_id.py | 요청ID 생성·중복·변경·취소 규칙 |
| team_loader.py | 팀 양식 읽기·통합·대외비 마스킹 |
| bank_loader.py | 은행 파일 표준화, 잔액, 거래 이력 누적 |
| duplicate_checker.py | 은행 거래 중복 제거 |
| bank_classifier.py | 키워드 자동분류(내부이체·TOP출금 등) |
| card_payment.py | 카드결제기준 시트 기반 결제일 계산 |
| payment_matcher.py | 예정 지출 ↔ 실제 출금 대조 |
| forecast_engine.py | 요일별 입금 예측, 4주 일별·13주 주별, 정기지출 |
| excel_report.py | 결과 Excel(사용자 기존 자금계획 양식 8시트 + 지출 4시트) + 확인필요 파일 |
| pdf_report.py | 대표 보고용 PDF |
| backup_manager.py | 입력 백업, 임시폴더, 손상파일 격리, 지난자료 |
| tools/make_templates.py | 팀 제출양식·기준파일 생성 스크립트 |
| tests/ | pytest 41개 테스트 |

## 테스트

```bat
python -m pytest tests -q
```

2026-09-18 기준 Linux/Python 3.11에서 41개 전부 통과.
가상자료만 사용하며 실제 급여·개인정보는 포함하지 않습니다.

## 문서

- `docs/설치안내서.md` — 최초 설치·빌드·시작프로그램 등록
- `docs/운영안내서.md` — 매주 운영 절차와 트레이 메뉴
- `docs/오류대응안내서.md` — 상태·증상별 조치 방법
- `docs/자동처리순서도.md` — 전체 자동 처리 흐름도
