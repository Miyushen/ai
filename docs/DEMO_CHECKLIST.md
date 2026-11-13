# InsightAgent 演示检查清单

## 演示前 10 分钟

1. 启动 Docker Desktop，在项目目录执行 `docker compose up -d`。
2. 执行 `docker compose exec api python scripts/check_demo_readiness.py`。
3. 确认所有检查均为 `PASS`，再打开 <http://localhost:8501>。
4. 从左侧历史任务打开一条已通过结果，确认报告、证据、执行过程和质量审查可见。
5. 主演示问题固定使用：`按渠道比较最近90天收入，并指出贡献最高和最低的渠道。`
6. 固定追问：`进一步计算最高与最低渠道的收入差额，以及该差额占最高渠道收入的比例。`

## 模型接口临时异常

不要反复点击“开始分析”。直接说明当前模型路由不可用，然后：

1. 从左侧“最近任务”打开已完成的渠道收入任务。
2. 展示生成 SQL、原始证据、8 节点执行轨迹和 Reviewer 结果。
3. 打开已保存的追问任务，展示父子任务关系和历史上下文提示。
4. 打开 `artifacts/eval-results.json`，展示已验证的真实基线；只有全量评测实际完成后，才称其为 15 题正式结果。
5. 如前端也不可用，使用 `docs/screenshots/` 中的三张截图和答辩 PPT。

历史结果保存在 PostgreSQL，与浏览器 Session 无关，因此模型接口异常不影响结果回放和报告导出。
