#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
覆盖率聚合（配置驱动版）: 扫描 <test_root>/build/*/ 的 *.gcov, 只统计 source_root 下被测源码,
多个测试工程对同一源文件的覆盖取并集, 输出 markdown 汇总表。

用法:
  python coverage_report.py                 # 打印 + 写 <配置目录>/test-docs/coverage-summary.md
  python coverage_report.py --out path.md

注意: 并集口径可能因不同 build 的 gcov 分支编号错位虚增分支总数;
文档口径建议以各模块主测工程(专属测试)的单份 gcov 为准, 本表作交叉参考。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wbconfig import load_config   # noqa: E402

LINE_RE = re.compile(r"^\s*([#\-=0-9]+):\s*(\d+):")
BRANCH_RE = re.compile(r"^\s*branch\s+(\d+)\s+(.*)$")


def parse_gcov(path: Path):
    """返回 (source, {line_no: hit_bool}, {(line_no, branch_idx): hit_bool})"""
    lines = {}
    branches = {}
    cur_line = None
    src = None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None, None
    for raw in text.splitlines():
        if raw.startswith("        -:    0:Source:"):
            src = raw.split("Source:", 1)[1].strip()
            continue
        m = LINE_RE.match(raw)
        if m:
            cnt, lineno = m.group(1), int(m.group(2))
            cur_line = lineno
            if lineno == 0:
                continue
            if cnt == "-":
                continue          # 非代码行
            hit = cnt.isdigit() and int(cnt) > 0
            lines[lineno] = lines.get(lineno, False) or hit
            continue
        m = BRANCH_RE.match(raw)
        if m and cur_line is not None:
            idx = int(m.group(1))
            rest = m.group(2)
            if "never executed" in rest:
                hit = False
            else:
                mm = re.search(r"taken\s+(\d+)", rest)   # -c: 次数; -b: 百分比
                hit = bool(mm) and int(mm.group(1)) > 0
            key = (cur_line, idx)
            branches[key] = branches.get(key, False) or hit
    return src, lines, branches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="输出 markdown 路径(缺省 <配置目录>/test-docs/coverage-summary.md)")
    ap.add_argument("--config", help="whitebox.config.json 路径")
    args = ap.parse_args()

    cfg = load_config(args.config)
    BUILD = cfg.test_root / "build"
    tag = cfg.source_tag
    out_path = Path(args.out) if args.out else cfg.base / "test-docs" / "coverage-summary.md"

    files = {}
    builds = sorted(BUILD.glob("*/"))
    for b in builds:
        for g in sorted(b.glob("*.gcov")):
            src, lines, branches = parse_gcov(g)
            if not src or tag not in src:
                continue          # 只统计被测源码, 跳过 harness/桩/测试
            rec = files.setdefault(src, {"lines": {}, "branches": {}})
            for k, v in lines.items():
                rec["lines"][k] = rec["lines"].get(k, False) or v
            for k, v in branches.items():
                rec["branches"][k] = rec["branches"].get(k, False) or v

    out = ["# gcov 覆盖率聚合汇总", "",
           f"扫描目录: `{BUILD}`（{len(builds)} 个测试工程）, 并集合并同源文件覆盖。", "",
           "| 源文件 | 行覆盖 | 行覆盖率 | 分支覆盖 | 分支覆盖率 |", "|---|---|---|---|---|"]
    tl = th = tb = tbc = 0
    for src in sorted(files):
        rel = src.replace("\\", "/")
        if tag in rel:
            rel = rel.split(tag, 1)[-1].lstrip("/")
        ln = files[src]["lines"]
        br = files[src]["branches"]
        l_total = len(ln)
        l_hit = sum(1 for v in ln.values() if v)
        b_total = len(br)
        b_hit = sum(1 for v in br.values() if v)
        tl += l_total; th += l_hit; tb += b_total; tbc += b_hit
        lp = (100.0 * l_hit / l_total) if l_total else 100.0
        bp = (100.0 * b_hit / b_total) if b_total else 100.0
        out.append(f"| {rel} | {l_hit}/{l_total} | {lp:.1f}% | {b_hit}/{b_total} | {bp:.1f}% |")
    lp = (100.0 * th / tl) if tl else 100.0
    bp = (100.0 * tbc / tb) if tb else 100.0
    out.append(f"| **总计** | **{th}/{tl}** | **{lp:.1f}%** | **{tbc}/{tb}** | **{bp:.1f}%** |")
    out.append("")
    out.append("注: 行覆盖率=执行次数>0 的代码行占比; 分支覆盖率=至少走过一次的分支边占比; `#####`/`=====` 行计为未覆盖。")

    report = "\n".join(out)
    print(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\n[written] {out_path}")


if __name__ == "__main__":
    main()
