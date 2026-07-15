# 静态审计 JSON 安全回填

## 适用对象

- `static-code-map`
- `static-injection`
- `static-auth`
- `static-file-ssrf`
- `static-deser`
- `static-logic`
- `static-info`

本说明仅关注 `Stage 1` 静态审计结果的安全回填，目的是减少静态 Agent 的上下文占用。

## 适用场景

在 `Windows/PowerShell` 环境下，以下内容不要直接在 shell 中拼接到 JSON：

- 长中文说明
- HTML 片段
- 多行代码片段
- 带引号、反斜杠、换行的证据文本
- 较长的修复建议

推荐做法：

1. 先把复杂内容写入临时文件
2. 再通过 `scripts/json_safe_update.py` 更新目标结果文件

## 常用字段

静态 Agent 通常更新：

```text
findings[0].title
findings[0].description
findings[0].impact
findings[0].fix.language
findings[0].fix.before
findings[0].fix.after
findings[0].remediation.short_term
findings[0].remediation.long_term
audit.coverage_summary
```

## 推荐命令

### 回填长文本

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/agent-results/agent-static-auth.json `
  --set-file findings[0].description=workDir/tmp/description.txt `
  --set-file findings[0].impact=workDir/tmp/impact.txt `
  --check-text-quality
```

### 回填修复代码

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/agent-results/agent-static-auth.json `
  --set-file findings[0].fix.before=workDir/tmp/fix-before.php `
  --set-file findings[0].fix.after=workDir/tmp/fix-after.php `
  --check-text-quality
```

### 回填结构化对象

如果覆盖说明或附加信息先整理成对象，可使用：

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/agent-results/agent-static-auth.json `
  --set-json-file audit.coverage_summary=workDir/tmp/coverage-summary.json `
  --check-text-quality
```

## 推荐规则

1. 短字符串可用 `--set`
2. 长文本优先用 `--set-file`
3. 对象 / 数组优先用 `--set-json-file` 或 `--append-json-file`
4. 回填后继续执行该 Agent 原本要求的 JSON 合法性检查
5. 需要文本质量兜底时，建议加 `--check-text-quality`

## 不推荐做法

- 不要直接用 PowerShell 拼大段 JSON 再整体覆盖结果文件
- 不要把多行代码片段直接塞进命令行参数
- 不要在 shell 中手工转义多层引号和反斜杠后再覆盖 finding 文件
