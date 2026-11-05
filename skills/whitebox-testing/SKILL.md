---
name: whitebox-testing
description: 嵌入式 C 代码白盒测试标准化流程：结构分析、宿主机打桩测试、gcov 覆盖率闭环、缺陷分级、控制逻辑学习手册。用于"对某模块做白盒测试""更新代码后回归验证""通过测试理解代码控制逻辑"等任务。
---

# 白盒测试工作流（嵌入式 C / 宿主机 GCC + gcov）

目标产出两件事：①**证明**——测试过程与覆盖率的证据链；②**学会**——控制逻辑学习手册（帮助工程师掌握代码逻辑，对照功能书/更改单做修改）。

## P0 范围界定

- 与用户确认：**范围**（哪些模块/层级）、**交付物清单**、**格式**（Markdown 文档集）。
- 标准交付物 7 件：00 控制逻辑学习手册、01 结构分析、02 测试用例表、03 测试脚本说明、04 覆盖率报告、05 执行记录、06 汇总报告。
- 小型纯逻辑模块可先行试点 2~3 个，验证 harness 后再批量铺开。

## P1 结构分析（先读代码再写测试）

- 画运行流程全景：上电入口 → 主循环 → 中断时基 → 任务分发（带源码行号）。
- 每模块输出：函数清单、环复杂度 V(G)（`wb.py vg <files>`，>10 列为重点）、独立路径（基路径/边覆盖路径）。
- 识别三类特殊结构并单独标注：**大面积注释禁用代码**（活跃口径 vs 完整口径要写明）、**空壳模块**（状态机定义了但没接线）、**编译期 #if 裁剪分支**（不可覆盖项）。

## P2 测试 harness（三类打桩 + 两个白盒技巧）

三类打桩：
1. **MCU 头/寄存器桩**：按芯片系列写桩头（参考 templates/harness/hc32_ll.h.example），只声明被用到的类型/函数。
2. **硬件调用记录器**（hwlog.h）：GPIO/UART/ADC/Flash/喂狗调用记入事件队列，断言调用序列与次数；返回值可编程（模拟 ADC 值、写失败等）。
3. **跨模块全局桩**：在 stub_<mod>.c 里 `#include 头` 后定义实例（如 `SysModeCtrl_t SysModeCtrl_out;`）。

两个白盒技巧：
- **#include 被测 .c**：测试文件直接 include 被测 .c 成同编译单元，可访问/重置 static 变量；此时 `--modules` 留空，gcov 归属仍正确。
- **#undef/#define 重定向**：把 `DataFlashRead` 等底层宏重定向到假外设（如 8KB 假闪存），模拟失败注入。

构建约定：宿主机 GCC + `--coverage`，per-source 单独编译避免 .gcno 重名；**工具路径与源码根写进 whitebox.config.json**（见 scripts/wbconfig.py 头注释）。

## P3 用例设计优先级

1. 入口函数冒烟（基本可达）→ 2. 每个分支条件的真假方向（语句+分支覆盖）→ 3. 独立路径 → 4. 边界/饱和/回绕（uint 回绕安全比较、0xFFFF 饱和、顶格索引）→ 5. **缺陷锁定用例**（发现缺陷后写一个当前行为的锁定用例，修复后翻转断言）。命名 `<ID>_<目标>`，ID 与用例表一一对应。

## P4 实现与执行

- `wb.py new <相对source/的Mod.c>` 生成骨架并注册 suites.json → 填用例 → `wb.py run <test>` → 达标后 `wb.py gate`。
- 每个模块建独立测试套件（主测工程），跨模块依赖走 `--modules` 链真实现或打桩。
- 每发现一个缺陷：记入 fragment（等级/位置/复现/建议），并固化锁定用例。

## P5 覆盖率闭环（口径是关键）

- **主测口径为准**：各模块以其专属测试工程的单份 `<primary>.gcov` 统计；跨 build 并集会因 gcov 分支编号错位虚增分支总数，仅作交叉参考。
- 验收线默认：行 ≥85%、分支 ≥80%（`wb.py gate --min-line --min-branch` 可调）。
- 残余未覆盖边**逐条归因**：死分支/防御性判空（可留）vs 漏测（必须补）vs 不可安全测试（如 NULL 解引用路径，列不可覆盖表并写明原因）。

## P6 缺陷分级

- [高] 功能失效/崩溃/数据丢失；[中] 异常工况错误/不可重入/与注释或平行模块不一致；[低] 命名/注释/硬编码。
- 报告格式：等级 | 位置（文件:行号）| 现象 | 复现（用例 ID）| 建议。
- 禁用代码内的缺陷标"·禁用"，与活跃缺陷分开；恢复启用前列修复清单。

## P7 文档交付

- 00 控制逻辑学习手册：每模块"功能定位/运行流程/核心逻辑详解（讲为什么）/条件路径表（条件→行为→行号→功能书变更落点）/状态变量清单/功能书对照练习/易错点"。**这份文档服务于"读懂控制逻辑"，是学习成果的主要载体。**
- 01 结构分析、02 用例表（用例×覆盖目标映射）、03 脚本说明（含环境坑）、04 覆盖率报告（主测口径+残余归因）、05 执行记录（可复现命令）、06 汇总报告（缺陷汇总+处置优先级）。
- fragments/ 放各模块明细，主文档引用不重复。

## 环境坑清单（Windows + MSYS2）

1. gcc 静默 exit 1 + cc1.exe 0xC0000139：PATH 被其他工具链 DLL 污染，构建前置 ucrt64\bin 到 PATH（build_run.py 已处理）。
2. subprocess 解码：必须 `encoding="utf-8", errors="replace"`，否则中文诊断触发 UnicodeDecodeError 吞真错。
3. 控制台打印非 ASCII 前 `sys.stdout.reconfigure(encoding="utf-8")`，否则 GBK UnicodeEncodeError。
4. gcov `-c` 分支行是 `branch N taken <次数>` 不是百分比。
5. `Path("M.c").stem` 会把 .c 吃掉（="M"），gcov 文件名用 `primary + ".gcov"`。
6. Python f-string 里嵌 C 代码大括号会 SyntaxError，模板用占位符 replace。

## 增量回归（代码更新时）

1. diff 定位受影响模块 → 2. `wb.py gate` 一键回归+门禁（不达标非零退出）→ 3. 新增/变更分支补用例（按 P3 优先级）→ 4. 更新文档数字 → 5. 高危缺陷复核是否已修（用锁定用例反向验证）。

## wb.py 用法

```
python <技能>/scripts/wb.py new App/NewModule.c   # 生成 test_/stub_ 骨架
python <技能>/scripts/wb.py run [test_a test_b]   # 跑指定/全部套件
python <技能>/scripts/wb.py gate                  # 全量回归+覆盖率门禁（CI 用，非零退出=不达标）
python <技能>/scripts/wb.py cases                 # 输出 TEST() 用例清单
python <技能>/scripts/wb.py vg App/Mod.c          # 环复杂度表
```

脚本全部由 whitebox.config.json 驱动（source_root/test_root/gcc 等），多项目复用零改动。
