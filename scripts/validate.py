#!/usr/bin/env python3
"""validate.py — upwind-time 方向选择与时间投入计划七维校验器

输入: 方向/时间盘点计划 JSON（schema 见 tests/sample_good.json）
  {
    "weekly_screen": {                       // 第 1 步：风向筛（每周）
      "last_week_upwind_hours": 14,          // 上周上风口实际小时
      "last_week_total_hours": 40,           // 上周总工作小时
      "upwind_locked_in_calendar": true,     // 上风口时间锁进日历（非"有空就做"）
      "upwind_in_peak_energy": true,         // 排精力最好时段
      "tasks_screened": [                    // 本周待办已分上/下/半资产
        {"name": "把 X 系统核心链路吃透并写拆解", "class": "upwind"},
        {"name": "客户 A 紧急需求交付", "class": "fast"},
        {"name": "整理销售数据（产出数据口径文档）", "class": "semi_asset", "asset_output": "数据口径文档 v2"}
      ]
    },
    "reverse_questions": {                   // 第 2 步：反向三问（新任务接入前）
      "applied_to_new_tasks": true,          // 新任务接入前都过了三问
      "task_cards": [                        // 三问结论落盘的任务卡
        {
          "name": "慢仓项目：X 系统核心链路拆解",
          "q1_hard": true,                   // 够难（参照系：领域内已有能力的人）
          "q1_ref_frame": "该领域资深工程师",
          "q2_still_valid_3y": true,         // 三年后还成立（需求结构性）
          "q2_need_type": "结构性",
          "q3_next_steps": [                 // 做成后自动带出的下一步（≥3）
            "可迁移拆解方法用于 Y 系统",
            "团队新人用拆解文档上手",
            "发现可复用的中间层组件"
          ]
        }
      ]
    },
    "slow_fast_ledger": {                    // 第 3 步：快慢双仓
      "slow_items": [                        // 慢仓项目（1-2 个）
        {
          "name": "X 系统核心链路拆解",
          "concrete": true,                  // 具体名字（非"学底层能力"）
          "weekly_hours": 6,                 // 每周固定小时数（锁日历）
          "quarterly_evidence": "本季度能解释 X 系统调度层的三层机制并写出拆解文档",
          "exit_criteria": "连续两季度无 E1/E2/E3 证据 or 三问重验挂"
        }
      ],
      "fast_capacity_capped": true,          // 快仓设容量上限（超=砍/降级/拒）
      "buffer_reserved": true,               // 每周留 10-15% 缓冲（吃紧急插队）
      "slow_sacrificed_this_week": 0         // 本周慢仓被挤占小时数（=0）
    },
    "gap_notes": {                           // 第 4 步：缝隙笔记
      "entry_this_week": 3,                  // 本周新增条目数
      "entry_format_ok": true,               // 每条 <2 分钟、只记异常不记待办
      "weekly_review_done": true,            // 每周复盘翻一遍（数 ≥3 次同类）
      "recurrence_ge3": [                    // 出现≥3 次的同类违和感
        {"pattern": "排期总是排满无缓冲导致延期无人负责", "occurrences": 4, "escalated": true}
      ]
    },
    "quarterly_check": {                     // 第 5 步：季度检查
      "done_this_quarter": true,             // 本季度已做
      "slow_moved_forward": true,            // 慢仓有 E1/E2/E3 证据
      "evidence_type": "E3 产出拆解文档 + E1 看懂调度层机制",
      "reverse_questions_rechecked": true    // 慢仓项目三问重验
    },
    "fun_calibration": {                     // 第 0 步：月度乐趣校准
      "last_month_want_to_dig": true,        // 上月"想知道下一步"冲动（是/否）
      "consecutive_no_months": 0             // 连续为否的月数（≥2 = 方向错，回①）
    }
  }

七维校验（任一 FAIL → exit 1）：
  D1 风向筛: last_week_upwind_hours / last_week_total_hours ≥ 0.30（30% 地板）
     且 upwind_locked_in_calendar=true（锁日历，"有空就做"=没有）
     且 upwind_in_peak_energy=true（精力最好时段）
     且 tasks_screened 非空且每项 class ∈ {upwind, fast, semi_asset}，
     semi_asset 必须有 asset_output（不写明资产产物=下次还是纯搬运）
  D2 反向三问: applied_to_new_tasks=true 且 task_cards 非空；
     每张卡：q1_hard 须有 q1_ref_frame（参照系，"我只觉得难"不算）；
     q2_still_valid_3y 须有 q2_need_type（结构性/风口性）；
     q3_next_steps ≥3 条（列不出=终点不是上风口）
  D3 快慢双仓: slow_items 1-2 个（0 个=没有慢仓，3+ 个=注意力稀释）；
     每个慢仓项目：concrete=true + weekly_hours>0 + quarterly_evidence 非空
     + exit_criteria 非空（四要素缺一=立不住）；
     fast_capacity_capped=true（快仓无限=必然侵蚀慢仓）；
     buffer_reserved=true（无缓冲=紧急插队吃满慢仓）
  D4 缝隙笔记: entry_this_week ≥0 且 entry_format_ok=true（<2 分钟只记异常）
     且 weekly_review_done=true（不翻=不存在）；
     recurrence_ge3 中每条 occurrences ≥3（<3 次是噪音不是缝隙）
     且 escalated 已判定（true/false 都要有结论，不能空着）
  D5 季度检查: done_this_quarter=true 且 slow_moved_forward=true
     且 evidence_type 非空且含 E1/E2/E3 标记（"在积累"不算证据）
     且 reverse_questions_rechecked=true（世界在变，三问要重验）
  D6 乐趣校准: consecutive_no_months < 2（连续两月为否=方向错，
     必须回①重看风向，不能继续"靠意志力"）
  D7 一致性: 慢仓项目的 weekly_hours 总和 ≤ 上周上风口实际小时
     （慢仓是上风口的一部分，慢仓小时不能超出上风口实际投入——
     超出=上风口时间被记账虚报，30% 地板是假的）
     且 last_week_upwind_hours ≥ slow_items 每周小时总和的当周应投

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

TASK_CLASSES = {"upwind", "fast", "semi_asset"}
EVIDENCE_MARKS = ("E1", "E2", "E3")


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def is_nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def validate(plan):
    checks = []

    ws = plan.get("weekly_screen") or {}
    rq = plan.get("reverse_questions") or {}
    sfl = plan.get("slow_fast_ledger") or {}
    gn = plan.get("gap_notes") or {}
    qc = plan.get("quarterly_check") or {}
    fc = plan.get("fun_calibration") or {}

    # D1 风向筛
    uh, th = ws.get("last_week_upwind_hours"), ws.get("last_week_total_hours")
    tasks = ws.get("tasks_screened") or []
    if not isinstance(uh, (int, float)) or not isinstance(th, (int, float)) or th <= 0:
        fail(checks, "D1", f"上风口/总工作小时非法（{uh!r}/{th!r}）——先有数字才能谈占比")
    elif uh / th < 0.30:
        fail(checks, "D1", f"上风口占比 {uh}/{th}={uh/th:.0%} < 30%——地板没守住（上风口永远排在快仓后面）")
    elif ws.get("upwind_locked_in_calendar") is not True:
        fail(checks, "D1", "upwind_locked_in_calendar=false——上风口时间没锁日历，'有空就做'=没有")
    elif ws.get("upwind_in_peak_energy") is not True:
        fail(checks, "D1", "upwind_in_peak_energy=false——上风口没排精力最好时段（排在'剩下的时间'=会被挤掉）")
    else:
        bad_tasks = []
        for t in tasks:
            if t.get("class") not in TASK_CLASSES:
                bad_tasks.append(f"{t.get('name', '?')}(class 非法)")
            elif t.get("class") == "semi_asset" and not is_nonempty_str(t.get("asset_output")):
                bad_tasks.append(f"{t.get('name', '?')}(半资产没写资产产物=下次还是纯搬运)")
        if not tasks:
            fail(checks, "D1", "tasks_screened 为空——本周待办没分上/下/半资产，风向筛没做")
        elif bad_tasks:
            fail(checks, "D1", "任务分类推错: " + "；".join(bad_tasks))
        else:
            ok(checks, "D1", f"风向筛合规（上风口 {uh}/{th}h={uh/th:.0%}，锁日历+精力时段，{len(tasks)} 项已归类）")

    # D2 反向三问
    cards = rq.get("task_cards") or []
    if rq.get("applied_to_new_tasks") is not True:
        fail(checks, "D2", "applied_to_new_tasks=false——新任务接入前没过三问，'伟大'叙事在替代属性判断")
    elif not cards:
        fail(checks, "D2", "task_cards 为空——三问结论没落盘（季度复盘时无从回看'当时为什么收'）")
    else:
        bad_cards = []
        for c in cards:
            nm = str(c.get("name", "?"))
            if c.get("q1_hard") is not True or not is_nonempty_str(c.get("q1_ref_frame")):
                bad_cards.append(f"{nm}(Q1 挂或没参照系——'我只觉得难'=学习曲线不是壁垒)")
            elif c.get("q2_still_valid_3y") is not True or not is_nonempty_str(c.get("q2_need_type")):
                bad_cards.append(f"{nm}(Q2 挂或没需求类型——'很有前景'是感觉不是证伪)")
            else:
                ns = c.get("q3_next_steps") or []
                if len([x for x in ns if is_nonempty_str(x)]) < 3:
                    bad_cards.append(f"{nm}(Q3 下一步 <3 条——带不出下一步的是终点不是上风口)")
        if bad_cards:
            fail(checks, "D2", "任务卡三问不全: " + "；".join(bad_cards))
        else:
            ok(checks, "D2", f"反向三问落盘（{len(cards)} 张任务卡，三问全有证据）")

    # D3 快慢双仓
    slows = sfl.get("slow_items") or []
    if not (1 <= len(slows) <= 2):
        fail(checks, "D3", f"慢仓项目 {len(slows)} 个——须 1-2 个（0 个=没有慢仓，纯快仓=滑向下风口；3+=注意力稀释，每个都不会推进）")
    else:
        bad_slow = []
        for s in slows:
            nm = str(s.get("name", "?"))
            if s.get("concrete") is not True:
                bad_slow.append(f"{nm}('学底层能力'式=没有慢仓)")
            elif not isinstance(s.get("weekly_hours"), (int, float)) or s.get("weekly_hours") <= 0:
                bad_slow.append(f"{nm}(没锁每周固定小时数)")
            elif not is_nonempty_str(s.get("quarterly_evidence")):
                bad_slow.append(f"{nm}(没有季度推进证据标准='感觉在推进'的温床)")
            elif not is_nonempty_str(s.get("exit_criteria")):
                bad_slow.append(f"{nm}(没有退出判据=沉没成本绑架)")
        if bad_slow:
            fail(checks, "D3", "慢仓立项要素不全: " + "；".join(bad_slow))
        elif sfl.get("fast_capacity_capped") is not True:
            fail(checks, "D3", "fast_capacity_capped=false——快仓不设上限=来者不拒=必然侵蚀慢仓")
        elif sfl.get("buffer_reserved") is not True:
            fail(checks, "D3", "buffer_reserved=false——没留缓冲=紧急插队直接吃满慢仓")
        else:
            if sfl.get("slow_sacrificed_this_week") != 0:
                fail(checks, "D3", f"slow_sacrificed_this_week={sfl.get('slow_sacrificed_this_week')}——慢仓被挤占=滑向下风口的开始（不是'这周太忙'）")
            else:
                ok(checks, "D3", f"快慢双仓合规（{len(slows)} 个慢仓四要素齐全，快仓有上限+有缓冲，本周零挤占）")

    # D4 缝隙笔记
    ent = gn.get("entry_this_week")
    if not isinstance(ent, int) or ent < 0:
        fail(checks, "D4", f"entry_this_week={ent!r}——本周新增条目数非法")
    elif gn.get("entry_format_ok") is not True:
        fail(checks, "D4", "entry_format_ok=false——记录 >2 分钟或混进待办（缝隙笔记死于太重/变成第二待办清单）")
    elif gn.get("weekly_review_done") is not True:
        fail(checks, "D4", "weekly_review_done=false——不翻的缝隙笔记=不存在（写进周复盘固定项）")
    else:
        rec = gn.get("recurrence_ge3")
        if not isinstance(rec, list):
            fail(checks, "D4", "recurrence_ge3 缺失——每周复盘要数'出现≥3次的同类'（不是每周都强求升级，但没有这个字段=没数）")
        else:
            bad_rec = [f"{r.get('pattern', '?')}(出现{r.get('occurrences')}次<3=噪音)"
                       for r in rec if not isinstance(r.get("occurrences"), int) or r.get("occurrences") < 3]
            undecided = [r.get("pattern", "?") for r in rec
                         if "escalated" not in r or r.get("escalated") is None]
            if bad_rec:
                fail(checks, "D4", "缝隙判定错误: " + "；".join(bad_rec))
            elif undecided:
                fail(checks, "D4", f"缝隙升级未判定: {undecided}（≥3 次的同类必须给出升级结论：走哪个出口或继续观察）")
            else:
                ok(checks, "D4", f"缝隙笔记合规（本周 {ent} 条 + 周复盘已做 + ≥3次同类 {len(rec)} 项已判定）")

    # D5 季度检查
    ev = str(qc.get("evidence_type") or "")
    if qc.get("done_this_quarter") is not True:
        fail(checks, "D5", "done_this_quarter=false——本季度没做慢仓检查（季度检查是慢仓唯一的检查机制，不做=慢仓裸奔）")
    elif qc.get("slow_moved_forward") is not True:
        fail(checks, "D5", "slow_moved_forward=false——慢仓没挪动（本季度先记录；连续两季度=方向错，回①重看风向）")
    elif not is_nonempty_str(ev) or not any(m in ev for m in EVIDENCE_MARKS):
        fail(checks, "D5", f"evidence_type='{ev}'——证据必须标 E1/E2/E3（'在积累/还没到出活'=没有证据）")
    elif qc.get("reverse_questions_rechecked") is not True:
        fail(checks, "D5", "reverse_questions_rechecked=false——世界在变，慢仓项目的三问要季度重验（当时的'三年成立'可能已经不成立）")
    else:
        ok(checks, "D5", f"季度检查合规（慢仓挪动证据: {ev[:25]}… + 三问已重验）")

    # D6 乐趣校准
    cno = fc.get("consecutive_no_months")
    if not isinstance(cno, int) or cno < 0:
        fail(checks, "D6", f"consecutive_no_months={cno!r}——连续为否月数非法（月度校准没做）")
    elif cno >= 2:
        fail(checks, "D6", f"consecutive_no_months={cno}——连续两月'不想往下挖'=方向选错了（不是意志力问题），必须回①重看风向")
    else:
        lm = fc.get("last_month_want_to_dig")
        if not isinstance(lm, bool):
            fail(checks, "D6", f"last_month_want_to_dig={lm!r}——月度校准没做（'想知道下一步'冲动是/否）")
        else:
            ok(checks, "D6", f"乐趣校准合规（上月={lm}，连续为否 {cno} 月 <2）")

    # D7 一致性：慢仓小时 vs 上风口实际
    slow_hours_sum = 0
    for s in slows:
        if isinstance(s.get("weekly_hours"), (int, float)):
            slow_hours_sum += s["weekly_hours"]
    if isinstance(uh, (int, float)) and isinstance(th, (int, float)) and th > 0 and uh / th >= 0.30:
        if slows and slow_hours_sum > uh:
            fail(checks, "D7", f"慢仓每周合计 {slow_hours_sum}h > 上风口实际 {uh}h——慢仓是上风口的一部分，超出=上风口记账虚报（30% 地板是假的）")
        else:
            ok(checks, "D7", f"一致性合规（慢仓 {slow_hours_sum}h ≤ 上风口实际 {uh}h）")
    else:
        ok(checks, "D7", "一致性跳过（D1 未通过，占比无法核验）")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
