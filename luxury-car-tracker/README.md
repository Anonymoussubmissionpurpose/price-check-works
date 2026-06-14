# 🏎️ 豪华二手车 · 美国最低售价追踪

自动追踪 11 款豪华车在**美国二手车市场**（2025 款及以上）当前**最低的 5 个挂牌价**，
每日两次抓取，用不同颜色的柱状图同图对比，部署在 GitHub Pages 上，移动端自适应。

> **只追踪二手车（used market）**，不含新车。

## 追踪车型

保时捷 卡宴 · 阿斯顿马丁 DBX · 阿斯顿马丁 Vantage · 兰博基尼 Urus ·
奔驰 GLS 迈巴赫 · 奔驰 AMG GT · 奔驰 SL · 奔驰 G级 · 路虎 揽胜 · 宾利 添越 · 法拉利 罗马

---

## ⚠️ 先读这一段：关于数据源（很重要）

我对数据源做了实测和调研，结论如下：

**直接爬 CarGurus / Cars.com / AutoTrader 在 GitHub Actions 上不可靠。** 这些站点都用了
企业级反爬系统（DataDome / Cloudflare），它们会**直接封禁数据中心 IP**——而 GitHub Actions
跑在 Azure 数据中心 IP 段上，正是被秒封的对象。也就是说，一个"看起来能跑"的纯爬虫脚本，
在云端定时任务里大概率被挡掉、弹验证码或返回空数据。

**因此本项目默认使用 MarketCheck API 作为主数据源**，它正是你要的"信息更丰富的美国范围内车商"：

- 聚合**全美 53,000+ 家经销商网站**、约 **620 万条二手/认证二手在售车源**
- 返回干净的 JSON，**从任何 IP 都能稳定访问**（不受反爬影响）
- 自带年份 / 里程 / 车源地 / 价格统计等字段
- **免费档每月 500 次调用**

脚本逻辑：

- **设置了 `MARKETCHECK_API_KEY`** → 走 API（推荐，稳定）
- **没设置** → 退化为 Cars.com 尽力爬取（best-effort，云端常被挡，仅作兜底）

> 关于配额：11 款车 × 每天 2 次 × 30 天 ≈ **660 次/月**，略超免费档 500 次。
> 三种选择：① 改成每天 1 次（≈330 次，稳在免费额度内）；② 升级 MarketCheck 付费档
> （Basic 5,000 次/月）；③ 保持每天两次、月底约第 22 天后触达上限——脚本届时会保留上次成功的数据。

---

## 部署步骤

### 1. 创建仓库并上传

```
your-repo/
├── .github/workflows/scrape.yml
├── data/prices.json
├── index.html
├── scraper.py
├── requirements.txt
└── README.md
```

```bash
git init && git add . && git commit -m "init"
git remote add origin https://github.com/你的用户名/你的仓库.git
git push -u origin main
```

### 2. （推荐）配置 MarketCheck API Key

1. 到 [MarketCheck Universe](https://www.marketcheck.com/apis/) 注册，免费档即可拿到 API Key
2. 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. Name 填 `MARKETCHECK_API_KEY`，Value 粘贴你的 Key，保存

> 不配也能跑（走 Cars.com 兜底爬取），但云端成功率低，强烈建议配置。

### 3. 开启 GitHub Pages

仓库 → **Settings** → **Pages** → Source 选 `Deploy from a branch` → 分支 `main` / `/(root)` → Save。
稍等出现 `https://你的用户名.github.io/你的仓库/`，即为你的页面。

### 4. 手动触发首次抓取

仓库 → **Actions** → 选 **Scrape Used Car Prices** → **Run workflow**。
约 1–3 分钟（走 API）后刷新 Pages 页面即可看到数据。之后每天北京时间 **08:00 / 20:00** 自动更新。

---

## 数据真实性提醒：部分车型可能"无数据"

这是市场现实，不是程序 bug：**二手 + 2025 款及以上 + 超豪华**这个交集本身就很小。
比如法拉利 Roma、阿斯顿 Vantage、迈巴赫 GLS 这类车，几乎全新的"准新二手"全美在售量可能只有
个位数甚至为 0。届时页面会显示"—"，等有车源时自动补上。这反映的是真实库存，任何数据源都一样。

---

## 自定义

- **改更新时间**：编辑 `.github/workflows/scrape.yml` 的 `cron`
  （`0 0 * * *` = UTC 0 点 = 北京 8 点；`0 12 * * *` = 北京 20 点）。
- **改年份范围**：编辑 `scraper.py` 顶部的 `YEARS = "2025,2026,2027"`。
- **某车型名对不上**：MarketCheck 的车型命名偶有差异（如 `Maybach GLS` vs `Maybach GLS 600`），
  在 `scraper.py` 的 `CARS` 列表里调整对应 `model` 字段即可。

## 技术栈

GitHub Actions（定时）→ `scraper.py`（MarketCheck API / 兜底 Playwright）→ `data/prices.json`
（Git 提交）→ GitHub Pages（`index.html` + Chart.js 横向分组柱状图，移动端自适应）。

## 已验证

- ✅ Python 解析 / 排序 / 去重 / 缓存兜底逻辑（单元测试通过）
- ✅ 工作流 YAML 合法，API Key 缺省时自动切换兜底路径
- ✅ 前端无 JS 报错，桌面 / 390px / 360px 三档渲染正常，移动端无横向溢出，表格首列吸附可横滑

> 数据仅供参考，请以经销商实际报价为准；请遵守各数据源的使用条款。
