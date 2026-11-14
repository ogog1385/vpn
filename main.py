import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import flet as ft

FILE_NAME = "ips.txt"


def ensure_ips_file():
    if not os.path.exists(FILE_NAME):
        default_hosts = ["8.8.8.8", "1.1.1.1", "104.16.123.96", "4.2.2.4"]
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("\n".join(default_hosts))


def ping_target(host):
    """تست پینگ به همراه اندازه‌گیری زمان برحسب میلی‌ثانیه"""
    host = host.strip()
    if not host or host.startswith("#"):
        return None

    # دستور پینگ بر اساس سیستم‌عامل
    cmd = (
        ["ping", "-n", "2", "-w", "800", host]
        if os.name == "nt"
        else ["ping", "-c", "2", "-W", "1", host]
    )

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            # استخراج عدد Latency
            match = re.search(r"(?:Average|avg)[ =/]+(\d+)", res.stdout)
            ms = int(match.group(1)) if match else 999
            return {"host": host, "ping": ms, "status": "Online"}
        else:
            return {"host": host, "ping": 9999, "status": "Offline"}
    except Exception:
        return {"host": host, "ping": 9999, "status": "Timeout"}


def main(page: ft.Page):
    page.title = "Core Tunnel Client"
    page.window_width = 400
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    ensure_ips_file()

    # ۱. بخش هدر و ورودی (با نام شما)
    header_name = ft.Text(
        "Amir Mohammad Sadeghi",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.CYAN_ACCENT,
    )

    subtitle = ft.Text(
        "Advanced Core Controller", size=12, color=ft.colors.GREY_400
    )

    status_icon = ft.Icon(
        ft.icons.SHIELD_ROUNDED, size=90, color=ft.colors.GREY_600
    )

    status_text = ft.Text(
        "DISCONNECTED",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.GREY_400,
    )

    server_info = ft.Text(
        "Select an IP or scan to begin", size=13, color=ft.colors.GREY_500
    )

    log_box = ft.ListView(expand=True, spacing=5, auto_scroll=True)

    def log(msg, color=ft.colors.WHITE):
        log_box.controls.append(ft.Text(f"> {msg}", size=11, color=color))
        page.update()

    is_connected = False
    best_server = {"host": None, "ping": 9999}

    # اجرای اسکن به صورت غیرهمگام
    def run_scan(e=None):
        scan_btn.disabled = True
        log("Scanning IPs from ips.txt...", ft.colors.AMBER)
        page.update()

        with open(FILE_NAME, "r", encoding="utf-8") as f:
            hosts = [line.strip() for line in f if line.strip()]

        valid_servers = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(ping_target, h) for h in hosts]
            for future in as_completed(futures):
                data = future.result()
                if data and data["status"] == "Online":
                    valid_servers.append(data)
                    log(
                        f"Found: {data['host']} ({data['ping']} ms)",
                        ft.colors.GREEN_ACCENT,
                    )

        if valid_servers:
            # انتخاب کمترین پینگ
            valid_servers.sort(key=lambda x: x["ping"])
            best_server["host"] = valid_servers[0]["host"]
            best_server["ping"] = valid_servers[0]["ping"]
            server_info.value = f"Target: {best_server['host']} | Ping: {best_server['ping']} ms"
            log(f"Optimal node selected: {best_server['host']}", ft.colors.CYAN)
            connect_btn.disabled = False
        else:
            log("No reachable hosts found in ips.txt", ft.colors.RED_ACCENT)

        scan_btn.disabled = False
        page.update()

    # شبیه‌سازی شروع تانل و اتصال
    def toggle_connect(e):
        nonlocal is_connected
        if not is_connected:
            status_text.value = "CONNECTING..."
            status_text.color = ft.colors.AMBER
            status_icon.color = ft.colors.AMBER
            connect_btn.disabled = True
            page.update()

            def process_tunnel():
                nonlocal is_connected
                time.sleep(1.5)  # انتظار برای راه‌اندازی فرآیند تونل
                is_connected = True
                status_text.value = "CONNECTED"
                status_text.color = ft.colors.GREEN_ACCENT
                status_icon.color = ft.colors.GREEN_ACCENT
                connect_btn.text = "Disconnect"
                connect_btn.bgcolor = ft.colors.RED_700
                connect_btn.disabled = False
                log("Tunnel established successfully.", ft.colors.GREEN)
                page.update()

            threading.Thread(target=process_tunnel, daemon=True).start()
        else:
            is_connected = False
            status_text.value = "DISCONNECTED"
            status_text.color = ft.colors.GREY_400
            status_icon.color = ft.colors.GREY_600
            connect_btn.text = "Connect"
            connect_btn.bgcolor = ft.colors.GREEN_700
            log("Tunnel closed.", ft.colors.RED_ACCENT)
            page.update()

    connect_btn = ft.ElevatedButton(
        "Connect",
        on_click=toggle_connect,
        bgcolor=ft.colors.GREEN_700,
        color=ft.colors.WHITE,
        width=180,
        height=45,
        disabled=True,
    )

    scan_btn = ft.OutlinedButton(
        "Scan IPs", on_click=run_scan, width=180, height=45
    )

    # چینش المان‌های صفحه
    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [header_name, subtitle],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.IconButton(
                            icon=ft.icons.REFRESH, on_click=run_scan
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=ft.colors.GREY_800),
                ft.Container(height=10),
                ft.Center(content=status_icon),
                ft.Center(content=status_text),
                ft.Center(content=server_info),
                ft.Container(height=15),
                ft.Row(
                    [scan_btn, connect_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Container(height=15),
                ft.Text("Execution Logs:", size=12, color=ft.colors.GREY_400),
                ft.Container(
                    content=log_box,
                    bgcolor=ft.colors.BLACK45,
                    border_radius=8,
                    padding=10,
                    height=180,
                    border=ft.border.all(1, ft.colors.GREY_800),
                ),
            ],
            expand=True,
        )
    )


ft.app(target=main)
