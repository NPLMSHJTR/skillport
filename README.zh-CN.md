# skillport

[English](README.md) | [简体中文](README.zh-CN.md)

**Agent Skill 只写一份主源，自动同步到各个智能体目录，并在副本发生漂移时第一时间告警。**

[![CI](https://github.com/NPLMSHJTR/skillport/actions/workflows/ci.yml/badge.svg)](https://github.com/NPLMSHJTR/skillport/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)

不同编码智能体读取 Skills 的目录各不相同（`.codex/skills/`、`.claude/skills/`、`.agents/skills/`、`.cursor/skills/`、`.gemini/skills/`、`.windsurf/skills/`、`.opencode/skills/`）。人工到处复制很快就会改乱版本。`skillport` 维护唯一主目录 `skills/`，一键同步到各目标目录，并通过跨平台归一化指纹检测副本漂移。

```console
$ skillport check

source: skills  (2 skills)
targets: codex, claude, agents

  sync     codex      changelog-from-tags
  sync     codex      csv-profile
  sync     claude     changelog-from-tags
  drifted  claude     csv-profile
             changed: SKILL.md
  sync     agents     changelog-from-tags
  sync     agents     csv-profile

1 drifted  → run `skillport sync`
```

## 操作工作流与流程图

```mermaid
flowchart LR
    A["1. 只修改主源目录<br/>(skills/<name>/SKILL.md)"] --> B["2. 预览将同步的目标<br/>(skillport sync --dry-run)"]
    B --> C["3. 同步到各 Agent 目录<br/>(skillport sync -> .codex / .claude / .cursor ...)"]
    C --> D["4. 在 CI / Hook 中只读检查漂移<br/>(skillport check)"]
    D -->|发现漂移| C
    D -->|清理废弃副本| E["skillport prune --yes"]
```

## 安装与常用工作流命令

```bash
pipx install git+https://github.com/NPLMSHJTR/skillport
# 或零依赖从源码运行：
git clone https://github.com/NPLMSHJTR/skillport && cd skillport && python -m skillport check .
```

```bash
skillport list                      # 查看支持的智能体目标目录与预设组
skillport check                     # 只读检查各目标是否漂移（适合 CI）
skillport sync                      # 将 skills/ 同步到全部目标目录
skillport sync --dry-run            # 预览同步变更，不实际写盘
skillport sync --skill my-skill     # 仅同步指定 Skill
skillport prune                     # 预览孤立废弃目录
skillport prune --yes               # 显式确认删除孤立目录
```

退出码：`0` 全部同步；`1` `check` 发现缺失、漂移或多余副本；`2` 用法错误或 `prune` 未加 `--yes`。

## 支持的目标与设计要点

- 支持目标：`codex`（`.codex/skills`）、`claude`（`.claude/skills`）、`agents`（`.agents/skills`）、`cursor`（`.cursor/skills`）、`gemini`（`.gemini/skills`）、`windsurf`（`.windsurf/skills`）、`opencode`（`.opencode/skills`），兼容性核验说明见 [docs/compatibility.md](docs/compatibility.md)。
- **归一化指纹**：忽略行尾 CRLF/LF 差异与打包元数据文件，避免跨 Windows/Linux 误报。
- **不使用软链接**：复制真实文件，避免 Windows 与容器环境下软链接失效。

## 开源协议

MIT，详见 [LICENSE](LICENSE)。
