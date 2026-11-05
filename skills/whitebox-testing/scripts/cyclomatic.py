#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环复杂度(扩展McCabe)统计: V(G) = 1 + 判定节点数(每 if/else-if/for/while/case/&&/||/?: 各计1)。
按函数输出, 函数识别: 返回类型+函数名(...  换行 '{' 的常见嵌入式风格。
忽略注释与字符串/字符字面量。

用法: python cyclomatic.py <file.c> [file2.c ...]   输出 markdown 表
"""
import re
import sys
from pathlib import Path

KW = re.compile(r"\b(if|for|while|case)\b|&&|\|\||\?(?!\?)")
FUNC = re.compile(r"^[A-Za-z_][\w\s\*]*?\b(\w+)\s*\([^;]*\)\s*$")


def strip_comments_strings(src: str) -> str:
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i+1] == '/':
            j = src.find('\n', i)
            i = n if j < 0 else j
        elif c == '/' and i + 1 < n and src[i+1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c in ('"', "'"):
            q = c
            j = i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == '\\' else 1
            out.append(' ' * (j - i + 1))
            i = j + 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def analyze(path: Path):
    text = strip_comments_strings(path.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    funcs = []   # (name, start, end)
    i = 0
    while i < len(lines):
        m = FUNC.match(lines[i].rstrip())
        if m and not lines[i].lstrip().startswith(('typedef', 'struct', 'extern', '#')):
            # 找到函数体 '{'
            j = i
            while j < len(lines) and '{' not in lines[j]:
                if ';' in lines[j]:
                    break
                j += 1
            if j < len(lines) and '{' in lines[j] and ';' not in lines[j]:
                depth = 0
                k = j
                while k < len(lines):
                    depth += lines[k].count('{') - lines[k].count('}')
                    if depth == 0 and k > j:
                        break
                    k += 1
                funcs.append((m.group(1), i, k))
                i = k + 1
                continue
        i += 1

    rows = []
    for name, a, b in funcs:
        body = "\n".join(lines[a:b+1])
        dec = len(KW.findall(body))
        rows.append((name, b - a + 1, dec, dec + 1))
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total_v = 0
    for f in sys.argv[1:]:
        p = Path(f)
        rows = analyze(p)
        print(f"\n## {p.name}\n")
        print("| 函数 | 行数 | 判定节点 | V(G) |")
        print("|---|---|---|---|")
        for name, ln, dec, v in rows:
            flag = " [高]" if v > 10 else ""
            print(f"| {name} | {ln} | {dec} | {v}{flag} |")
        tv = sum(r[3] for r in rows)
        total_v += tv
        print(f"\n模块合计 V(G) = {tv}\n")
    print(f"\n**全部模块 V(G) 总计 = {total_v}**")


if __name__ == "__main__":
    main()
