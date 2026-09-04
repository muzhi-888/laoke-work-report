#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_from_log.py —— 周报/月报工作汇报生成器 配套脚本

功能：把零散的工作记录、待办、commit 文本，按类目自动归类并统计，
      产出一份 Markdown 周报草稿骨架。纯 Python 标准库，零依赖，离线可用。

用法：
  python report_from_log.py --input log.txt          # 从文件读
  python report_from_log.py                          # 从 stdin 读（管道）
  python report_from_log.py --demo                   # 用内置示例跑一遍（自检）
  python report_from_log.py --input log.txt --title "工作周报（示例）"

输出：Markdown 写到 stdout，同时打印分类计数表。
退出码：0 成功；非 0 输入为空或参数错误。
"""

import sys
import argparse
import re
from collections import OrderedDict

# 类目关键词表（命中即归类，按顺序优先级：缺陷修复 > 重构优化 > 新功能 > 协作沟通 > 业务推进 > 其他）
CATEGORY_RULES = OrderedDict([
    ("缺陷修复", ["修复", "fix", "bug", "报错", "异常", "故障", "排查", "定位", "解决", "崩", "patch"]),
    ("重构优化", ["重构", "refactor", "优化", "性能", "提速", "压测", "降级", "精简", "清理", "tech debt", "技术债"]),
    ("新功能", ["新增", "开发", "feature", "实现", "上线", "接入", "搭建", "完成", "交付", "模块", "支持"]),
    ("协作沟通", ["会议", "对齐", "评审", "沟通", "同步", "答疑", "协调", "周会", "访谈", "培训", "分享"]),
    ("业务推进", ["客户", "报价", "成单", "签约", "拜访", "拓客", "回款", "跟进", "谈判", "线索", "订单", "营收"]),
])

DEFAULT_CATEGORY = "其他"


def classify(text):
    t = text.lower()
    for cat, kws in CATEGORY_RULES.items():
        for kw in kws:
            if kw.lower() in t:
                return cat
    return DEFAULT_CATEGORY


def parse_items(raw_lines):
    """把原始文本拆成一条条工作项。支持：每行一条；或「- 」/「* 」/「1. 」前缀；或 commit 行。"""
    items = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # 去掉常见列表前缀
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^\d+[.、]\s+", "", line)
        # 跳过纯分隔符
        if set(line) <= set("-=_* "):
            continue
        # 跳过表头类
        if line.startswith("|") or line.endswith("|"):
            continue
        items.append(line)
    return items


def build_report(title, items):
    grouped = OrderedDict((c, []) for c in list(CATEGORY_RULES.keys()) + [DEFAULT_CATEGORY])
    for it in items:
        grouped[classify(it)].append(it)

    # 计数表
    counts = {c: len(v) for c, v in grouped.items() if v}

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("> 以下为自动归类草稿，请补充数据与核心贡献后使用。数字与成果以你确认为准。")
    lines.append("")
    lines.append("## 一、本周核心贡献（待你补充一句话）")
    lines.append("")
    lines.append("## 二、工作明细（按类目）")
    lines.append("")
    for cat, its in grouped.items():
        if not its:
            continue
        lines.append(f"### {cat}（{len(its)} 项）")
        for it in its:
            lines.append(f"- {it}")
        lines.append("")
    lines.append("## 三、分类计数")
    lines.append("")
    lines.append("| 类目 | 项数 |")
    lines.append("|------|------|")
    for c, n in counts.items():
        lines.append(f"| {c} | {n} |")
    lines.append("")
    lines.append("## 四、待补充（自检清单）")
    lines.append("- [ ] 核心贡献一句话")
    lines.append("- [ ] 关键数据（成单/客单价/故障率等，带环比）")
    lines.append("- [ ] 下周计划 ≤3 条")
    lines.append("- [ ] 需支持/待决策项")
    lines.append("- [ ] 敏感信息脱敏确认")
    return "\n".join(lines), counts


DEMO_TEXT = """周一跟客户 A 对了需求
周二出了方案初稿
周三过会评审
修复导出 bug 影响 120 人
周五定位线上卡顿是缓存击穿加了哨兵
新增跟进 8 个其中 3 个报价
完成订单系统 v2.3 上线
重构了缓存层把响应时间压了一半
跟产线对齐了交付节点
写了两份 SOP 文档"""


def main():
    ap = argparse.ArgumentParser(description="工作记录 → 周报草稿归类器")
    ap.add_argument("--input", help="输入文件路径（每行一条工作项）")
    ap.add_argument("--title", default="工作周报（自动草稿）", help="报告标题")
    ap.add_argument("--demo", action="store_true", help="用内置示例运行（自检）")
    args = ap.parse_args()

    if args.demo:
        raw = DEMO_TEXT.splitlines()
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                raw = f.readlines()
        except OSError as e:
            sys.stderr.write(f"[错误] 无法读取输入文件: {e}\n")
            return 2
    else:
        if sys.stdin.isatty():
            sys.stderr.write("[提示] 未给 --input 且非管道输入，使用 --demo 查看示例。\n")
            raw = DEMO_TEXT.splitlines()
        else:
            raw = sys.stdin.read().splitlines()

    items = parse_items(raw)
    if not items:
        sys.stderr.write("[错误] 未解析到任何工作项，请检查输入。\n")
        return 1

    report, counts = build_report(args.title, items)
    sys.stdout.write(report + "\n")
    sys.stderr.write(f"[完成] 共归类 {sum(counts.values())} 项，分布: " +
                     ", ".join(f"{c}={n}" for c, n in counts.items()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
