# 动态验证 JSON 安全回填

## 适用对象

- `dynamic-verifier`

本说明仅关注 `Stage 2` 动态漏洞验证结果与状态文件的安全回填，目的是减少动态 Agent 的上下文占用。

## 适用场景

在 `Windows/PowerShell` 环境下，以下内容不要直接在 shell 中拼接到 JSON：

- 原始 HTTP 请求 / 响应报文
- HTML 页面片段
- 长中文说明
- 复杂正则命中片段
- `attempts[]`、`poc.steps[]`、`poc.evidence[]` 这类结构化对象
- `dynamic-state.json` 的并发状态更新

推荐做法：

1. 先把复杂文本写入临时 `.txt` 文件
2. 把结构化对象写入临时 `.json` 文件
3. 再通过 `scripts/json_safe_update.py` 回填

## 常用字段

动态 Agent 通常更新：

```text
poc.result
status
dynamic_verification.state
dynamic_verification.runtime_notes
dynamic_verification.final_evidence.summary
dynamic_verification.attempts
poc.steps
poc.evidence
poc.failure_log
```

状态文件通常更新：

```text
findings[0].queue_state
findings[0].leased_by
findings[0].lease_until
findings[0].last_error
agents[0].current_vuln_id
```

## 推荐命令

### 回填长文本证据

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/dynamic-findings/FINDING-001.json `
  --set-file dynamic_verification.final_evidence.summary=workDir/tmp/http-output.txt `
  --set-file dynamic_verification.runtime_notes=workDir/tmp/runtime-notes.txt `
  --check-text-quality
```

### 追加 attempts / poc.steps / evidence

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/dynamic-findings/FINDING-001.json `
  --append-json-file dynamic_verification.attempts=workDir/tmp/attempt-1.json `
  --append-json-file poc.steps=workDir/tmp/poc-step-1.json `
  --append-json-file poc.evidence=workDir/tmp/poc-evidence-1.json `
  --check-text-quality
```

### 更新动态状态文件

并发场景下建议始终开启文件锁：

```powershell
python .trae/skills/vibe-csa/scripts/json_safe_update.py `
  --file workDir/dynamic-state.json `
  --set findings[0].queue_state=running `
  --set findings[0].leased_by=dynamic-verifier-1 `
  --set agents[0].current_vuln_id=FINDING-001 `
  --lock `
  --print-summary
```

## 与 http_test.py 的配合

若 `http_test.py` 输出较长：

1. 优先用 `--data-file`
2. 复杂过滤优先用 `--response-filter-file`
3. 输出先落到临时文件
4. 再用 `json_safe_update.py --set-file` 或 `--append-json-file` 回填

## 推荐规则

1. 短字符串可用 `--set`
2. 长文本优先用 `--set-file`
3. 对象 / 数组优先用 `--set-json-file` 或 `--append-json-file`
4. 更新 `dynamic-state.json` 时优先加 `--lock`
5. 回填后继续执行 `dynamic-verifier` 要求的 JSON 合法性和一致性校验

## 不推荐做法

- 不要直接把原始 HTTP 报文塞进命令行参数
- 不要在 shell 中手工拼接大段 JSON 然后覆盖 `dynamic-findings/*.json`
- 不要在多个并行 Agent 中无锁写同一个 `dynamic-state.json`
