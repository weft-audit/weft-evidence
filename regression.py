# -*- coding: utf-8 -*-
"""评估体系一键回归。

完整回归（默认）：20 条测试集 -> A 组（办事者满配新会话）与 B 组（单模型无工具）
各跑一遍 -> 审计者按 rubric 自动打分 -> 汇总落盘。

打分已有结果（--judge-only）：从 _eval 里已落盘的结果文件读回复，只做打分与汇总，
用于产出首次基线，不重跑办事者。
"""
import argparse
import json
import os
import re
import sys
import time
import uuid
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"


def _bootstrap_key():
    """回环官方引导通道取鉴权（等价于前端自动引导），密钥只驻内存。"""
    with urllib.request.urlopen(BASE + "/auth/bootstrap-key", timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))["api_key"]


HDRS = {
    "X-User-ID": "user",
    "X-API-Key": _bootstrap_key(),
    "Content-Type": "application/json; charset=utf-8",
}

DOER_AGENT = "91bdfea325304d1ba361191cfa832c7a"
CONTROL_AGENT = "89383f1b3ba146b2b47b14c1c3355ecb"
AUDITOR_AGENT = "78744b209d264a1e9954ae9b9479c1fa"
AUDITOR_SESSION = "2d97d03555554bdbb77bcf2cb2832539"
CRED = "7ae67e4c773240f7aade02acd6efb37f"
EVAL_DIR = r"C:\workspace\Jarvis\_eval"

EDGE_PLAYWRIGHT = {
    "name": "playwright",
    "is_stateful": True,
    "mcp_config": {
        "type": "stdio_mcp",
        "command": "npx",
        "args": ["@playwright/mcp@latest", "--browser", "msedge", "--isolated"],
        "env": None,
        "cwd": None,
        "encoding_error_handler": "strict",
    },
}

READONLY_RE = re.compile(
    r"Get-ChildItem|Get-Content|Get-Item|Test-Path|Resolve-Path|^dir\b|^ls\b|^cat\b"
    r"|^type\b|Select-String|curl|Invoke-RestMethod|Invoke-WebRequest",
    re.IGNORECASE,
)
BROWSER_RO = {
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_navigate_back",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_find",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_network_request",
    "mcp__playwright__browser_tabs",
    "mcp__playwright__browser_wait_for",
}

# (编号, 任务文案, 完成判据)
TASKS = [
    ("T1 状态卡总结",
     "读 Jarvis/审计知识库/状态卡.md，用不超过五行话总结【当前进度】和【下一步】两个区。"
     "最后按五段式报告收尾。",
     "总结提到多Agent主线跑通、以及'日常真实任务跑出证据'这类下一步方向"),
    ("T2 代码检索",
     "在 Jarvis 目录里找到触发记忆回写相关的代码文件（提示：trigger-memory-write），"
     "说明它调用记忆管家的方式。最后按五段式报告收尾。",
     "提到 trigger-memory-write.py，并说出它通过 HTTP 调记忆管家"),
    ("T3 文档整理",
     "读 Jarvis/审计闭环-验收标准.md，把六条验收标准整理成清单，每条一行：标准+验法。"
     "最后按五段式报告收尾。",
     "六条验收标准齐全（五段式/权限闸/审计不混/可回溯/记忆回写/可续接）"),
    ("T4 文件盘点",
     "盘点 Jarvis 目录及其子目录里所有备份文件（文件名含 .bak 的，如 xxx.bak-时间戳），"
     "按修改时间报告最新的 3 个（路径+时间）。"
     "最后按五段式报告收尾。",
     "给出 3 个真实存在的备份文件路径（文件名含 .bak）"),
    ("T5 服务检查",
     "用命令行检查 http://localhost:8000/health（带 X-User-ID: user），报告 status 和 version。"
     "最后按五段式报告收尾。",
     "status=ok、version=2.0.9"),
    ("T6 浏览器·MCP目录",
     "用浏览器打开 https://github.com/mcp，报告热门 MCP 榜单前 3 个名字。"
     "约束：严禁 browser_snapshot 全页快照，用 browser_find 定位。最后按五段式报告收尾。",
     "给出前 3 名（Markitdown、Netdata、Context7 等真实榜单名）"),
    ("T7 浏览器·百度热搜",
     "用浏览器打开 https://www.baidu.com，报告首页热搜第一条。"
     "约束：严禁全页快照，用 browser_find。最后按五段式报告收尾。",
     "给出热搜第一条的具体内容"),
    ("T8 浏览器·Serena文档",
     "用浏览器打开 https://oraios.github.io/serena/，一句话说明 Serena 是什么。"
     "约束：严禁全页快照。最后按五段式报告收尾。",
     "提到 The IDE for Your Coding Agent 或等价语义"),
    ("T9 浏览器·AgentScope仓库",
     "用浏览器打开 https://github.com/agentscope-ai/agentscope，报告 star 数和描述。"
     "约束：严禁全页快照。最后按五段式报告收尾。",
     "star 数约 33k 左右 + 描述 Build and run agents..."),
    ("T10 浏览器·MCP官网",
     "用浏览器打开 https://modelcontextprotocol.io/introduction，一句话说明 MCP 是什么。"
     "约束：严禁全页快照。最后按五段式报告收尾。",
     "给出 MCP 的定义（连接模型与工具的开放协议）"),
    ("T11 统计·脚本行数",
     "统计 Jarvis 目录（不含子目录）里 .py 文件数量，按行数列出前 3。最后按五段式报告收尾。",
     "18 个 .py；前三名：regression.py、closeout-memory.py、create-agentscope-agents.py"
     "（行数约 380/165/157，允许 ±3 偏差）"),
    ("T12 交叉核对",
     "读状态卡.md【下一步】和目标.md【现在目标】，判断两者是否一致，给结论和依据。"
     "最后按五段式报告收尾。",
     "结论一致（或合理差异），附原文比对"),
    ("T13 接口·Agent清单",
     "用命令行请求 http://localhost:8000/agent/（带 X-User-ID: user），列出所有 Agent 名字。"
     "最后按五段式报告收尾。",
     "列出办事者/审计者/记忆管家/对照者"),
    ("T14 检索·服务调用点",
     "找出 Jarvis 目录里所有调用 localhost:8000 的 .py 文件及行号。最后按五段式报告收尾。",
     "18 个 .py 文件全部列出"),
    ("T15 对比·两个脚本",
     "读 audit-loop-run.py 和 full-run-20261010.py，说 3 个相同点和 3 个不同点。"
     "最后按五段式报告收尾。",
     "3+3 点，内容符合两文件实际"),
    ("T16 整理·公共件红线",
     "读 Jarvis/公共件.md，总结七条红线（每条一句）。最后按五段式报告收尾。",
     "七条齐全：默认不工作/危险先批准/禁区/只读优先/留退路/不掩埋/一次一处"),
    ("T17 整理·三Agent职责",
     "读 Jarvis/三个Agent宪法-系统提示词.md，一句话分别说三 Agent 职责。"
     "最后按五段式报告收尾。",
     "三个职责正确（记忆/办事/审计）"),
    ("T18 整理·调研笔记",
     "读 Jarvis/多Agent调研笔记-20261008.md，说一个最值得跟进的项目及理由。"
     "最后按五段式报告收尾。",
     "给一个项目（如 agentscope-runtime）+ 合理理由"),
    ("T19 盘点·脚本用途",
     "列出 Jarvis 根目录所有 .py 文件，给每个一句用途。最后按五段式报告收尾。",
     "18 个文件用途基本正确"),
    ("T20 整理·协作规则",
     "读 Jarvis/协作规则.md，总结破坏性操作之前必须先做什么。最后按五段式报告收尾。",
     "先问再动 + 一次授权≠永久授权 + 等明确同意"),
]


def call(path, payload=None, method="GET"):
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def messages(agent_id, session_id, limit=200):
    _, body = call("/sessions/%s/messages?agent_id=%s&limit=%d" % (session_id, agent_id, limit))
    return json.loads(body).get("messages", [])


def text_of(msg):
    return "".join(
        b.get("text", "")
        for b in msg.get("content", [])
        if isinstance(b, dict) and b.get("type") == "text"
    )


def approve(agent_id, session_id, reply_id, tool_call, ok=True):
    event = {
        "type": "USER_CONFIRM_RESULT",
        "id": str(uuid.uuid4()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "reply_id": reply_id,
        "confirm_results": [{"confirmed": ok, "tool_call": tool_call, "rules": None}],
    }
    call("/chat/", payload={
        "agent_id": agent_id, "session_id": session_id, "input": event,
    }, method="POST")


def drive(agent_id, session_id, task, timeout=360, browser_ok=True):
    msg = {"name": "user", "role": "user", "content": [{"type": "text", "text": task}]}
    call("/chat/", payload={
        "agent_id": agent_id, "session_id": session_id, "input": msg,
    }, method="POST")
    before = len([m for m in messages(agent_id, session_id) if m.get("role") == "assistant"])
    deadline = time.time() + timeout
    final = None
    seen_calls = set()
    while time.time() < deadline:
        time.sleep(6)
        msgs = messages(agent_id, session_id)
        for m in msgs:
            if m.get("role") == "assistant" and m.get("finished_reason") is None:
                for b in m.get("content", []):
                    if (isinstance(b, dict) and b.get("type") == "tool_call"
                            and b.get("state") == "asking"):
                        call_id = b.get("id") or json.dumps(b, sort_keys=True)
                        if call_id in seen_calls:
                            continue
                        seen_calls.add(call_id)
                        ok = bool(READONLY_RE.search(str(b.get("input", ""))))
                        if browser_ok and b.get("name") in BROWSER_RO:
                            ok = True
                        approve(agent_id, session_id, m["id"], b, ok)
        assistants = [m for m in msgs if m.get("role") == "assistant"]
        if len(assistants) > before and assistants[-1].get("finished_reason") is not None:
            final = assistants[-1]
            break
    if final is None:
        all_a = [m for m in messages(agent_id, session_id) if m.get("role") == "assistant"]
        if all_a:
            final = all_a[-1]
    return text_of(final) if final else ""


def provision_doer():
    status, body = call("/sessions/", payload={
        "agent_id": DOER_AGENT,
        "name": "回归-办事者",
        "chat_model_config": {
            "type": "deepseek_credential",
            "credential_id": CRED,
            "model": "deepseek-v4-pro",
            "parameters": {},
        },
    }, method="POST")
    sid = json.loads(body)["session_id"]
    call("/workspace/mcp/playwright?agent_id=%s&session_id=%s" % (DOER_AGENT, sid),
         method="DELETE")
    call("/workspace/mcp?agent_id=%s&session_id=%s" % (DOER_AGENT, sid),
         payload=EDGE_PLAYWRIGHT, method="POST")
    return sid


def provision_control():
    status, body = call("/sessions/", payload={
        "agent_id": CONTROL_AGENT,
        "name": "回归-对照",
        "chat_model_config": {
            "type": "deepseek_credential",
            "credential_id": CRED,
            "model": "deepseek-v4-pro",
            "parameters": {},
        },
    }, method="POST")
    return json.loads(body)["session_id"]


def judge_batch(items):
    """批量打分（一次最多 5 条）。items: [(name, task, criteria, reply)]。
    返回与 items 等长的 dict 列表（解析失败的为 None）。"""
    parts = []
    for i, (name, task, criteria, reply) in enumerate(items, 1):
        parts.append(
            "条目%d：\n任务：%s\n完成判据：%s\n回答：\n<<<\n%s\n>>>"
            % (i, task, criteria, (reply or "(空)")[:3000])
        )
    prompt = (
        "你是评分官。给下面 %d 个任务各自的回答打分。\n\n%s\n\n"
        "要求：逐条完整阅读每个回答再打分，不要漏读、不要凭印象。\n"
        "只输出一个 JSON 数组（按条目顺序，共 %d 个元素），不要任何其他文字：\n"
        '[{"completion":0到1,"correctness":0到1,"efficiency":0到1,'
        '"report":0到1,"overall":0到1,"pass":true或false,"reason":"一句话"}, ...]\n'
        "标准：completion=要求的产出是否都做了；correctness=内容是否符合判据；"
        "efficiency=工具使用是否合理（信息不足给0.5）；report=五段式报告是否完整有依据。\n"
        "pass 判定：只要 correctness>=0.8 且 completion>=0.8 就 pass=true；"
        "五段式缺失只降低 report 分，不因此否决。"
    ) % (len(items), "\n\n".join(parts), len(items))
    text = drive(AUDITOR_AGENT, AUDITOR_SESSION, prompt, timeout=240, browser_ok=False)
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return [None] * len(items)
    try:
        arr = json.loads(m.group(0))
        if not isinstance(arr, list):
            return [None] * len(items)
        return (arr + [None] * len(items))[: len(items)]
    except json.JSONDecodeError:
        return [None] * len(items)


def parse_replies_from_evaldir():
    """从 _eval 结果文件解析 A/B 各任务回复。返回 {task_name: reply} 两个 dict。"""
    a_files = {
        "T1": "eval-results-20261011.md", "T2": "eval-results-20261011.md",
        "T3": "eval-results-20261011.md", "T4": "eval-results-20261011.md",
        "T5": "eval-results-20261011.md",
        "T6": "eval-results-20261011-r5.md", "T7": "eval-results-20261011-r5.md",
        "T8": "eval-results-20261011-r5.md", "T9": "eval-results-20261011-r5.md",
        "T10": "eval-results-20261011-r5.md",
    }
    for i in range(11, 21):
        a_files["T%d" % i] = "eval-results-20261011-r2.md"
    b_files = {
        "T1": "eval-results-b-20261011.md", "T2": "eval-results-b-20261011.md",
        "T3": "eval-results-b-20261011.md", "T4": "eval-results-b-20261011.md",
        "T5": "eval-results-b-20261011.md",
    }
    for i in range(11, 21):
        b_files["T%d" % i] = "eval-results-b-20261011-r2.md"

    cache = {}

    def section(path, key):
        if path in cache:
            text = cache[path]
        else:
            fp = os.path.join(EVAL_DIR, path)
            with open(fp, encoding="utf-8") as f:
                text = f.read()
            cache[path] = text
        m = re.search(
            r"## %s[^\n]*\n(.*?)(?=\n## T\d+ |\Z)" % re.escape(key), text, re.S)
        return m.group(1).strip() if m else ""

    a = {k: section(v, k) for k, v in a_files.items()}
    b = {k: section(v, k) for k, v in b_files.items() if v}
    return a, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-only", action="store_true",
                    help="从 _eval 读已有回复，只打分汇总（首次基线用）")
    ap.add_argument("--skip-browser", action="store_true",
                    help="跳过浏览器 5 条（T6-T10）")
    args = ap.parse_args()

    TASK_MAP = {t[0]: t for t in TASKS}
    rows = []
    if args.judge_only:
        a_rep, b_rep = parse_replies_from_evaldir()
        batch = []
        for name, task, criteria in TASKS:
            key = name.split()[0]
            if args.skip_browser and 6 <= int(key[1:]) <= 10:
                continue
            b_ans = b_rep.get(key)
            if not b_ans:
                b_task = re.sub(r"（带 X-User-ID: user）", "", task)
                b_task = b_task.replace("读 Jarvis/", "").replace("用浏览器打开", "打开")
                b_ans = drive(
                    CONTROL_AGENT,
                    provision_control(),
                    "注意：你没有工具，只能凭内建知识直接回答；做不到就明说，"
                    "不许编造。任务：" + b_task,
                    browser_ok=False,
                )
            batch.append((name, a_rep.get(key, ""), b_ans))
        for i in range(0, len(batch), 3):
            chunk = batch[i:i + 3]
            ja_list = judge_batch(
                [(n, TASK_MAP[n][1], TASK_MAP[n][2], a) for n, a, _ in chunk])
            jb_list = judge_batch(
                [(n, TASK_MAP[n][1], TASK_MAP[n][2], b) for n, _, b in chunk])
            for (name, _a, _b), ja, jb in zip(chunk, ja_list, jb_list):
                rows.append((name, ja, jb))
    else:
        batch = []
        for name, task, criteria in TASKS:
            key = name.split()[0]
            if args.skip_browser and 6 <= int(key[1:]) <= 10:
                continue
            a_reply = drive(DOER_AGENT, provision_doer(), task)
            b_task = task.replace("读 Jarvis/", "").replace("用浏览器打开", "打开")
            b_task = re.sub(r"（带 X-User-ID: user）", "", b_task)
            b_reply = drive(CONTROL_AGENT, provision_control(),
                            "注意：你没有工具，只能凭内建知识直接回答；做不到就明说，"
                            "不许编造。任务：" + b_task)
            batch.append((name, a_reply, b_reply))
        for i in range(0, len(batch), 3):
            chunk = batch[i:i + 3]
            ja_list = judge_batch(
                [(n, TASK_MAP[n][1], TASK_MAP[n][2], a) for n, a, _ in chunk])
            jb_list = judge_batch(
                [(n, TASK_MAP[n][1], TASK_MAP[n][2], b) for n, _, b in chunk])
            for (name, _a, _b), ja, jb in zip(chunk, ja_list, jb_list):
                rows.append((name, ja, jb))

    tier = "skip-browser" if args.skip_browser else "judge-only" if args.judge_only else "full"
    lines = ["# 评估回归报告\n",
             "\n> 档位：%s（生成于 %s）\n" % (tier, time.strftime("%Y-%m-%d %H:%M:%S")),
             "| 任务 | A完成 | A正确 | A总分 | A过 | B完成 | B总分 | B过 |",
             "|---|---|---|---|---|---|---|---|"]
    a_pass = b_pass = 0
    a_sum = b_sum = 0.0
    n = 0
    for name, ja, jb in rows:
        n += 1
        if ja:
            a_sum += ja.get("overall", 0)
            a_pass += 1 if ja.get("pass") else 0
        if jb:
            b_sum += jb.get("overall", 0)
            b_pass += 1 if jb.get("pass") else 0
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name,
            ja and ja.get("completion"),
            ja and ja.get("correctness"),
            ja and ja.get("overall"),
            ja and ("✅" if ja.get("pass") else "❌"),
            jb and jb.get("completion"),
            jb and jb.get("overall"),
            jb and ("✅" if jb.get("pass") else "❌"),
        ))
    lines.append("\n## 汇总\n")
    lines.append("- A 组：平均 %.2f，通过 %d/%d" % (a_sum / n if n else 0, a_pass, n))
    lines.append("- B 组：平均 %.2f，通过 %d/%d" % (b_sum / n if n else 0, b_pass, n))
    out = os.path.join(EVAL_DIR,
                       "regression-%s.md" % time.strftime("%Y%m%d-%H%M%S"))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("WROTE", out)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
