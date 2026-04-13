#!/usr/bin/env python3
"""Moti-Physio CLI — 會員管理與分析報告查詢工具"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel

from moti_client import MotiClient, MotiAPIError

load_dotenv()
console = Console()


def create_client():
    program_id = os.getenv("PROGRAM_ID")
    security_key = os.getenv("SECURITY_KEY")
    if not program_id or not security_key:
        console.print("[red]請在 .env 設定 PROGRAM_ID 和 SECURITY_KEY[/red]")
        sys.exit(1)
    return MotiClient(program_id, security_key)


def ts_to_date(ts):
    """Unix timestamp → 可讀日期"""
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return str(ts)


def gender_text(g):
    return "男" if g == 0 else "女" if g == 1 else str(g)


# ── 功能：會員列表 ──

def show_user_list(client):
    console.print("\n[bold cyan]載入會員列表...[/bold cyan]")
    users = client.get_user_list()

    table = Table(title=f"會員列表（共 {len(users)} 人）")
    table.add_column("#", style="dim", width=5)
    table.add_column("User ID", style="bold")
    table.add_column("姓名")
    table.add_column("年齡", justify="right")
    table.add_column("性別")
    table.add_column("註冊日期")

    for i, u in enumerate(users, 1):
        table.add_row(
            str(i),
            u.get("userId", ""),
            u.get("name", "") or "(未填)",
            str(u.get("age", "")),
            gender_text(u.get("gender")),
            ts_to_date(u.get("signupDate")),
        )

    console.print(table)
    return users


# ── 功能：會員詳細資訊 ──

def show_user_info(client):
    user_id = Prompt.ask("[bold]請輸入 User ID[/bold]")
    console.print(f"\n[cyan]查詢 {user_id} ...[/cyan]")

    try:
        info = client.get_user_info(user_id)
    except MotiAPIError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        return

    table = Table(title=f"會員資訊：{user_id}")
    table.add_column("欄位", style="bold")
    table.add_column("值")

    fields = [
        ("User ID", info.get("userId")),
        ("姓名", info.get("name") or "(未填)"),
        ("年齡", info.get("age")),
        ("性別", gender_text(info.get("gender"))),
        ("生日", ts_to_date(info.get("birthDay"))),
        ("Email", info.get("email") or "(未填)"),
        ("電話", info.get("phoneNum") or "(未填)"),
        ("Trainer ID", info.get("trainerId")),
        ("註冊日期", ts_to_date(info.get("signupDate"))),
    ]
    for label, val in fields:
        table.add_row(label, str(val) if val is not None else "-")

    console.print(table)


# ── 功能：分析列表 ──

def show_analysis_list(client, analysis_type):
    user_id = Prompt.ask("[bold]請輸入 User ID[/bold]")
    type_names = {"static": "靜態分析", "ohs": "OHS 深蹲", "ols": "OLS 單腳站立"}
    label = type_names[analysis_type]

    console.print(f"\n[cyan]查詢 {user_id} 的{label}列表...[/cyan]")

    try:
        if analysis_type == "static":
            analyses = client.get_static_analysis_list(user_id)
        elif analysis_type == "ohs":
            analyses = client.get_ohs_analysis_list(user_id)
        else:
            analyses = client.get_ols_analysis_list(user_id)
    except MotiAPIError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        return

    if not analyses:
        console.print(f"[yellow]{user_id} 無{label}記錄[/yellow]")
        return

    table = Table(title=f"{user_id} — {label}列表（共 {len(analyses)} 筆）")
    table.add_column("#", style="dim", width=5)
    table.add_column("Analysis Index", justify="right")
    table.add_column("量測日期")
    table.add_column("版本")

    for i, a in enumerate(analyses, 1):
        table.add_row(
            str(i),
            str(a.get("analysisIndex", "")),
            ts_to_date(a.get("measurementDate")),
            str(a.get("version", "")),
        )

    console.print(table)
    return analyses


# ── 功能：分析報告 ──

def show_analysis_report(client, analysis_type):
    user_id = Prompt.ask("[bold]請輸入 User ID[/bold]")
    index = IntPrompt.ask("[bold]請輸入 Analysis Index[/bold]")
    type_names = {"static": "靜態分析", "ohs": "OHS 深蹲", "ols": "OLS 單腳站立"}
    label = type_names[analysis_type]

    console.print(f"\n[cyan]取得 {user_id} 的{label}報告 (index={index})...[/cyan]")

    try:
        if analysis_type == "static":
            report = client.get_static_report(user_id, index)
        elif analysis_type == "ohs":
            report = client.get_ohs_report(user_id, index)
        else:
            report = client.get_ols_report(user_id, index)
    except MotiAPIError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        return

    if isinstance(report, dict) and "reports" in report:
        reports = report["reports"]
    elif isinstance(report, dict):
        reports = report
    else:
        console.print(f"[yellow]回傳格式未預期：{type(report)}[/yellow]")
        return

    for category, pages in reports.items():
        if not isinstance(pages, list):
            continue
        table = Table(title=f"{label}報告 — {category}")
        table.add_column("Page", justify="right", width=6)
        table.add_column("檔名")
        table.add_column("Presigned URL（24hr 有效）", max_width=80)

        for p in pages:
            table.add_row(
                str(p.get("page_index", "")),
                p.get("filename", ""),
                p.get("presigned_url", "")[:80] + "...",
            )
        console.print(table)

    if "url_expiration_seconds" in report:
        console.print(f"[dim]URL 有效期：{report['url_expiration_seconds']} 秒[/dim]")


# ── 主選單 ──

MENU = """
[bold]Moti-Physio CLI[/bold]

  [1] 查詢會員列表
  [2] 查詢會員詳細資訊
  [3] 靜態分析列表
  [4] OHS 深蹲分析列表
  [5] OLS 單腳站立分析列表
  [6] 靜態分析報告
  [7] OHS 深蹲分析報告
  [8] OLS 單腳站立分析報告
  [0] 離開
"""


def main():
    client = create_client()
    console.print(Panel("[bold green]Moti-Physio CLI 啟動成功[/bold green]"))

    while True:
        console.print(MENU)
        choice = Prompt.ask("[bold]請選擇功能[/bold]", choices=["0","1","2","3","4","5","6","7","8"], default="0")

        if choice == "0":
            console.print("[bold]再見！[/bold]")
            break
        elif choice == "1":
            show_user_list(client)
        elif choice == "2":
            show_user_info(client)
        elif choice == "3":
            show_analysis_list(client, "static")
        elif choice == "4":
            show_analysis_list(client, "ohs")
        elif choice == "5":
            show_analysis_list(client, "ols")
        elif choice == "6":
            show_analysis_report(client, "static")
        elif choice == "7":
            show_analysis_report(client, "ohs")
        elif choice == "8":
            show_analysis_report(client, "ols")


if __name__ == "__main__":
    main()
