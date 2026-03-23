---
name: "kol-workflow"
description: "KOL达人投放管理工作流 - 从产品话题生成到达人建联发送的完整流程。当用户需要：生成产品话题关键词、搜索达人并爬取数据、评分筛选达人、提取联系方式、生成建联话术、发送邮件时调用此技能。"
---

# KOL Claw - 达人投放管理系统

一套完整的KOL达人投放工作流，从产品分析到达人建联全流程自动化。

## 决策树：选择你的下一步

```
用户需求是什么？
│
├─ 没有明确指定 → 默认执行全流程（步骤1→2→3→4→5→6）
│
├─ 我只需要某个步骤 → 执行对应步骤
│   ├─ 步骤1：生成话题关键词 → 询问产品信息，生成话题和关键词
│   ├─ 步骤2：搜索达人爬取数据 → 询问存储路径，搜索并保存达人数据
│   ├─ 步骤3：评分筛选达人 → 使用同一路径，进行评分分析
│   ├─ 步骤4：提取联系方式 → 使用同一路径，提取联系方式
│   ├─ 步骤5：生成建联话术 → 使用同一路径，生成话术
│   └─ 步骤6：发送邮件 → 使用同一路径，发送邮件
│
└─ 我不知道在哪一步 → 先查看数据文件状态，判断当前进度
```

**重要**：步骤2时 Agent 应询问用户存储路径（默认 `outputs/KOL达人评分最终报告.xlsx`），后续步骤使用同一路径。

---

## 步骤 1：生成产品话题关键词

根据产品特点，生成用于搜索达人的话题标签和关键词。

**执行方式**：
1. 询问用户目标产品是什么（名称、品类、卖点、目标受众等）
2. 基于产品信息生成相关话题标签和搜索关键词

**输出示例**：
```
话题：#skincare #beauty #glowingskin
关键词：skincare routine, beauty tips, glowing skin
```

**输出**：话题标签和搜索关键词列表，用于步骤2搜索达人

---

## 步骤 2：搜索达人并爬取数据

使用 TikHub API 搜索达人并获取视频数据，所有数据统一保存到最终报告文件。

**统一输出文件**：`outputs/KOL达人评分最终报告.xlsx`

### 2.1 搜索达人

```python
from scripts.search.tikhub_client import TikHubClient

client = TikHubClient()
# 搜索达人并保存到 Excel（询问用户存储路径）
users = client.search_tiktok_users(keyword=keyword, output_path=output_path)
```

### 2.2 爬取达人详细数据

```python
import pandas as pd

# 直接使用 2.1 返回的 users 数据
for idx, user in enumerate(users):
    sec_uid = user["sec_uid"]
    
    # 获取达人视频数据（最新3个 + 最早2个）
    videos = client.fetch_user_post(sec_uid=sec_uid, count=20)
    
    if len(videos) >= 10:
        # 提取最新3个 + 最早2个
        recent_3 = videos[:3]
        oldest_2 = videos[-2:]
        all_5 = recent_3 + oldest_2
        
        # 更新播放数据到 user 字典
        for i, video in enumerate(all_5, 1):
            stats = video.get("stats", {})
            user[f"播放{i}"] = stats.get("play_count", 0)
            user[f"点赞{i}"] = stats.get("digg_count", 0)
            user[f"评论{i}"] = stats.get("comment_count", 0)
            user[f"收藏{i}"] = stats.get("collect_count", 0)
        
        print(f"[{idx+1}/{len(users)}] {user['nickname']} - 已获取 {len(videos)} 个视频")

# 保存更新后的数据到 Excel
df = pd.DataFrame(users)
df.to_excel(output_path, index=False)
print(f"已保存所有达人数据到 {output_path}")
```

**说明**：Agent 应询问用户存储路径，默认为 `outputs/KOL达人评分最终报告.xlsx`

**输入**：
- 搜索关键词（步骤1生成）

**输出**：`outputs/KOL达人评分最终报告.xlsx`（包含达人基本信息、粉丝数、播放量、点赞、评论等）

---

## 步骤 3：评分筛选达人

对达人进行 8 维度加权评分，确定投放优先级和报价建议。

```python
from scripts.analyze.anaylze_kol_v2 import run_kol_analysis

# 读取并分析数据，询问用户存储路径
run_kol_analysis(excel_path=output_path)
```

**说明**：Agent 应使用步骤2的同一路径

**输出**：同一文件中新增评分相关列（总分、投放优先级、建议报价等）

### 评分维度

| 维度 | 最高分 | 判断条件 |
|------|--------|----------|
| 体量分 | +6 | 中粉爆款(5k-3w粉+播粉比>15) |
| 播粉比 | +1 | ≥3 |
| 稳定性 | +2 | 变异系数<30% |
| 爆款 | +2 | ≥2个极值视频 |
| 性价比 | +2 | CPM<8 |
| 趋势 | ±2 | 上升/下降趋势 |
| 内容匹配 | ±1 | 完全/部分/不匹配 |
| 互动率 | ±1 | ≥5%/≥2%/<1% |

### 优先级划分

| 优先级 | 总分 | 建议 |
|--------|------|------|
| 高 | ≥12分 | 强烈推荐投放 |
| 中 | 8-12分 | 可考虑投放 |
| 低 | <8分 | 暂不推荐 |

### 动态 CPM 定价

```
粉丝量级定价：
  < 5千粉    → CPM = 8
  5千-3万    → CPM = 15
  3万-10万   → CPM = 18
  > 10万     → CPM = 19.5

趋势溢价：上升趋势 ×1.1

报价计算：
  中位价 = 播放量 × CPM / 1000
  低价   = 中位价 × 0.75
  高价   = 中位价 × 1.25
```

---

## 步骤 4：提取联系方式

从达人签名中提取邮箱、Instagram、WhatsApp 等联系方式。

```python
from scripts.outreach.extract_email import extract_contact_with_ai

# 提取联系方式，使用同一路径
extract_contact_with_ai(excel_path=output_path)
```

**说明**：Agent 应使用前面步骤的同一路径

**输出**：同一文件中新增"联系方式"列

**说明**：使用 OpenAI GPT-4o-mini 智能识别联系方式

---

## 步骤 5：生成建联话术

根据达人粉丝量和播放数据，生成个性化建联话术。

```python
from scripts.outreach.generate_script import generate_script, batch_generate

# 单个达人
generate_script(kol_name="达人昵称", excel_path=output_path)

# 或批量生成（TOP3 未建联达人）
batch_generate(excel_path=output_path, top_n=3)
```

**说明**：Agent 应使用前面步骤的同一路径

**话术策略**：

| 达人类型 | 条件 | 话术风格 |
|----------|------|----------|
| 大达人 | ≥5万粉 | 正式商务型 |
| 中达人 | 5千-5万 | 询价型 |
| 小达人 | <5千 | 爆款突出型 |

**输出**：同一文件中新增"话术"列

---

## 步骤 6：发送邮件

通过 Playwright 自动化发送 Gmail 邮件。

```python
from scripts.outreach.playwright_gmail_sender import GmailAutoSender

sender = GmailAutoSender()

# 首次使用：登录 Gmail
sender.login()

# 发送邮件，使用同一路径
sender.send_from_excel(excel_path=output_path, delay=30)
```

**说明**：Agent 应使用前面步骤的同一路径

**参数**：
- `delay`：发送间隔（秒），建议 30 以上

---

## 常见陷阱

❌ **评分显示"数据不足"**
→ 确保每个达人至少有 3 个有效播放数据

❌ **CPM 报价不知道是否合理**
→ 计算 CPM = 报价 ÷ (平均播放 ÷ 1000)，CPM ≤ 15 为合理

❌ **Gmail 发送失败**
→ 先运行 `--login` 重新登录，确保 Playwright 浏览器已安装

❌ **邮箱提取不到**
→ 确认达人 signature 中确实包含联系方式

---

## 最佳实践

- 步骤1的话题关键词要精准，直接影响达人搜索质量
- 步骤2爬取数据时注意 API 调用频率，避免被限流
- 步骤3评分后优先处理"高"优先级达人
- 步骤5话术可根据品牌特点调整模板
- 步骤6发送前先测试登录是否成功

---

## 项目结构

```
kol-workflow/
├── scripts/
│   ├── search/
│   │   └── tikhub_client.py        # TikHub API：搜索达人、爬取数据
│   ├── analyze/
│   │   └── anaylze_kol_v2.py       # 8维度评分分析
│   ├── outreach/
│   │   ├── extract_email.py        # 提取联系方式
│   │   ├── generate_script.py      # 生成建联话术
│   │   └── playwright_gmail_sender.py  # Gmail发送
│   └── kol_workflow.py             # 工作流统一入口
└── outputs/
    └── KOL达人评分最终报告.xlsx     # 统一输出文件（包含所有数据）
```

---

## 前提条件

### 1. 安装依赖
```bash
cd kol-claw/kol-workflow
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件：
```
OPENAI_API_KEY=your_openai_api_key
TIK_HUB_API_KEY=your_tikhub_api_key
```
