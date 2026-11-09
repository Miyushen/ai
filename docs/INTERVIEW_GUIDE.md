# InsightAgent 面试讲解稿

## 一句话介绍

InsightAgent 是一个基于 LangGraph 的自主数据分析智能体。用户输入业务问题后，它会规划分析步骤、读取数据库 Schema、生成只读 SQL、执行查询、基于证据生成结论，并由独立 Reviewer 检查结果是否回答了原问题以及结论是否有数据支撑。

## 两分钟项目介绍

我做这个项目是因为通用聊天模型虽然能生成 SQL，但在真实数据分析场景里有三个问题：生成过程不可观察、错误结果容易被直接包装成结论、数据库安全不能只依靠提示词。

因此我用 LangGraph 把任务拆成确定的状态图：Planner 负责理解问题，Schema 节点提供真实表结构，SQL Generator 生成查询，SQL Guard 做 AST 校验，Executor 在只读事务中执行，Analyst 只根据返回行生成结论，Reviewer 再独立复核。如果 SQL 无效、执行失败、查询没有证据行或 Reviewer 拒绝，图会在限定次数内自动修复。

安全方面，我做了多层防护：SQLGlot 解析单条语句、禁止 DDL/DML、限制可访问表、强制行数上限、设置语句超时，并在只读事务里执行和回滚。这样即使模型提示词失效，也不能直接修改数据库。

项目用 FastAPI 提供接口，用 Streamlit 展示生成 SQL、原始证据、执行轨迹和 Reviewer 结果。分析任务会持久化到 PostgreSQL，刷新页面或重启前端后仍可回放；用户还能基于任意历史报告继续追问，系统会把上一轮问题、报告、SQL 和有限证据行作为受控上下文交给下一次 LangGraph 工作流。

我还为五个固定业务问题编写了只读 Oracle SQL，用数据库黄金结果检查关键实体和数值。最新本地评测中 5/5 请求成功、Reviewer 通过率 100%、黄金结果得分 100%，中位端到端延迟 70.30 秒。这个基线规模不大，但比只检查报告关键词更能证明结论与真实查询结果一致。

## 五分钟演示流程

界面参考：[分析报告](screenshots/insight-agent-demo.png) · [执行轨迹](screenshots/insight-agent-trace.png) · [手机布局](screenshots/insight-agent-mobile.png)

1. 打开 `http://localhost:8501`，先展示 API、数据库、密钥和模型状态。
2. 输入：`过去30天哪个地区的销售额下降最明显？请与之前30天比较。`
3. 运行后先看五个指标：SQL 尝试次数、证据行数、Reviewer 状态、置信度和端到端耗时。
4. 在 Report 页说明结论只来自查询结果，不允许补充模型常识。
5. 在 Evidence 页展示生成 SQL和原始数据，强调结果可审计。
6. 在 Execution trace 页展示 LangGraph 节点顺序、节点耗时和失败修复路径，说明如何定位模型调用或数据库执行瓶颈。
7. 在 Reviewer 页展示独立复核意见。
8. 刷新页面并从“最近任务”重新打开结果，证明历史记录保存在 PostgreSQL，而不是只存在浏览器会话。
9. 点击“基于本次结果继续追问”，演示父子任务上下文和二次分析。
10. 最后打开 `artifacts/eval-results.json`，展示固定评测集、黄金结果得分和各节点平均耗时。

## 架构讲解重点

```text
Question
  -> Planner
  -> Schema Retrieval
  -> SQL Generator
  -> AST Guard
  -> Read-only Executor
  -> Evidence Analyst
  -> Independent Reviewer
  -> Report
```

Planner、SQL Generator、Analyst、Reviewer 和 Reporter 是模型节点；Schema、SQL Guard 和 Executor 是确定性代码节点。系统把适合模型判断的工作交给模型，把权限、安全和数据执行留在代码层。

## 关键技术取舍

### 为什么用 LangGraph

- 数据分析不是一次模型调用，而是有条件分支和重试的工作流。
- 状态图比自由对话式多 Agent 更容易追踪、测试和限制成本。
- 每个节点输入输出明确，出现错误时能定位是生成、校验、执行还是复核阶段。

### 为什么不是只做 Text-to-SQL

Text-to-SQL 只解决查询生成，没有解决业务问题拆解、证据分析、结论复核和可观察性。InsightAgent 把 SQL 当作工具调用的一部分，而不是最终产品。

### 为什么 Reviewer 不能作为唯一安全层

Reviewer 本身仍是模型，也可能误判。因此项目先用确定性规则拦截空结果、危险 SQL、未知表和超量结果，Reviewer 只负责语义层面的证据一致性检查。

### 为什么限制重试次数

无限自我修复会造成成本和延迟不可控。项目分别限制 SQL 业务修复次数与模型网络重试次数，并且只对连接错误和 5xx 做传输重试，4xx 和业务校验错误不会被盲目重试。

## 常见面试追问

### 如何防止模型执行 DELETE 或 DROP？

提示词不是安全边界。SQL 会经过 SQLGlot AST 解析，只允许单条 SELECT；代码还检查访问表白名单、追加或收紧 LIMIT，并在 PostgreSQL 只读事务中执行。

### 如何减少幻觉？

Schema 来自数据库实时内省；Analyst 只收到 SQL、列名和有限数量的真实行；所有数字必须能在返回行中找到；空结果会进入修复循环；Reviewer 会检查结论是否超出证据。

### 如何评估 Agent？

当前评测记录 HTTP 成功率、Reviewer 批准率、关键词召回、SQL 尝试次数和端到端延迟；单次运行还会记录每个 LangGraph 节点的耗时。下一步会加入结果集签名、人工标注答案、SQL 语义正确率和 token 成本。

### 为什么当前评测不能证明生产准确率？

目前只有 5 个固定问题，主要验证端到端链路和回归稳定性。它是演示基线，不是统计意义上的生产基准。README 对这一限制做了明确说明。

### 如果数据库有几百张表怎么办？

不会把全部 Schema 一次塞进上下文。生产版会先做表级检索和业务语义层，根据问题召回相关表与指标定义，再把精简 Schema 交给 SQL Generator。

### 如何支持多租户？

为每个租户绑定独立只读数据库角色和连接池，在状态中传递租户上下文，Schema 检索和执行层都按租户隔离，并在 API 层加入认证、配额和审计日志。

### 连续追问如何避免上下文无限增长？

系统不会把完整对话历史直接塞回模型。每次追问只读取直接父任务，并传入上一轮问题、报告、SQL、列名和最多 30 行证据。这样既保留业务上下文，也限制 token、延迟和提示注入面。

### 历史任务为什么自己建表，而不是只用浏览器 Session？

浏览器 Session 刷新后会丢失，也无法审计失败任务。项目把运行状态、模型、耗时、完整结果和父任务 ID 持久化到 PostgreSQL，因此可以回放、追踪任务链并分析失败率。

### 当前最大的不足是什么？

- 评测集目前只有 5 个固定问题，业务场景和 SQL 形态覆盖仍然有限。
- 仍使用单一模型处理多个角色，成本与延迟还有优化空间。
- 已实现任务结果和父子关系持久化，但节点级 LangGraph Checkpoint 尚未落库，运行中断后仍不能从具体节点恢复。
- 演示数据库权限仍是开发配置，生产环境应使用最小权限角色。

## 可继续扩展的方向

1. 使用 LangGraph Checkpointer 支持从具体节点中断恢复；当前历史回放保存的是完整任务结果。
2. 扩展业务指标语义层，并按问题动态检索相关 Schema。
3. 接入 LangSmith 或 OpenTelemetry，记录分节点延迟、token 和错误率。
4. 增加人工审批节点，用于高风险查询或对外报告。
5. 使用 Celery、RQ 或任务队列支持长任务和并发限制。
6. 将评测升级为 SQL 结果签名、对抗问题和回归阈值检查。

## 简历描述参考

基于 LangGraph、OpenAI 兼容 API、FastAPI 和 PostgreSQL 构建自主数据分析 Agent，实现问题规划、Schema 感知 Text-to-SQL、SQL AST 安全校验、只读执行、证据分析与独立 Reviewer 修复闭环；设计 5 类业务评测集并实现成功率、Reviewer 通过率、召回率与延迟统计，本地基线达到 5/5 端到端成功。

## 演示前检查

```powershell
docker compose up -d
docker compose ps
docker compose exec api pytest -q
docker compose exec api python scripts/run_evals.py
```

演示期间需要保持 Docker Desktop 和 CC Switch 运行。不要展示 `.env`，也不要在录屏或截图中暴露 API 密钥。
