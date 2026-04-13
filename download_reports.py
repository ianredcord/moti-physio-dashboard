#!/usr/bin/env python3
"""批次下載 Moti-Physio 分析報告圖片"""

import os
import sys
import requests

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt

from moti_client import MotiClient, MotiAPIError

load_dotenv()
console = Console()


def download_file(url: str, save_path: str):
    """下載檔案到指定路徑"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def download_report(client, user_id, analysis_type, analysis_index, base_dir="reports"):
    """下載指定分析報告的所有圖片"""
    type_dir = {"static": "static", "ohs": "ohs", "ols": "ols"}

    console.print(f"\n[cyan]取得 {user_id} 的 {analysis_type} 報告 (index={analysis_index})...[/cyan]")

    try:
        if analysis_type == "static":
            report = client.get_static_report(user_id, analysis_index)
        elif analysis_type == "ohs":
            report = client.get_ohs_report(user_id, analysis_index)
        else:
            report = client.get_ols_report(user_id, analysis_index)
    except MotiAPIError as e:
        console.print(f"[red]錯誤：{e}[/red]")
        return

    if isinstance(report, dict) and "reports" in report:
        reports = report["reports"]
    elif isinstance(report, dict):
        reports = report
    else:
        console.print(f"[yellow]未預期回傳格式[/yellow]")
        return

    save_base = os.path.join(base_dir, user_id, type_dir[analysis_type], str(analysis_index))
    total_files = sum(len(pages) for pages in reports.values() if isinstance(pages, list))

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TextColumn("{task.completed}/{task.total}")) as progress:
        task = progress.add_task("下載中", total=total_files)

        for category, pages in reports.items():
            if not isinstance(pages, list):
                continue
            for page in pages:
                url = page.get("presigned_url", "")
                filename = page.get("filename", f"page_{page.get('page_index', 0)}.png")
                save_path = os.path.join(save_base, category, filename)

                try:
                    download_file(url, save_path)
                except Exception as e:
                    console.print(f"[red]下載失敗 {filename}: {e}[/red]")

                progress.advance(task)

    console.print(f"[green]完成！檔案儲存於 {save_base}[/green]")


def download_all_reports(client, user_id, base_dir="reports"):
    """下載某會員的所有報告"""
    for atype, get_list in [
        ("static", client.get_static_analysis_list),
        ("ohs", client.get_ohs_analysis_list),
        ("ols", client.get_ols_analysis_list),
    ]:
        try:
            analyses = get_list(user_id)
        except MotiAPIError:
            console.print(f"[yellow]{user_id} 無 {atype} 資料[/yellow]")
            continue

        if not analyses:
            continue

        for a in analyses:
            idx = a.get("analysisIndex", 0)
            download_report(client, user_id, atype, idx, base_dir)


def main():
    program_id = os.getenv("PROGRAM_ID")
    security_key = os.getenv("SECURITY_KEY")
    if not program_id or not security_key:
        console.print("[red]請在 .env 設定 PROGRAM_ID 和 SECURITY_KEY[/red]")
        sys.exit(1)

    client = MotiClient(program_id, security_key)
    user_id = Prompt.ask("[bold]請輸入要下載報告的 User ID[/bold]")
    mode = Prompt.ask("[bold]下載模式[/bold]", choices=["all", "single"], default="all")

    if mode == "all":
        download_all_reports(client, user_id)
    else:
        atype = Prompt.ask("[bold]分析類型[/bold]", choices=["static", "ohs", "ols"])
        index = int(Prompt.ask("[bold]Analysis Index[/bold]"))
        download_report(client, user_id, atype, index)


if __name__ == "__main__":
    main()
