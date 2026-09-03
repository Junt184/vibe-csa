<div align="center">

[中文](./README.md) | [English](./README_EN.md)

</div>

# Vibe CSA

> 当前版本：v1.0.20

Vibe CSA (Code Security Audit)，是一款基于 AI Agent 架构的代码审计工具，采用多 Agent 并行执行架构，用“上帝视角”静态审计源代码，用“实战模拟”动态验证漏洞，保证了 Web 漏洞挖掘的全面性和准确性，输出稳定可靠的安全报告，并提供可落地整改建议。主要能力：AI 代码审计和 AI 漏洞评估。

项目特点：
- `Stage 1`：基于源码和语言插件做静态审计
- `Stage 2`：基于静态 finding 做单漏洞动态验证
- `Stage 3`：生成标准 JSON，并导出 HTML / Word 报告

## 目录

- [流程示意图](#流程示意图)
- [提示词示例（强烈推荐使用）](#提示词示例强烈推荐使用)
- [三分钟教学视频](#三分钟教学视频)
- [三步骤快速安装](#三步骤快速安装)
- [环境运行依赖](#环境运行依赖)
- [工作目录与报告输出](#工作目录与报告输出)
- [免责声明](#免责声明)

## 流程示意图

![流程示意图](vibe-csa_v1.0.png)

## 提示词示例（强烈推荐使用）

### Agent 说明

使用 AI 智能体软件调用本技能，即可开启 AI 代码审计（Vibe CSA），会自动创建多个不同角色分工的 Agent 并行审计，子 Agent 详细定义可参考 [references/sub_agents](./references/sub_agents)。

| Agent            | 职责方向                              |
| ---------------- | --------------------------------- |
| static-code-map  | 构建代码事实图谱，为 6 个静态审计 Agent 提供共享上下文 |
| static-injection | SQLi、XSS、命令注入、SSTI 等注入类漏洞         |
| static-auth      | 认证绕过、越权提权、会话管理、接口访问控制缺陷           |
| static-file-ssrf | 文件上传/下载/包含、路径穿越、SSRF、XXE          |
| static-deser     | 反序列化、JNDI、对象注入、危险对象绑定             |
| static-logic     | 支付篡改、状态绕过、竞态条件、CSRF 等业务逻辑漏洞       |
| static-info      | 密钥泄露、硬编码凭据、弱加密、安全配置缺陷             |
| dynamic-verifier | **动态漏洞验证**，验证静态审计到的漏洞是否真实可利用 |

### 1. 纯静态审计模式（安全，不接触目标系统）

- 纯静态审计只分析源代码，不会向目标系统发送任何请求，无影响风险，适合可获取源代码的场景。
- 审计完成后输出标准 JSON，并导出 HTML / Word 报告。

```text
使用 `vibe-csa` 技能对当前目录源码做静态审计：
1. 先启动 `static-code-map` agent，并由它生成 `workDir/agent-results/agent-static-code-map.json`；
2. 再并发启动 6 个静态审计 agent；每个 agent 必须先读取 `agent-static-code-map.json`，再由各自直接生成并回填自己的 `workDir/agent-results/agent-static-*.json`；
3. 最后使用 `merge_static_results.py` 脚本汇总结果，生成 `workDir/static-merged.json`，并使用去重脚本清除重复漏洞项。

将最终 JSON 报告生成 HTML 和 Word 报告：使用 `scripts/vibe_csa_html.py` 和 `scripts/vibe_csa_report.py` 脚本导出稳定的报告结果。
```

### 2. 静态审计 + 动态漏洞验证模式

- 在静态审计基础上，只对“严重/高危/抽样中危”的漏洞进行漏洞验证，产出运行时证据，适合已获取审计目标线上地址和授权的场景。
- 动态验证需要提供目标 URL、授权声明，如有测试账号会自动弹出浏览器，您手工输入账号密码（输入后等浏览器自动关闭）；如果没有测试账号，以下提示词可以删除掉相关内容。

```text
阶段一：静态审计
使用 `vibe-csa` 技能对当前目录源码做静态审计：
1. 先启动 `static-code-map` agent，并由它生成 `workDir/agent-results/agent-static-code-map.json`；
2. 再并发启动 6 个静态审计 agent；每个 agent 必须先读取 `agent-static-code-map.json`，再由各自直接生成并回填自己的 `workDir/agent-results/agent-static-*.json`；
3. 最后使用 `merge_static_results.py` 脚本汇总结果，生成 `workDir/static-merged.json`，并使用去重脚本清除重复漏洞项。

阶段二：动态漏洞验证
只对静态审计到的“严重/高危/抽样中危”的漏洞进行动态验证：先使用 `scripts/prepare_dynamic_pocs.py` 同时生成 `workDir/static-findings/FINDING-*.json`、`workDir/dynamic-findings/FINDING-*.json` 和 `workDir/dynamic-state.json`，再启动 `1~5` 个 `dynamic-verifier` 自定义子 Agent 并发执行漏洞验证，基于 `dynamic-state.json` 的验证队列，读取对应静态参考文件并只回写动态 finding 文件；全部完成后，再使用脚本汇总生成 `workDir/dynamic-verified.json`

目标 URL: https://example.com
授权声明: 已获得书面授权，授权范围包含该目标全部接口和页面

测试账号（1个）:
账号：admin
密码：123456
登录方式：你调用 `scripts/extract_credentials.py` 打开浏览器，我手动输入账号密码登录

白帽子职业操守：允许对测试过程中由自己创建的数据、上传的文件和插入的记录进行删除、修改、恢复和清理，以验证相关安全风险；禁止破坏原始业务数据、真实用户账号与会话、生产数据或超出验证目的的业务对象；所有测试行为应遵循最小影响原则，在获得有效证据后停止不必要的重复利用和扩散操作。

阶段三：报告生成
将最终 JSON 报告生成 HTML 和 Word 报告：使用 `scripts/vibe_csa_html.py` 和 `scripts/vibe_csa_report.py` 脚本导出稳定的报告结果。

```

## 三分钟教学视频

代码审计过程中，要确保智能体软件会调用多个不同角色分工的 Agent 并行审计，否则会影响审计质量和效率。

这是 Vibe Pentest 技能的教学视频，Vibe CSA 安装与使用过程类似，可直接参考。视频包含智能体软件安装介绍、多 Agent 并行运行演示：[3 分钟使用教程](https://www.bilibili.com/video/BV1RiGX6rESQ/)

## 三步骤快速安装

1. 安装 AI 智能体软件（已安装可忽略）

   优先推荐编程类智能体软件：Qoder、Zcode、DeepSeek Harness、Claude Code、OpenCode 等

   > 注意：codex、workbuddy 不太兼容代码审计过程中并发多 Agent 的能力

2. 手工安装 `Git` 代码管理软件工具

   请先手工安装 `Git` 工具，方便后续从代码仓库克隆技能、以及自动更新技能。
   `Git` 工具官方下载地址：[git-scm.com](https://git-scm.com/)。

3. 输入提示词，让 AI 智能体软件自动安装本技能和环境依赖

   `Git` 安装完成后，在 AI 智能体软件中直接发送下面这段提示词即可：

   ```text
   帮我安装 vibe-csa skill（包括环境运行依赖），仓库地址：https://gitee.com/ok-helloworld/vibe-csa
   ```

## 环境运行依赖

### Git

强烈推荐先安装 Git，并使用 `git clone` 获取本项目，不要使用网页下载 ZIP 压缩包的方式使用项目。

推荐优先从 Gitee 克隆，访问更顺畅：

```bash
git clone https://gitee.com/ok-helloworld/vibe-csa
```

推荐原因：

- 只有 Git 仓库方式才能配合项目内的自动更新机制，持续获取最新的技能规则、脚本能力和参考资料
- 这样可以让 AI 智能体持续获得最新的代码审计流程、检测方法和能力增强

### Python

建议使用 Python 3.10+

先安装 Python 依赖：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright jsonschema requests urllib3 python-docx matplotlib httpx charset-normalizer chardet semgrep
```

再安装 Playwright 浏览器依赖，遇到复杂验证码可以调用脚本手工输入账号密码：

```bash
playwright install chromium
```

如果下载卡住或过慢，先切换到国内镜像再安装：

```bash
# Linux/macOS
export PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
# Windows PowerShell（Windows CMD 用 set）
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://cdn.npmmirror.com/binaries/playwright"

playwright install chromium
```

## 工作目录与报告输出

本技能的所有输出都会写入到当前工作目录下的 `workDir/` 文件夹，最终报告位于 `workDir/reports/`。

建议每个代码审计任务使用单独的工作目录，方便区分不同任务的中间文件和最终报告。

## 免责声明

本技能旨在帮助开发人员、安全研究人员和 IT 专业人员在**获得明确授权**的情况下对源代码进行安全审计，并对授权目标系统进行漏洞验证。

**使用本工具即表示您同意：**

- 仅对您拥有所有权或已获得明确授权的源代码进行审计
- 仅在获得明确书面授权的目标系统上进行动态验证
- 遵守所有适用的法律法规和道德准则
- 对任何未经授权的使用或滥用行为承担全部责任

**开发者不对任何滥用行为负责！** 请确保您的使用符合当地法律法规，并获得目标系统所有者的明确授权。
