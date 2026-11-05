#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whitebox.config.json 加载器（被 build_run.py / wb.py / coverage_report.py 共用）。

配置文件放在被测工程根目录（或其任意子目录向上可找到），键（路径相对配置文件所在目录）:
  {
    "test_root":    "whitebox-test",                 // 测试根目录(harness/tests/stubs/build), 默认 whitebox-test
    "source_root":  "path/to/MainProject/source",    // 必填: 被测源码根目录
    "include_dirs": ["path/to/bsp"],                 // 附加头文件目录(可选)
    "source_tag":   "my-project",                    // gcov Source 过滤标记(可选, 默认取 source_root 末段)
    "gcc":          "C:/msys64/ucrt64/bin/gcc.exe",  // 可选, 默认 PATH 查找 gcc
    "gcov":         "C:/msys64/ucrt64/bin/gcov.exe"  // 可选, 默认 PATH 查找 gcov
  }
查找顺序: --config 显式指定 > 环境变量 WHITEBOX_CONFIG > 从 CWD 逐级向上找 whitebox.config.json。
"""
import json
import os
import shutil
import sys
from pathlib import Path


class WbConfig:
    def __init__(self, cfg_path: Path):
        self.cfg_path = cfg_path.resolve()
        self.base = self.cfg_path.parent
        raw = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.test_root = (self.base / raw.get("test_root", "whitebox-test")).resolve()
        if "source_root" not in raw:
            sys.exit(f"[x] {self.cfg_path} 缺少 source_root")
        self.source_root = (self.base / raw["source_root"]).resolve()
        self.include_dirs = [(self.base / d).resolve() for d in raw.get("include_dirs", [])]
        self.source_tag = raw.get("source_tag", self.source_root.name)
        self.gcc = raw.get("gcc") or self._find_tool("gcc")
        self.gcov = raw.get("gcov") or self._find_tool("gcov")

    @staticmethod
    def _find_tool(name):
        hit = shutil.which(name)
        if hit:
            return hit
        for cand in (Path(r"C:\msys64\ucrt64\bin") / (name + ".exe"),
                     Path(r"C:\msys64\mingw64\bin") / (name + ".exe")):
            if cand.exists():
                return str(cand)
        return name  # 交给子进程报 not-found


def load_config(explicit=None) -> WbConfig:
    if explicit:
        return WbConfig(Path(explicit))
    env = os.environ.get("WHITEBOX_CONFIG")
    if env:
        return WbConfig(Path(env))
    d = Path.cwd().resolve()
    for p in [d, *d.parents]:
        cand = p / "whitebox.config.json"
        if cand.exists():
            return WbConfig(cand)
    sys.exit("[x] 未找到 whitebox.config.json（放被测工程根目录, 格式见 wbconfig.py 头注释, "
             "或用 --config / 环境变量 WHITEBOX_CONFIG 指定）")
