# dsh-plugin-whitebox-testing

DSH 技能插件：嵌入式 C 白盒测试标准化工作流。技能被 DSH 自动发现后，说"对 XX 模块做白盒测试"即可按 P0~P7 流程执行。

## 提供什么

| 内容 | 说明 |
|---|---|
| `skills/whitebox-testing/SKILL.md` | 方法论与判断规则：范围界定→结构分析→三类打桩→用例设计→执行→覆盖率闭环口径→缺陷分级→文档交付（含控制逻辑学习手册），附环境坑清单与增量回归 5 步 |
| `skills/whitebox-testing/scripts/wb.py` | 测试驱动：`new`（生成 test/stub 骨架并注册）/ `run` / `gate`（覆盖率门禁，CI 非零退出）/ `cases` / `vg`（环复杂度） |
| `skills/whitebox-testing/scripts/build_run.py` | 构建+执行+gcov（宿主机 GCC） |
| `skills/whitebox-testing/scripts/coverage_report.py` | gcov 聚合报告（markdown） |
| `skills/whitebox-testing/scripts/cyclomatic.py` | 扩展 McCabe 环复杂度表 |
| `skills/whitebox-testing/templates/harness/` | harness 模板：test_framework.h、hwlog.h（硬件调用记录器）、hc32_ll.h.example / stubs_hw.c.example（MCU 桩示例，按芯片适配） |

## 安装

```sh
dsh plugin add <本仓库>          # 或 DSH 内 plugin_manager 安装
```

要求 Node.js >= 22.19。安装后 DSH 自动发现 `skills/whitebox-testing`。

## 使用

1. 在被测工程根目录放 `whitebox.config.json`（键说明见 `scripts/wbconfig.py` 头注释）：

```json
{
  "test_root": "whitebox-test",
  "source_root": "path/to/source",
  "include_dirs": ["path/to/bsp"],
  "gcc": "C:/msys64/ucrt64/bin/gcc.exe"
}
```

2. 对 DSH 说"对 App/Defrost.c 做白盒测试"——技能按 SKILL.md 流程产出 7 件文档 + 可执行测试 + 覆盖率门禁。

## 实证

方法论与脚本已在一套 2 万行 VRF 多联机室外机固件（HC32F175, IAR 工程）上完整走通：10 个模块、217 个测试用例、1639 断言全绿，行覆盖 100%、分支覆盖 97.3%（主测口径），发现约 70 处缺陷（高危 11 处）。`wb.py gate` 端到端通过。

## 提交插件市场（awesome-dsh-plugin）

投稿是**一个文件**的 PR：`data/plugins/<owner>__<repo>.yml`，草稿见 `docs/marketplace-entry.yml`。CI 检查清单（详见 [contributing.md](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/main/contributing.md)）：

- [x] `package.json` 声明 `dsh.bundle`（含 `patch: ./cordis.patch.yml`）——已具备
- [x] 仓库根有 `cordis.patch.yml`（`- insert: id/name`）——已具备
- [ ] 建独立 GitHub 仓库、添加 `dsh-plugin` topic、**仓库创建满 1 天**
- [ ] 填写 `package.json` 的 `repository` 字段指向该仓库
- [ ] 可选：`screenshots.json` 截图、发布 npm（免构建授权）
- [ ] 提 PR（单 PR ≤3 条目；描述不带营销词、与代码一致）

## License

MIT
