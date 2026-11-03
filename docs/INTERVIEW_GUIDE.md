# InsightAgent 面试讲解稿

## 一句话介绍

InsightAgent 是一个基于 LangGraph 的自主数据分析智能体。用户输入业务问题后，它会规划分析步骤、读取数据库 Schema、生成只读 SQL、执行查询、基于证据生成结论，并由独立 Reviewer 检查结果是否回答了原问题以及结论是否有数据支撑。

## 两分钟项目介绍

我做这个项目是因为通用聊天模型虽然能生成 SQL，但在真实数据分析场景里有三个问题：生成过程不可观察、错误结果容易被直接包装成结论、数据库安全不能只依靠提示词。

因此我用 LangGraph 把任务拆成确定的状态图：Planner 负责理解问题，Schema 节点提供真实表结构，SQL Generator 生成查询，SQL Guard 做 AST 校验，Executor 在只读事务中执行，Analyst 只根据返回行生成结论，Reviewer 再独立复核。如果 SQL 无效、执行失败、查询没有证据行或 Reviewer 拒绝，图会在限定次数内自动修复。

安全方面，我做了多层防护：SQLGlot 解析单条语句、禁止 DDL/DML、限制可访问表、强制行数上限、设置语句超时，并在只读事务里执行和回滚。这样即使模型提示词失效，也不能直接修改数据库。

项目用 FastAPI 提供接口，用 Streamlit 展示生成 SQL、原始证据、执行轨迹和 Reviewer 结果。评测集包含 5 个固定业务问题，当前本地基线为 5/5 请求成功、Reviewer 批准率 100%、关键词召回率 100%，中位端到端延迟 38.27 秒。

## 五分钟演示流程

1. 打开 `http://localhost:8501`，先展示 API、数据库、密钥和模型状态。
2. 输入：`过去30天哪个地区的销售额下降最明显？请与之前30天比较。`
3. 运行后先看四个指标：SQL 尝试次数、证据行数、Reviewer 状态和置信度。
4. 在 Report 页说明结论只来自查询结果，不允许补充模型常识。
5. 在 Evidence 页展示生成 SQL和原始数据，强调结果可审计。
6. 在 Execution trace 页展示 LangGraph 节点顺序和失败修复路径。
7. 在 Reviewer 页展示独立复核意见。
8. 最后打开 `artifacts/eval-results.json`，说明不仅演示单个成功案例，也维护了固定评测集。

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

当前评测记录 HTTP 成功率、Reviewer 批准率、关键词召回、SQL 尝试次数和端到端延迟。下一步会加入结果集签名、人工标注答案、SQL 语义正确率、token 成本和分节点延迟。

### 为什么当前评测不能证明生产准确率？

目前只有 5 个固定问题，主要验证端到端链路和回归稳定性。它是演示基线，不是统计意义上的生产基准。README 对这一限制做了明确说明。

### 如果数据库有几百张表怎么办？

不会把全部 Schema 一次塞进上下文。生产版会先做表级检索和业务语义层，根据问题召回相关表与指标定义，再把精简 Schema 交给 SQL Generator。

### 如何支持多租户？

为每个租户绑定独立只读数据库角色和连接池，在状态中传递租户上下文，Schema 检索和执行层都按租户隔离，并在 API 层加入认证、配额和审计日志。

### 当前最大的不足是什么？

- 评测集规模较小，缺少结果集级的黄金答案。
- 仍使用单一模型处理多个角色，成本与延迟还有优化空间。
- 尚未接入持久化 Checkpoint、任务队列和可观测平台。
- 演示数据库权限仍是开发配置，生产环境应使用最小权限角色。

## 可继续扩展的方向

1. 使用 LangGraph Checkpointer 支持中断恢复和历史回放。
2. 增加 Schema 检索与业务指标语义层。
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
