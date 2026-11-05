#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whitebox-testing 标准化入口（配套 SKILL.md, 配置驱动版）

子命令:
  new  <相对source_root的Module.c> [中文模块名]   生成 tests/test_<mod>.c + stubs/stub_<mod>.c 骨架并注册
  run  [test ...]                                跑指定/全部测试套件, 汇总 checks 结果
  gate [--min-line 85 --min-branch 80]           全量回归 + 主测工程覆盖率门禁（CI 用, 不达标非零退出）
  cases                                          列出全部 TEST() 用例清单
  vg <file.c ...>                                环复杂度 V(G) 表

套件注册表: <test_root>/scripts/suites.json  { test名: {modules:[相对source路径], primary:主测源文件名} }
覆盖率口径: 各套件 build/<test>/<primary>.gcov 为准（勿跨 build 并集, gcov 分支编号会错位）。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wbconfig import load_config   # noqa: E402

LINE_RE = re.compile(r"^\s*([#\-=0-9]+):\s*(\d+):")
BRANCH_RE = re.compile(r"^\s*branch\s+(\d+)\s+(.*)$")
SUMMARY_RE = re.compile(r"====\s*SUMMARY:\s*(\d+)\s*checks\s*passed,\s*(\d+)\s*failed")
TEST_RE = re.compile(r"^TEST\((\w+)\)")


def load_suites():
    if SUITE_JSON.exists():
        return json.loads(SUITE_JSON.read_text(encoding="utf-8"))
    return {}


def save_suites(reg):
    SUITE_JSON.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def run_build_run(test, modules):
    args = [sys.executable, str(SCRIPTS / "build_run.py"), "--test", test]
    if modules:
        args += ["--modules"] + modules
    if CONFIG_ARG:
        args += ["--config", CONFIG_ARG]
    p = subprocess.run(args, cwd=str(WS), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p


def parse_gcov(path):
    """返回 (行覆盖数, 行总数, 分支覆盖数, 分支总数)"""
    line_hit = line_tot = br_hit = br_tot = 0
    cur = None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return (0, 0, 0, 0)
    for raw in text.splitlines():
        m = LINE_RE.match(raw)
        if m:
            cnt, lineno = m.group(1), int(m.group(2))
            cur = lineno
            if lineno == 0 or cnt == "-":
                continue
            line_tot += 1
            if cnt.isdigit() and int(cnt) > 0:
                line_hit += 1
            continue
        m = BRANCH_RE.match(raw)
        if m and cur is not None:
            br_tot += 1
            rest = m.group(2)
            if "never executed" in rest:
                continue
            mm = re.search(r"taken\s+(\d+)", rest)
            if mm and int(mm.group(1)) > 0:
                br_hit += 1
    return (line_hit, line_tot, br_hit, br_tot)


def cmd_new(args):
    src = args.source.replace("\\", "/")
    mod = Path(src).stem                       # e.g. NewModule
    test_name = "test_" + mod.lower()
    reg = load_suites()
    tfile = WT / "tests" / f"{test_name}.c"
    sfile = WT / "stubs" / f"stub_{mod.lower()}.c"
    if tfile.exists():
        sys.exit(f"[x] 已存在: {tfile}")
    test_tpl = """/* __TEST__.c —— __MOD__ 白盒测试（骨架, 由 wb.py new 生成）
 * 覆盖准则: 语句/分支/独立路径/边界/缺陷锁定（见 SKILL.md P3）
 * 运行: python <技能>/scripts/build_run.py --test __TEST__
 * 注意: 下面用 #include 被测 .c 的白盒技巧访问 static, 此时不要加 --modules;
 *       若改为链接真实现, 删除 #include 并在 suites.json modules 中登记。
 */
#include "test_framework.h"
#include "hwlog.h"
#include "__SRCFILE__"        /* 白盒: 同编译单元, 可见 static */

static void reset_state(void)
{
    /* TODO: 重置被测 .c 内 static 变量与全局输出结构 */
}

/* TODO: 按用例表替换为正式用例, 命名 <ID>_<目标> */
TEST(__MODUPPER___smoke_reachable)
{
    reset_state();
    /* TODO: 调用入口函数一次, 断言基本可达 */
    CHECK(1, "skeleton smoke");
}

int main(void)
{
    RUN_TEST(__MODUPPER___smoke_reachable);
    return TEST_SUMMARY();
}
"""
    tfile.write_text(test_tpl.replace("__TEST__", test_name)
                     .replace("__MOD__", mod)
                     .replace("__MODUPPER__", mod.upper())
                     .replace("__SRCFILE__", src.split("/")[-1]), encoding="utf-8")
    stub_tpl = """/* stub___MODLOWER__.c —— __MOD__ 测试桩（骨架, 由 wb.py new 生成）
 * 内容: 跨模块全局实例(#include 头后定义) + 被调函数可控桩 + hwlog 记录
 * build_run.py 自动挂载本文件。
 */
/* TODO: 如被测 .c 引用其他模块全局(如 SysModeCtrl_out), 在此:
 *   #include "SysMainModeCtrl.h"
 *   SysModeCtrl_t SysModeCtrl_out;
 */
"""
    sfile.write_text(stub_tpl.replace("__MODLOWER__", mod.lower())
                     .replace("__MOD__", mod), encoding="utf-8")
    reg[test_name] = {"modules": [], "primary": f"{mod}.c"}
    save_suites(reg)
    print(f"[ok] 生成 {tfile}")
    print(f"[ok] 生成 {sfile}")
    print(f"[ok] 注册 suites.json: {test_name} (primary={mod}.c)")
    print(f"[next] 1) 填写用例  2) build_run.py --test {test_name}  3) wb.py gate 复核覆盖率")


def cmd_run(args):
    reg = load_suites()
    names = args.tests if args.tests else list(reg.keys())
    total_c = failed_suites = 0
    for t in names:
        info = reg.get(t)
        modules = info["modules"] if info else []
        p = run_build_run(t, modules)
        out = p.stdout + p.stderr
        m = SUMMARY_RE.search(out)
        if m and p.returncode == 0 and m.group(2) == "0":
            print(f"[PASS] {t}: {m.group(1)} checks")
            total_c += int(m.group(1))
        else:
            failed_suites += 1
            print(f"[FAIL] {t}: exit={p.returncode}")
            print(out[-2000:])
    print(f"\n==== wb.py run: {len(names)} 套件, {total_c} checks, {failed_suites} 套失败 ====")
    sys.exit(1 if failed_suites else 0)


def cmd_gate(args):
    reg = load_suites()
    rows = []
    failed = []
    tot_lh = tot_lt = tot_bh = tot_bt = 0
    for t, info in reg.items():
        p = run_build_run(t, info["modules"])
        out = p.stdout + p.stderr
        m = SUMMARY_RE.search(out)
        checks = f"{m.group(1)} ok/{m.group(2)} fail" if m else f"RUN-ERR exit={p.returncode}"
        if not (m and p.returncode == 0 and m.group(2) == "0"):
            failed.append(t + "(运行)")
        gcov = BUILD / t / (info["primary"] + ".gcov")
        if gcov.exists():
            lh, lt, bh, bt = parse_gcov(gcov)
            lp = 100.0 * lh / lt if lt else 0.0
            bp = 100.0 * bh / bt if bt else 0.0
            ok = lp >= args.min_line and bp >= args.min_branch
            rows.append((t, info["primary"], checks, f"{lh}/{lt} {lp:.1f}%", f"{bh}/{bt} {bp:.1f}%",
                         "PASS" if ok else "GATE-FAIL"))
            if not ok:
                failed.append(t + "(覆盖率)")
            tot_lh += lh; tot_lt += lt; tot_bh += bh; tot_bt += bt
        else:
            rows.append((t, info["primary"], checks, "no gcov", "-", "GATE-FAIL"))
            failed.append(t + "(无gcov)")
    print(f"{'套件':<22}{'主测源文件':<20}{'断言':<14}{'行覆盖':<16}{'分支覆盖':<16}门禁")
    for r in rows:
        print(f"{r[0]:<22}{r[1]:<20}{r[2]:<14}{r[3]:<16}{r[4]:<16}{r[5]}")
    lp = 100.0 * tot_lh / tot_lt if tot_lt else 0.0
    bp = 100.0 * tot_bh / tot_bt if tot_bt else 0.0
    print(f"\n总计: 行 {tot_lh}/{tot_lt} ({lp:.1f}%), 分支 {tot_bh}/{tot_bt} ({bp:.1f}%), "
          f"门禁线 行{args.min_line}%/分支{args.min_branch}%")
    if failed:
        print("[GATE-FAIL] " + ", ".join(failed))
        sys.exit(1)
    print("[GATE-PASS] 全部套件通过且覆盖率达标")


def cmd_cases(args):
    n = 0
    for f in sorted((WT / "tests").glob("test_*.c")):
        names = [m.group(1) for m in map(TEST_RE.match, f.read_text(encoding="utf-8", errors="replace").splitlines()) if m]
        n += len(names)
        print(f"{f.name}: {len(names)} 用例")
        for x in names:
            print(f"    {x}")
    print(f"==== 共 {n} 个 TEST ====")


def cmd_vg(args):
    r = subprocess.run([sys.executable, str(SCRIPTS / "cyclomatic.py")] + args.files,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout)
    if r.stderr.strip():
        print(r.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="whitebox.config.json 路径(缺省自动查找)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="生成新模块测试骨架")
    p.add_argument("source", help="被测源文件, 相对 source_root 如 App/NewModule.c")
    p.add_argument("name", nargs="?", help="中文模块名(注释用)")
    p = sub.add_parser("run", help="跑测试套件")
    p.add_argument("tests", nargs="*", help="测试名(缺省=全部)")
    p = sub.add_parser("gate", help="全量回归+覆盖率门禁")
    p.add_argument("--min-line", type=float, default=85.0)
    p.add_argument("--min-branch", type=float, default=80.0)
    sub.add_parser("cases", help="列用例清单")
    p = sub.add_parser("vg", help="环复杂度表")
    p.add_argument("files", nargs="+", help=".c 文件")
    args = ap.parse_args()

    global cfg, WT, WS, SCRIPTS, BUILD, SUITE_JSON, CONFIG_ARG
    CONFIG_ARG = args.config or ""
    cfg = load_config(args.config)
    WT = cfg.test_root
    WS = cfg.base
    SCRIPTS = Path(__file__).resolve().parent
    BUILD = WT / "build"
    SUITE_JSON = WT / "scripts" / "suites.json"
    {"new": cmd_new, "run": cmd_run, "gate": cmd_gate, "cases": cmd_cases, "vg": cmd_vg}[args.cmd](args)


if __name__ == "__main__":
    main()
