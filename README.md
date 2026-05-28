
---
name: shang-hai-rpa
description: 执行上海访护 RPA 自动化程序或查询其执行结果。包括前置环境检查、后台启动 exe 程序、查询任务状态和日志结果。Use when the user mentions 上海访护、访护生成、RPA 执行结果、任务完成了吗, or wants to run/check the Shanghai home-care RPA task.
---

# 上海访护 RPA 执行技能

本技能指导 Agent 完成上海访护 RPA 自动化程序的前置检查与执行。

## 配置项

| 参数　　　　 | 默认值　　　　　　　　　　　　　　　　 | 说明　　　　　　　　　　　　　　 |
| --------------| ----------------------------------------| ----------------------------------|
| EXE 路径　　 | `C:\RPA\上海访护生成\上海访护生成.exe` | RPA 自动化程序路径　　　　　　　 |
| 日志路径　　 | `C:\RPA\rpa.log`　　　　　　　　　　　 | exe 生成的执行日志文件　　　　　 |
| 结果文件　　 | `C:\RPA\rpa_result.json`　　　　　　　 | 脚本写入的任务状态和结果　　　　 |
| CDP 端口　　 | `5333`　　　　　　　　　　　　　　　　 | Chrome 远程调试端口　　　　　　s |
| 标签页关键词 | `易照护`　　　　　　　　　　　　　　　 | 用于匹配目标标签页标题的关键词　 |

如果用户指定了不同的值，使用用户提供的值替换默认值。

### Chrome 启动参数

RPA 程序通过 Chrome DevTools Protocol (CDP) 控制浏览器，Chrome 必须以如下参数启动：

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=5333 --user-data-dir="C:\RPA\Chrome\User Data" --remote-allow-origins=*
```

此参数通常已配置在 Chrome 快捷方式的启动属性中，无需每次手动输入。

---

## 执行流程

> ⚠️ **严格约束：步骤必须按序执行，禁止跳过**
> - 在步骤 1 的脚本 exit code 返回 `0` 之前，**绝对不能执行步骤 3**
> - 即使用户明确说「直接执行」或「跳过检查」，也必须先完成步骤 1 和步骤 2
> - 步骤 1 未执行或未通过 → 终止流程，告知用户原因

复制以下清单跟踪进度：

```
任务进度：
- [ ] 步骤 1：运行前置检查脚本
- [ ] 步骤 2：处理检查结果
- [ ] 步骤 3：启动 RPA 任务（后台执行，立即返回）
- [ ] 步骤 4：（用户主动询问时）查询执行结果
```

---

### 步骤 1：运行前置检查脚本

使用 Shell 工具执行检查脚本，该脚本通过 CDP 远程调试协议自动完成三项检查：

```powershell
python "./scripts/check_browser.py"
```

> **路径说明**：`.` 即 `SKILL同级目录`，则完整命令为：
> ```powershell
> python ".\scripts\check_browser.py"
> ```

脚本自动检查以下四项：
1. **Chrome 远程调试是否可达** — 通过 `urllib` 请求 `localhost:5333/json` 探测端口（不会自动启动浏览器）
2. **易照护标签页是否存在** — 先从 CDP 返回的标签页列表预检，再通过 DrissionPage 精确获取标签页
3. **是否已登录** — 通过 DrissionPage 查找页面中的已登录特征元素（`h1.sidebar-title` 且文本包含「易照护平台」）
4. **必需文件是否存在** — 检查以下文件，并在 JSON 输出中通过 `missing_files` 字段返回缺失文件详情（含文件名、说明、是否可由用户上传）：
   - `C:\RPA\上海访护生成\上海访护生成.exe`（系统文件，不可上传）
   - `C:\RPA\回访\回访情况表.xlsx`（数据文件，可由用户上传）
   - `C:\RPA\回访\妙阖护士护理员信息.xlsx`（数据文件，可由用户上传）

脚本输出 JSON 格式结果。

---

### 步骤 2：处理检查结果

根据脚本的 exit code 和 JSON 输出判断下一步操作：

| exit code | 含义 | 操作 |
|-----------|------|------|
| `0` | 全部通过 | 继续步骤 3 |
| `1` 且 `missing_files` 为空 | 非文件类检查未通过 | 读取 `message` 字段内容告知用户，**终止流程** |
| `1` 且 `missing_files` 非空 | 必需文件缺失 | 进入 **步骤 2a：处理缺失文件** |

**JSON 输出字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `chrome_running` | bool | Chrome 远程调试是否可达 |
| `tab_found` | bool | 是否找到易照护标签页 |
| `logged_in` | bool/null | 登录状态：true=已登录，false=未登录 |
| `files_ok` | bool | 必需的 Excel 文件是否齐全 |
| `tab_title` | string | 匹配到的标签页标题 |
| `tab_url` | string | 匹配到的标签页 URL |
| `message` | string | 人类可读的结果描述 |
| `missing_files` | list | 缺失文件详情列表，每项包含 `path`、`name`、`description`、`uploadable` |

---

### 步骤 2a：处理缺失文件

当 `missing_files` 非空时，按照以下逻辑处理：

**1. 区分文件类型：**
- `uploadable: true` — 用户可上传的数据文件（如 `.xlsx` 表格）
- `uploadable: false` — 系统级文件（如 `.exe` 程序），用户无法直接提供

**2. 对于可上传文件（`uploadable: true`）：**

向用户展示缺失文件清单，并明确提示用户在聊天中上传对应文件：

> 前置检查发现以下数据文件缺失，需要您提供：
>
> | 文件名 | 说明 | 目标路径 |
> |--------|------|----------|
> | [name] | [description] | [path] |
>
> 请在聊天中直接上传对应的文件，我会自动将它们放置到正确位置。

**3. 用户上传文件后：**

用户通过聊天上传文件后，Agent 应：
1. 使用 Shell 工具确保目标目录存在：`mkdir -p "目标目录"` (PowerShell: `New-Item -ItemType Directory -Force -Path "目标目录"`)
2. 使用 Shell 工具将上传的文件复制到 `missing_files` 中对应条目的 `path` 路径
3. 复制完成后，**重新执行步骤 1** 运行前置检查脚本，确认文件已就位
4. 如果检查通过，继续步骤 3

**4. 对于不可上传文件（`uploadable: false`）：**

告知用户该文件为系统级程序文件，需联系管理员部署，**终止流程**。

**5. 混合情况（同时存在可上传和不可上传文件）：**

优先处理不可上传文件的提示（因为即使用户上传了数据文件，缺少 exe 仍无法执行），告知用户需先联系管理员部署系统文件，**终止流程**。

---

### 步骤 3：启动 RPA 任务

前置检查全部通过后，使用 Shell 工具**后台启动**包装脚本：

```powershell
python "<本Skill所在目录>/scripts/run_rpa.py"
```

> **路径说明**：与步骤 1 相同，使用项目工作区的绝对路径拼接。例如：
> ```powershell
> python "D:\Python\Code\RPA-skills\.cursor\skills\shang_hai\scripts\run_rpa.py"
> ```

**执行策略：**

1. 使用 `block_until_ms: 0` 将命令放入后台运行
2. 脚本启动后会在 `C:\RPA\rpa_result.json` 写入 `status: "running"`
3. **不要轮询，不要等待**，立即向用户反馈：

> RPA 任务已成功启动，正在后台执行中，请勿操作浏览器。
>
> 任务可能需要较长时间，完成后结果会自动保存。
> 您可以随时问我「查看 RPA 执行结果」来获取最新状态。

4. Agent 的本次任务到此结束，**不再做任何后续操作**

---

### 步骤 4：查询执行结果（用户主动触发）

当用户询问 RPA 任务结果时（如「查看 RPA 执行结果」「任务完成了吗」等），执行查询脚本：

```powershell
python "<本Skill所在目录>/scripts/get_result.py"
```

**根据脚本输出的 JSON 和 exit code 判断：**

| exit code | status 字段 | 操作 |
|-----------|-------------|------|
| `1` | `running` | 告知用户「任务仍在执行中，请稍后再查询」，并展示 `started_at` |
| `1` | `no_task` | 告知用户「未找到任务记录，请先启动 RPA 任务」 |
| `0` | `finished` | 向用户展示完整执行报告 |
| `0` | `error` / `warning` | 向用户展示错误信息并建议排查 |

**结果 JSON 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `running` / `finished` / `error` / `warning` / `no_task` |
| `started_at` | string/null | 任务开始时间 |
| `finished_at` | string/null | 任务结束时间 |
| `exit_code` | int/null | exe 进程退出码 |
| `log_lines` | list/null | rpa.log 最后两行原始内容（可能为飞书卡片 JSON） |
| `card_summary` | string/null | 从 `log_lines` 中解析出的纯文本摘要，优先使用此字段展示结果 |
| `message` | string | 人类可读的结果描述 |

**任务完成时的反馈规则：**

按以下优先级决定展示内容：

**情况 A：`card_summary` 非空**（RPA 程序输出了结构化结果）

直接将 `card_summary` 的内容渲染给用户，同时附上时间信息：

> 开始时间：[started_at]　结束时间：[finished_at]
>
> ---
>
> [card_summary 内容，逐段展示，保留换行和 emoji]

**情况 B：`card_summary` 为空**（日志无结构化内容）

> **上海访护 RPA 执行完成**
>
> 开始时间：[started_at]
> 结束时间：[finished_at]
> 执行状态：[exit_code 为 0 则"成功"，否则"失败（exit code: N）"]
>
> 日志信息：
> ```
> [log_lines 内容]
> ```
>
> [如有异常，附加说明或建议]

---

## 依赖说明

前置检查脚本依赖 `DrissionPage` 库，执行前确保已安装：

```powershell
pip install DrissionPage
```

## 注意事项

- exe 执行期间**不要操作浏览器**，避免干扰 RPA 自动化流程
- 如果 exe 路径包含中文或空格，Shell 命令中务必用引号包裹路径
- 日志文件每次执行会覆盖或追加，读取时以最新内容为准
- Chrome 必须通过配置了调试参数的快捷方式启动，普通方式启动的 Chrome 无法被脚本检测到
