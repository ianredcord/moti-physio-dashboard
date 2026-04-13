#!/usr/bin/env python3
"""快速掃描所有會員的分析資料與報告可用性"""

import os, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
load_dotenv()

from moti_client import MotiClient, MotiAPIError

client = MotiClient(os.getenv("PROGRAM_ID"), os.getenv("SECURITY_KEY"))

def scan_user(uid):
    """掃描單一會員，回傳結果 dict"""
    result = {"userId": uid, "static": [], "ohs": [], "ols": [], "static_reports": [], "ohs_reports": [], "ols_reports": []}

    for atype, key, report_key, get_list, get_report in [
        ("static", "static", "static_reports", client.get_static_analysis_list, client.get_static_report),
        ("ohs", "ohs", "ohs_reports", client.get_ohs_analysis_list, client.get_ohs_report),
        ("ols", "ols", "ols_reports", client.get_ols_analysis_list, client.get_ols_report),
    ]:
        try:
            analyses = get_list(uid)
            if not analyses:
                continue
            result[key] = [a.get("analysisIndex") for a in analyses]

            for a in analyses:
                idx = a.get("analysisIndex")
                try:
                    report = get_report(uid, idx)
                    reps = report.get("reports", {})
                    file_count = sum(len(v) for v in reps.values() if isinstance(v, list))
                    if file_count > 0:
                        cats = {k: len(v) for k, v in reps.items() if isinstance(v, list) and len(v) > 0}
                        result[report_key].append({"index": idx, "files": file_count, "categories": cats})
                except MotiAPIError:
                    pass
        except MotiAPIError:
            pass

    return result


def main():
    users = client.get_user_list()
    total = len(users)
    print(f"總會員數: {total}")

    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_user, u["userId"]): u["userId"] for u in users}
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  進度: {done}/{total}", flush=True)
            try:
                results.append(future.result())
            except Exception as e:
                results.append({"userId": futures[future], "error": str(e)})

    # 統計
    has_static = [r for r in results if r.get("static")]
    has_ohs = [r for r in results if r.get("ohs")]
    has_ols = [r for r in results if r.get("ols")]
    has_static_rpt = [r for r in results if r.get("static_reports")]
    has_ohs_rpt = [r for r in results if r.get("ohs_reports")]
    has_ols_rpt = [r for r in results if r.get("ols_reports")]
    no_data = [r for r in results if not r.get("static") and not r.get("ohs") and not r.get("ols")]

    print("\n" + "=" * 60)
    print("掃描完成")
    print("=" * 60)
    print(f"總會員數:              {total}")
    print(f"無任何分析資料:        {len(no_data)} ({len(no_data)*100//total}%)")
    print(f"有靜態分析數據:        {len(has_static)} ({len(has_static)*100//total}%)")
    print(f"有 OHS 分析數據:       {len(has_ohs)} ({len(has_ohs)*100//total}%)")
    print(f"有 OLS 分析數據:       {len(has_ols)} ({len(has_ols)*100//total}%)")
    print(f"有靜態報告圖片:        {len(has_static_rpt)} 位會員")
    print(f"有 OHS 報告圖片:       {len(has_ohs_rpt)} 位會員")
    print(f"有 OLS 報告圖片:       {len(has_ols_rpt)} 位會員")

    if has_static_rpt:
        print(f"\n{'='*60}")
        print("有靜態報告的會員:")
        print(f"{'='*60}")
        for r in sorted(has_static_rpt, key=lambda x: x["userId"]):
            for rpt in r["static_reports"]:
                print(f"  {r['userId']}  index={rpt['index']}  files={rpt['files']}  {rpt['categories']}")

    if has_ohs_rpt:
        print(f"\nOHS 報告:")
        for r in sorted(has_ohs_rpt, key=lambda x: x["userId"]):
            for rpt in r["ohs_reports"]:
                print(f"  {r['userId']}  index={rpt['index']}  files={rpt['files']}  {rpt['categories']}")

    if has_ols_rpt:
        print(f"\nOLS 報告:")
        for r in sorted(has_ols_rpt, key=lambda x: x["userId"]):
            for rpt in r["ols_reports"]:
                print(f"  {r['userId']}  index={rpt['index']}  files={rpt['files']}  {rpt['categories']}")

    # 存檔
    with open("/Users/apple/Downloads/motit/scan_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n詳細結果已存至 scan_results.json")


if __name__ == "__main__":
    main()
