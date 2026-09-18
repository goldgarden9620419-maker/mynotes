# -*- coding: utf-8 -*-
"""시스템 트레이 상주 프로그램 (3번 항목).

메뉴: 현재 실행상태 / 다음 자동 실행 / 지금 실행 / 이번 주 실행상태 확인
     / 누락파일 확인 / 변경자료 반영 / 결과폴더 열기 / 실행로그 열기
     / 자동실행 일시정지 / 프로그램 종료
"""
from __future__ import annotations

import pystray
from PIL import Image, ImageDraw

from common import APP_VERSION


def _make_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, size - 2, size - 2], radius=14,
                           fill=(31, 78, 121, 255))
    # 원화 기호를 간단한 도형으로 그린다 (글꼴 의존 제거)
    white = (255, 255, 255, 255)
    draw.line([(16, 18), (26, 46)], fill=white, width=5)
    draw.line([(26, 46), (32, 24)], fill=white, width=5)
    draw.line([(32, 24), (38, 46)], fill=white, width=5)
    draw.line([(38, 46), (48, 18)], fill=white, width=5)
    draw.line([(12, 28), (52, 28)], fill=white, width=3)
    draw.line([(12, 36), (52, 36)], fill=white, width=3)
    return img


def run_tray(service) -> None:
    """트레이 아이콘을 실행한다. 종료 시 스케줄러도 함께 멈춘다."""

    def notify(title: str, message: str) -> None:
        try:
            icon.notify(message[:250], title[:60])
        except Exception:
            service.log.info("[알림] %s — %s", title, message)

    def on_run_now(icon_, item_):
        notify("주간 자금계획", "지금 실행을 시작합니다.")
        service.run_now()

    def on_status(icon_, item_):
        notify("이번 주 실행상태", service.status_text())

    def on_missing(icon_, item_):
        notify("누락파일 확인", service.missing_files_text())

    def on_apply_changes(icon_, item_):
        notify("변경자료 반영", "변경된 입력자료로 다시 생성합니다.")
        service.apply_changes()

    def on_open_output(icon_, item_):
        service.open_output_folder()

    def on_open_log(icon_, item_):
        service.open_log_folder()

    def on_toggle_pause(icon_, item_):
        paused = service.toggle_pause()
        notify("자동실행", "일시정지되었습니다." if paused else "재개되었습니다.")
        icon.update_menu()

    def on_quit(icon_, item_):
        service.stop()
        icon.stop()

    def state_title(item_):
        try:
            status = service.state.state.get("last_run_status", "NOT_RUN")
        except Exception:
            status = "?"
        run_state = "실행 중" if not service.paused else "일시정지"
        return f"상태: {run_state} · 이번 주 {status}"

    def next_run_title(item_):
        return f"다음 자동 실행: {service.next_run_text()}"

    menu = pystray.Menu(
        pystray.MenuItem(state_title, None, enabled=False),
        pystray.MenuItem(next_run_title, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("지금 실행", on_run_now),
        pystray.MenuItem("이번 주 실행상태 확인", on_status),
        pystray.MenuItem("누락파일 확인", on_missing),
        pystray.MenuItem("변경자료 반영", on_apply_changes),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("결과폴더 열기", on_open_output),
        pystray.MenuItem("실행로그 열기", on_open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("자동실행 일시정지",
                         on_toggle_pause,
                         checked=lambda item: service.paused),
        pystray.MenuItem("프로그램 종료", on_quit),
    )

    icon = pystray.Icon(
        "cashflow_automation", _make_icon_image(),
        f"(주)에이팜건강 주간 자금계획 자동화 v{APP_VERSION}", menu)

    # 서비스 알림을 트레이 풍선알림으로 연결
    service.notify = notify

    icon.run()
