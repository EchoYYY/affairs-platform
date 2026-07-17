
# AFFAIRS — Recommended Improvements (Plain-Language Summary)


> **Bottom line: AFFAIRS is in good shape and does what it set out to do. This is a punch list of improvements — nothing here is a crisis. We suggest doing the short 'Now' list first (small fixes, high value), then 'Soon', and only tackling the 'Later' security/scale items once you decide how and where the tool will be hosted.**


## What the platform does today

AFFAIRS reads your library of medical-device regulatory documents, makes them searchable, uses AI to summarise each one (key requirements, obligations, risk), and adds live monitoring of regulators, an alerts feed, impact assessment against your product list, and predictive insights. It runs on a lightweight setup (a single database file) that is easy to operate.


## How to read this list

The improvements are grouped by urgency, not by difficulty. 'Now' items are small things that currently behave incorrectly. 'Soon' items make the tool more trustworthy and easier to live with. 'Later' items only matter once you grow the document library a lot, or open the tool up to more people over a network.


## Now — small fixes worth doing first


| Improvement | What it means for you |
|---|---|
| Refresh the AI model setting | The AI features point at an older model name. Update it so they keep working reliably, and consider a cheaper AI model for the high-volume parts (scoring, Q&A) to lower running cost. |
| Turn on (or remove) the hidden search page | A document search feature was fully built but has no button to reach it — the menu opens a different page instead. Either add it to the menu or remove the leftover, so nothing is half-finished. |
| Stop alerts over-triggering for some regions | The alert system currently treats the US, EU, UK and 'International' as always relevant, even if you don't operate there — which adds noise. Make it follow your configured markets. |
| Switch on the 'ignore low-value alerts' filter | A setting meant to hide unimportant updates was never actually applied, so every monitored item becomes an alert. Turning it on (or deciding a threshold) reduces clutter. |
| Stop the forecast page from crashing | If the AI call behind the predictive-insights page fails, the page errors out instead of showing a simple fallback like the other pages already do. |


## Soon — trust and everyday polish


| Improvement | What it means for you |
|---|---|
| Verify the assistant's citations | When the assistant answers a question and cites sources by number, nothing yet confirms those citations are real. A quick check makes the answers trustworthy. |
| Show helpful error messages | When something fails to load, pages currently go blank with no explanation. Friendly error messages make problems obvious instead of mysterious. |
| Make web-source monitoring fail loudly, not silently | The parts that read regulator websites can quietly stop working if those sites change their layout — looking like 'no news' rather than 'broken'. Add a visible health status per source. |
| Match the manual to reality | The documentation says the AI features work without an API key, but part of them stop entirely without one. Align the wording so expectations are correct. |
| Fix small accuracy and naming rough edges | A document-category filter can occasionally match the wrong category; two unrelated features confusingly share the name 'horizon'; and one screen duplicates a shared component. All minor, all worth tidying. |
| Add a basic automated test safety net | There are currently no automated tests. A small starter set means future changes are far less likely to break something quietly. |


## Later — only when you grow or expose the tool


| Improvement | What it means for you |
|---|---|
| Add security before exposing it | Today anyone who can reach the app can use it and download documents. That is fine on a single private machine. Before putting it on a shared network or the internet, add a login / access key and standard safeguards on file access. |
| Plan for a bigger document library | The current search approach is fast now but will slow down with a very large library. There is a clear upgrade path when you reach that point — this just flags it in advance. |
| Smooth out database upgrades and background jobs | As new features arrive, the database needs a tidy way to evolve, and background import jobs need a guard so two can't run into each other. Housekeeping for growth. |
| Optionally read scanned PDFs | Image-only (scanned) PDFs are currently skipped. If some of your important documents are scans, adding text recognition would bring them in. |


## What we suggest first

Start with the 'Now' list — it is a small amount of work with immediate payoff and low risk. Move to 'Soon' next. Hold the 'Later' security and scale items until you have decided how the tool will be hosted, because the right answer depends entirely on that decision.


# AFFAIRS —— 改进建议（通俗易懂版摘要）


> **结论：AFFAIRS 整体状况良好，已经实现了预定目标。以下是一份改进清单，其中没有任何紧急问题。我们建议先完成简短的“现在”清单（改动小、价值高），然后是“不久”清单；至于“以后”中涉及安全与扩展的事项，等您确定工具将如何以及在何处部署之后再着手。**


## 平台目前的功能

AFFAIRS 会读取您的医疗器械法规文档库，使其可被检索，并用 AI 对每份文档进行摘要（关键要求、义务、风险）；此外还提供对监管机构的实时监控、预警信息流、针对您产品清单的影响评估，以及预测性洞察。它运行在一个轻量化的架构上（单个数据库文件），便于维护。


## 如何阅读本清单

这些改进按紧急程度分组，而非按难度。“现在”类是目前行为不正确的小问题；“不久”类能让工具更可信、更易于使用；“以后”类只有在文档库大幅增长、或将工具通过网络开放给更多人使用时才需要关注。


## 现在 —— 值得优先处理的小修复


| 改进项 | 对您意味着什么 |
|---|---|
| 更新 AI 模型设置 | 各项 AI 功能目前指向一个较旧的模型名称。请更新它以保证功能稳定运行；同时可考虑对高频使用的部分（评分、问答）改用更经济的 AI 模型，以降低运行成本。 |
| 启用（或移除）隐藏的搜索页面 | 文档搜索功能已完整开发，但没有入口按钮 —— 菜单打开的是另一个页面。请将其加入菜单，或移除这段遗留代码，避免功能半成品状态。 |
| 避免部分地区的预警过度触发 | 预警系统目前把美国、欧盟、英国和“国际”一律视为相关，即使您并不在这些地区运营，从而增加了噪音。应改为遵循您所配置的市场。 |
| 启用“忽略低价值预警”的过滤 | 一个用于隐藏不重要更新的设置从未真正生效，导致每一条被监控的信息都变成预警。启用它（或设定一个阈值）可减少干扰。 |
| 防止预测页面崩溃 | 如果预测性洞察页面背后的 AI 调用失败，该页面会报错，而不像其他页面那样显示一个简单的兜底内容。 |


## 不久 —— 提升可信度与日常体验


| 改进项 | 对您意味着什么 |
|---|---|
| 核对助手给出的引用 | 当助手回答问题并按编号引用来源时，目前没有任何机制确认这些引用是真实存在的。加一道快速核对即可让答案更可信。 |
| 显示友好的错误提示 | 当某些内容加载失败时，页面目前会一片空白且没有任何说明。友好的错误提示能让问题一目了然，而不是让人摸不着头脑。 |
| 让网页来源监控“出错就报警”，而非默默失效 | 读取监管机构网站的部分，如果对方网站改版可能会悄无声息地停止工作 —— 表现为“没有新消息”而非“出故障了”。应为每个来源增加可见的健康状态。 |
| 让说明文档与实际情况一致 | 文档说 AI 功能无需 API 密钥即可使用，但其中一部分在没有密钥时会完全停止。请调整措辞以符合实际。 |
| 修正一些准确性与命名上的小瑕疵 | 一个文档类别过滤器偶尔会匹配到错误的类别；两个不相关的功能都叫“horizon（地平线/展望）”容易混淆；还有一个页面重复实现了公共组件。都是小问题，但值得整理。 |
| 建立基础的自动化测试保障 | 目前没有任何自动化测试。一套小型的起步测试能大幅降低未来改动悄悄破坏功能的风险。 |


## 以后 —— 仅在扩展或对外开放时才需要


| 改进项 | 对您意味着什么 |
|---|---|
| 对外开放前先加上安全措施 | 目前只要能访问到该应用的人都可以使用它并下载文档。在单台私人机器上这没问题；但在放到共享网络或互联网之前，应加上登录 / 访问密钥，并对文件访问加上标准防护。 |
| 为更大的文档库做准备 | 当前的搜索方式现在很快，但文档库非常庞大时会变慢。届时有清晰的升级路径 —— 这里只是提前提醒。 |
| 优化数据库升级与后台任务 | 随着新功能加入，数据库需要一种整洁的方式来演进，后台导入任务也需要加锁以防两个任务相互冲突。属于面向增长的日常维护。 |
| 可选：识别扫描版 PDF | 目前会跳过纯图像（扫描版）的 PDF。如果您的一些重要文档是扫描件，增加文字识别即可将它们纳入。 |


## 我们的优先建议

从“现在”清单开始 —— 工作量小、见效快、风险低。接着处理“不久”清单。至于“以后”中的安全与扩展事项，请等到确定工具的部署方式之后再动手，因为正确的做法完全取决于这个决定。
