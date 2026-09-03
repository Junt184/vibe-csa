<div align="center">

[中文](./README.md) | [English](./README_EN.md)

</div>

# Vibe CSA

> Current Version: v1.0.20

Vibe CSA (Code Security Audit) is a code audit tool based on AI Agent architecture, adopting a multi-Agent parallel execution architecture. It statically audits source code with a "God's eye view" and dynamically verifies vulnerabilities through "combat simulation", ensuring the comprehensiveness and accuracy of Web vulnerability discovery, outputting stable and reliable security reports, and providing actionable remediation recommendations. Main capabilities: AI Code Audit and AI Vulnerability Assessment.

Project Features:
- `Stage 1`: Static audit based on source code and language plugins
- `Stage 2`: Dynamic verification of single vulnerabilities based on static findings
- `Stage 3`: Generate standard JSON and export HTML / Word reports

## Table of Contents

- [Flow Diagram](#flow-diagram)
- [Prompt Examples (Highly Recommended)](#prompt-examples-highly-recommended)
- [3-Minute Tutorial Video](#3-minute-tutorial-video)
- [3-Step Quick Installation](#3-step-quick-installation)
- [Runtime Dependencies](#runtime-dependencies)
- [Working Directory & Report Output](#working-directory--report-output)
- [Disclaimer](#disclaimer)

## Flow Diagram

![Flow Diagram](vibe-csa_v1.0.png)

## Prompt Examples (Highly Recommended)

### Agent Overview

By invoking this skill with AI agent software, you can start AI code auditing (Vibe CSA). Multiple Agents with different roles will be automatically created to audit in parallel. For detailed sub-Agent definitions, refer to [references/sub_agents](./references/sub_agents).

| Agent            | Responsibility                                                              |
| ---------------- | --------------------------------------------------------------------------- |
| static-code-map  | Builds the code fact graph and provides shared context for the 6 static audit Agents |
| static-injection | Injection vulnerabilities such as SQLi, XSS, command injection, SSTI, etc.  |
| static-auth      | Authentication bypass, privilege escalation, session management, API access control flaws |
| static-file-ssrf | File upload/download/inclusion, path traversal, SSRF, XXE                   |
| static-deser     | Deserialization, JNDI, object injection, dangerous object binding           |
| static-logic     | Business logic vulnerabilities such as payment tampering, state bypass, race conditions, CSRF, etc. |
| static-info      | Key leakage, hardcoded credentials, weak encryption, security misconfiguration |
| dynamic-verifier | **Dynamic vulnerability verification**, verifies whether vulnerabilities found by static audit are actually exploitable |

### 1. Pure Static Audit Mode (Safe, No Contact with Target System)

- Pure static audit only analyzes source code and does not send any requests to the target system, with no impact risk. Suitable for scenarios where source code is available.
- After the audit is complete, standard JSON is output and HTML / Word reports are exported.

```text
Use the `vibe-csa` skill to perform a static audit on the source code in the current directory:
1. First, launch the `static-code-map` agent and have it generate `workDir/agent-results/agent-static-code-map.json`;
2. Then launch 6 static audit agents in parallel; each agent must read `agent-static-code-map.json` first, then directly generate and write back its own `workDir/agent-results/agent-static-*.json`;
3. Finally, use the `merge_static_results.py` script to aggregate the results into `workDir/static-merged.json`, and run the deduplication script to remove duplicate vulnerability items.

Generate HTML and Word reports from the final JSON report: use the `scripts/vibe_csa_html.py` and `scripts/vibe_csa_report.py` scripts to export stable report results.
```

### 2. Static Audit + Dynamic Vulnerability Verification Mode

- On top of the static audit, only vulnerabilities rated "critical / high-risk / sampled medium-risk" undergo vulnerability verification to produce runtime evidence. Suitable for scenarios where the online address and authorization of the audit target have been obtained.
- Dynamic verification requires a target URL and an authorization statement. If a test account is available, a browser will pop up automatically for you to manually enter the credentials (wait for the browser to close automatically after entering them). If there is no test account, you can remove the related content from the following prompt.

```text
Stage 1: Static Audit
Use the `vibe-csa` skill to perform a static audit on the source code in the current directory:
1. First, launch the `static-code-map` agent and have it generate `workDir/agent-results/agent-static-code-map.json`;
2. Then launch 6 static audit agents in parallel; each agent must read `agent-static-code-map.json` first, then directly generate and write back its own `workDir/agent-results/agent-static-*.json`;
3. Finally, use the `merge_static_results.py` script to aggregate the results into `workDir/static-merged.json`, and run the deduplication script to remove duplicate vulnerability items.

Stage 2: Dynamic Vulnerability Verification
Only perform dynamic verification for vulnerabilities rated "critical / high-risk / sampled medium-risk" in the static audit results: first use `scripts/prepare_dynamic_pocs.py` to generate `workDir/static-findings/FINDING-*.json`, `workDir/dynamic-findings/FINDING-*.json`, and `workDir/dynamic-state.json` at the same time; then launch `1~5` `dynamic-verifier` custom sub-Agents to verify vulnerabilities concurrently. Based on the verification queue in `dynamic-state.json`, each sub-Agent reads the corresponding static reference file and only writes back the dynamic finding file. After all verification is complete, use the script to aggregate the results into `workDir/dynamic-verified.json`

Target URL: https://example.com
Authorization Statement: Written authorization obtained, authorization scope covers all interfaces and pages of the target

Test Account (1):
Username: admin
Password: 123456
Login Method: You invoke `scripts/extract_credentials.py` to open the browser, and I will manually enter the credentials to log in

White hat professional ethics: Allowed to delete, modify, restore, and clean up data created by yourself, files uploaded by yourself, and records inserted by yourself during testing, in order to verify the relevant security risks; prohibited from destroying original business data, real user accounts and sessions, production data, or business objects beyond the purpose of verification; all testing actions should follow the principle of minimal impact, and stop unnecessary repeated exploitation and spreading operations once valid evidence has been obtained.

Stage 3: Report Generation
Generate HTML and Word reports from the final JSON report: use the `scripts/vibe_csa_html.py` and `scripts/vibe_csa_report.py` scripts to export stable report results.

```

## 3-Minute Tutorial Video

During the code audit process, make sure the agent software invokes multiple Agents with different roles to audit in parallel; otherwise, it will affect audit quality and efficiency.

This is the tutorial video of the Vibe Pentest skill. The installation and usage process of Vibe CSA is similar, so you can refer to it directly. The video includes an introduction to agent software installation and a demo of multi-Agent parallel execution: [3-Minute Tutorial](https://www.bilibili.com/video/BV1RiGX6rESQ/)

## 3-Step Quick Installation

1. Install AI agent software (skip if already installed)

   Programming AI agent software is recommended first: Qoder, Zcode, DeepSeek Harness, Claude Code, OpenCode, etc.

   > Note: codex and workbuddy are not very compatible with the concurrent multi-Agent capability during the code audit process

2. Manually install the `Git` source code management tool

   Please install the `Git` tool first, which is convenient for cloning the skill from the repository later and auto-updating the skill.
   Official download for the `Git` tool: [git-scm.com](https://git-scm.com/).

3. Send the prompt to let the AI agent software automatically install this skill and environment dependencies

   After installing `Git`, just send the following prompt in the AI agent software:

   ```text
   Help me install the vibe-csa skill (including environment dependencies), repository: https://gitee.com/ok-helloworld/vibe-csa
   ```

## Runtime Dependencies

### Git

It is strongly recommended to install Git first and use `git clone` to obtain this project. Do not use the web page download ZIP compressed package method.

It is recommended to clone from Gitee first for smoother access:

```bash
git clone https://gitee.com/ok-helloworld/vibe-csa
```

Reasons for recommendation:

- Only the Git repository method can work with the auto-update mechanism in the project to continuously obtain the latest skill rules, script capabilities, and reference materials
- This allows AI agents to continuously obtain the latest code audit processes, detection methods, and capability enhancements

### Python

Python 3.10+ is recommended

First install the Python dependencies:

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright jsonschema requests urllib3 python-docx matplotlib httpx charset-normalizer chardet semgrep
```

Then install the Playwright browser dependency. If you encounter complex CAPTCHAs, you can invoke the script to open the browser and manually enter the account credentials:

```bash
playwright install chromium
```

If the download gets stuck or is too slow, switch to a domestic mirror first, then install:

```bash
# Linux/macOS
export PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
# Windows PowerShell (use set on Windows CMD)
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://cdn.npmmirror.com/binaries/playwright"

playwright install chromium
```

## Working Directory & Report Output

All outputs from this skill will be written to the `workDir/` folder in the current working directory, with the final report located in `workDir/reports/`.

It is recommended to use a separate working directory for each code audit task to facilitate distinguishing intermediate files and final reports for different tasks.

## Disclaimer

This skill is intended to help developers, security researchers, and IT professionals perform security audits on source code and verify vulnerabilities on authorized target systems **with explicit authorization**.

**By using this tool, you agree to:**

- Only audit source code that you own or for which you have obtained explicit authorization
- Only perform dynamic verification on target systems for which you have obtained explicit written authorization
- Comply with all applicable laws, regulations, and ethical standards
- Take full responsibility for any unauthorized use or abuse

**The developers assume no responsibility for any abuse!** Please ensure your usage complies with local laws and regulations, and that you have obtained explicit authorization from the owner of the target system.
