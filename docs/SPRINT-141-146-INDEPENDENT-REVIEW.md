# Sprint 141–146：独立验收流程

## 实现
- GET/POST `/api/v1/governance/tasks/{task_id}/reviews`: 验收记录查看/提交。
- GET `/api/v1/governance/tasks-acceptance-report`: 验收汇总统计。
- 通过/退回两种决策；通过必须已有整改证据。
- 若任务 owner 与验收用户一致，则拒绝验收，避免责任人自行验收。
- 验收记录写入 Record(category=task_review)并登记审计日志；继续使用既有记录表，不涉及新增迁移。
- 测试覆盖无证据、责任人自验收限制及通过流程。

## 注意事项
- 该工作包未改变任务的原始状态/关闭接口；验收记录和任务关闭仍是两个动作。
- 汇总报告读取最新记录时依赖 Record.created_at 排序，建议后续改用正式验收字段或事件表、SQL聚合与索引。
- 当前数据存储为元数据记录，不支持上传二进制文件。测试及CI执行结果尚待确认。
