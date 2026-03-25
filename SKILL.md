***

name: "kol-workflow"
description: "KOL达人投放管理工作流 - 从产品话题生成到达人建联发送的完整流程。当用户需要：生成产品话题关键词、搜索达人并爬取数据、评分筛选达人、提取联系方式、生成建联话术、发送邮件时调用此技能。"
------------------------------------------------------------------------------------------------------------

# KOL Claw - 达人投放管理系统

一套完整的KOL达人投放工作流，从产品分析到达人建联全流程自动化。

## 决策树：选择你的下一步

```
用户需求是什么？
│
├─ 没有明确指定 → 默认执行全流程（步骤0→1→2→3→4→5→6）
│   └─ 步骤0：检查环境变量，未配置时引导用户配置
│
├─ 我只需要某个步骤 → 执行对应步骤
│   ├─ 步骤1：生成话题关键词 → 使用环境变量 PRODUCT_INFO_FILE
│   ├─ 步骤2：搜索达人爬取数据 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤3：评分筛选达人 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤4：提取联系方式 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤5：生成建联话术 → 使用 DEFAULT_OUTPUT_PATH
│   └─ 步骤6：发送邮件 → 使用 DEFAULT_OUTPUT_PATH
│
└─ 我不知道在哪一步 → 先查看数据文件状态，判断当前进度
```

## 步骤 0：环境变量配置检查

执行全流程前，检查以下环境变量，未配置时询问用户并添加到 `.env` 文件：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DEFAULT_OUTPUT_PATH` | 输出文件路径 | `assets/outputs/KOL达人评分最终报告.xlsx` |
| `PRODUCT_INFO_FILE` | 产品信息文件路径 | `references/产品信息.md` |
| `SCRIPT_STRATEGY_FILE` | 话术策略文件路径 | `references/邀约话术.md` |
| `GMAIL_AUTH_STATE` | Gmail 登录状态文件路径 | `gmail_auth_state.json` |
| `TIK_HUB_API_KEY` | TikHub API 密钥 | 无（必需） |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 无（必需） |

***

## 步骤 1：生成产品话题关键词

根据产品特点，生成用于搜索达人的话题标签和关键词。

**执行方式**：

1. 尝试从环境变量 `PRODUCT_INFO_FILE` 读取产品信息文件
2. 如果文件存在，向用户确认产品信息是否需要修改；如果文件不存在，询问用户目标产品信息，以md格式保存到 `PRODUCT_INFO_FILE`
3. 根据产品信息生成相关话题标签和搜索关键词

**输出示例**：

```
话题：#skincare #beauty #glowingskin
关键词：skincare routine, beauty tips, glowing skin
```

**输出**：话题标签和搜索关键词列表，用于步骤2搜索达人

***

## 步骤 2：搜索达人并爬取数据

使用 TikHub API 搜索达人并获取视频数据，所有数据统一保存到最终报告文件。

**统一输出文件**：`DEFAULT_OUTPUT_PATH` 环境变量

### 2.1 搜索达人

```python
from scripts.search.tikhub_client import TikHubClient
import os

client = TikHubClient()
output_path = os.getenv("DEFAULT_OUTPUT_PATH", "assets/outputs/KOL达人评分最终报告.xlsx")
users = client.search_tiktok_users(keyword=keyword, output_path=output_path)
```

### 2.2 爬取达人详细数据

```python
for user in users:
    client.fetch_kol_play_data(sec_uid=user["sec_uid"], output_path=output_path)
```

**输入**：搜索关键词（步骤1生成）

**输出**：`DEFAULT_OUTPUT_PATH`（包含达人基本信息、粉丝数、播放量、点赞、评论等）

***

## 步骤 3：评分筛选达人

对达人进行 8 维度加权评分，确定投放优先级和报价建议。

```python
from scripts.analyze.anaylze_kol_v2 import run_kol_analysis
import os

output_path = os.getenv("DEFAULT_OUTPUT_PATH", "assets/outputs/KOL达人评分最终报告.xlsx")
run_kol_analysis(output_path)
```

**输出**：同一文件中新增评分相关列（总分、投放优先级、建议报价等）

***

## 步骤 4：提取联系方式

从达人签名中提取邮箱、Instagram、WhatsApp 等联系方式。

```python
from scripts.outreach.extract_email import extract_contact_with_ai
import os

excel_path = os.getenv("DEFAULT_OUTPUT_PATH", "assets/outputs/KOL达人评分最终报告.xlsx")
extract_contact_with_ai(excel_path)
```

**输出**：同一文件中新增"联系方式"列

**说明**：使用 LLM 智能识别联系方式

***

## 步骤 5：生成建联话术

根据达人粉丝量和播放数据，从话术策略文件读取话术模板，使用 LLM 生成个性化建联话术。

**执行方式**：
1. 从环境变量 `SCRIPT_STRATEGY_FILE` 读取话术策略文件
2. 让用户确认或修改话术策略
3. 根据达人数据使用 LLM 生成个性化话术

***

## 步骤 6：发送邮件

通过 Playwright 自动化发送 Gmail 邮件。

```python
from scripts.outreach.playwright_gmail_sender import GmailAutoSender
import os

auth_state_path = os.getenv("GMAIL_AUTH_STATE", "gmail_auth_state.json")
sender = GmailAutoSender(auth_state_path=auth_state_path)
sender.login()
sender.send_from_excel(delay=30)
```

**参数**：`delay`：发送间隔（秒），建议 30 以上

***

## 常见陷阱

❌ **评分显示"数据不足"**
→ 确保每个达人至少有 3 个有效播放数据

❌ **CPM 报价不知道是否合理**
→ 计算 CPM = 报价 ÷ (平均播放 ÷ 1000)，CPM ≤ 15 为合理

❌ **Gmail 发送失败**
→ 先运行 `--login` 重新登录，确保 Playwright 浏览器已安装

❌ **邮箱提取不到**
→ 确认达人 signature 中确实包含联系方式

***

## 最佳实践

- 步骤1的话题关键词要精准，直接影响达人搜索质量
- 步骤2爬取数据时注意 API 调用频率，避免被限流
- 步骤3评分后优先处理"高"优先级达人
- 步骤5话术可根据品牌特点调整模板
- 步骤6发送前先测试登录是否成功

***

## 项目结构

```
kol-workflow/
├── SKILL.md                    # 技能定义文件
├── scripts/                    # 可执行代码
│   ├── search/
│   │   └── tikhub_client.py    # TikHub API：搜索达人、爬取数据
│   ├── analyze/
│   │   └── anaylze_kol_v2.py  # 8维度评分分析
│   ├── outreach/
│   │   ├── extract_email.py           # 提取联系方式
│   │   ├── generate_script.py         # 生成建联话术
│   │   └── playwright_gmail_sender.py # Gmail发送
├── references/                # 文档资料
│   ├── 产品信息.md           # 产品信息
│   ├── 邀约话术.md          # 话术策略模板
│   └── docs/
│       └── anaylze_kol_v2流程说明.md
├── assets/                    # 模板资源
│   └── data/                 # 数据目录
└── requirements.txt
```

***

## 前提条件

### 1. 安装依赖

```bash
cd kol-claw/kol-workflow
pip install -r requirements.txt
playwright install chromium
```

