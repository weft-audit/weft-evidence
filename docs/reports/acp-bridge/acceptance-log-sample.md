# ACP 桥验收日志样本（脱敏）

以下为桥三次验收的原始输出摘录（会话编号与机器路径已隐去）：

```text
[INIT] authMethods=[] caps=mcpCapabilities,promptCapabilities,sessionCapabilities
[NEW] sessionId=<session-id>
[SUM] stopReason=end_turn elapsed=4.9s sessionId=<session-id> 用量=未知
[AUDIT] CANCEL 试验钩子 3000ms 触发
[AUDIT] CANCEL_OK stopReason=cancelled cancelToStop=3ms
[AUDIT] DENIED tool=<tool> 原因=白名单未含
[AUDIT] APPROVED tool=<tool> option=allow-once kind=allow_once
```

判读：主链路通（end_turn）；取消打断 3ms（≤10s 验收线）；权限双路径
（空名单=拒绝、白名单=放行）且每次决定审计留痕；三路日志分离，密钥扫描零误报。
