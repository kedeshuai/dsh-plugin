#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
白盒单元测试 构建+执行+覆盖率（宿主机 GCC + gcov, 配置驱动版）

用法:
  python build_run.py --test test_my_module --modules path/to/my_module.c
  python build_run.py --test test_common --modules Common/Common.c
  python build_run.py --test test_my_module                      # 测试内 #include 被测 .c 时 --modules 留空

说明:
  路径来自 whitebox.config.json（见 wbconfig.py 头注释）:
  --modules  相对 source_root 的被测源文件
  --stubs    相对 <test_root>/stubs/ 的补充桩文件(可多个)
  测试文件固定为 <test_root>/tests/<test>.c
  产物在 <test_root>/build/<test>/ 下: 目标文件、可执行、.gcno/.gcda、*.gcov
  自动挂载 <test_root>/stubs/stub_<test去掉test_前缀>.c（如存在）
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wbconfig import load_config   # noqa: E402


def make_env(cfg):
    env = os.environ.copy()
    gcc_dir = str(Path(cfg.gcc).resolve().parent)
    env["PATH"] = gcc_dir + os.pathsep + env.get("PATH", "")
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True, help="测试名, 对应 tests/<test>.c")
    ap.add_argument("--modules", nargs="*", default=[],
                    help="被测源文件(相对 source_root); 测试文件内 #include 被测 .c 时留空")
    ap.add_argument("--stubs", nargs="*", default=[], help="补充桩文件(相对 stubs/)")
    ap.add_argument("--no-run", action="store_true", help="只编译链接不执行")
    ap.add_argument("--config", help="whitebox.config.json 路径(缺省自动查找)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    WT = cfg.test_root
    SRC = cfg.source_root

    build = WT / "build" / args.test
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    test_src = WT / "tests" / f"{args.test}.c"
    if not test_src.exists():
        print(f"[ERROR] 测试文件不存在: {test_src}")
        return 2

    sources = [test_src, WT / "harness" / "stubs_hw.c"]
    for m in args.modules:
        p = SRC / m
        if not p.exists():
            print(f"[ERROR] 被测源文件不存在: {p}")
            return 2
        sources.append(p)
    for s in args.stubs:
        p = WT / "stubs" / s
        if not p.exists():
            print(f"[ERROR] 桩文件不存在: {p}")
            return 2
        sources.append(p)
    auto = WT / "stubs" / ("stub_" + args.test.replace("test_", "") + ".c")
    if auto.exists() and auto not in sources:
        sources.append(auto)

    includes = [WT / "harness", WT / "stubs", *cfg.include_dirs]
    if SRC.exists():
        includes += [d for d in sorted(SRC.iterdir()) if d.is_dir()]

    CFLAGS = ["--coverage", "-O0", "-g", "-std=gnu11", "-Wall", "-Wno-unused-variable",
              "-Wno-unused-but-set-variable", "-Wno-unused-function", "-Wno-parentheses",
              "-Wno-sign-compare", "-Wno-pointer-sign", "-Wno-char-subscripts"]

    env = make_env(cfg)
    objs = []
    for s in sources:
        obj = build / (s.stem + ".o")
        cmd = [cfg.gcc, *CFLAGS, "-c", "-o", str(obj), str(s)]
        cmd += ["-I" + str(d) for d in includes]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[COMPILE FAIL] {s.name}")
            print(r.stdout)
            print(r.stderr)
            return 1
        if r.stderr.strip():
            print(f"[warn {s.name}] {r.stderr.strip()}")
        objs.append(obj)

    exe = build / (args.test + ".exe")
    cmd = [cfg.gcc, "--coverage", "-O0", "-g", "-o", str(exe)] + [str(o) for o in objs] + ["-lm"]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[LINK FAIL]")
        print(r.stdout)
        print(r.stderr)
        return 1

    print(f"[BUILD OK] {exe}")
    if args.no_run:
        return 0

    r = subprocess.run([str(exe)], cwd=str(build), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout)
    if r.stderr.strip():
        print("[stderr]", r.stderr)

    for gcno in sorted(build.glob("*.gcno")):
        subprocess.run([cfg.gcov, "-b", "-c", gcno.name], cwd=str(build), env=env,
                       capture_output=True, text=True)
    print(f"[GCOV] 覆盖率文件已生成于 {build}")
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
