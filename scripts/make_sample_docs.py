"""生成演示文档：报销制度 docx 与 100 周运维周报长文档。"""
from __future__ import annotations

import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample_docs"


def _make_docx() -> None:
    import docx

    path = SAMPLE_DIR / "02_报销管理制度.docx"
    document = docx.Document()
    document.add_heading("报销管理制度", level=1)

    document.add_heading("适用范围", level=2)
    document.add_paragraph(
        "本制度适用于公司全体正式员工和实习生因公发生的费用报销，包括差旅费、"
        "业务招待费、办公采购费、培训费等。报销应真实、合规、及时。"
    )

    document.add_heading("报销流程", level=2)
    document.add_paragraph(
        "1. 员工在费控系统提交报销单并上传发票和证明材料；"
        "2. 直属上级审批；3. 财务审核发票与金额；4. 统一打款。"
    )
    document.add_paragraph(
        "财务打款日为每月 10 日和 25 日，遇节假日顺延至下一工作日。"
        "紧急报销可申请加急，审批通过后 1 个工作日内打款。"
    )

    document.add_heading("发票要求", level=2)
    document.add_paragraph(
        "发票需为公司抬头的增值税发票，包含公司全称和纳税人识别号。"
        "电子发票需在税务局平台查验真伪，同一张发票禁止重复报销。"
        "发票日期应与业务发生日期一致，跨月费用需附情况说明。"
    )

    document.add_heading("差旅标准", level=2)
    document.add_paragraph(
        "交通：高铁限二等座，飞机限经济舱。住宿：一线城市每晚不超过 500 元，"
        "其他城市每晚不超过 350 元，超出部分自理。市内交通实报实销，单日上限 100 元。"
        "餐费补贴每天 80 元，按出差天数计算，不再单独报销餐费。"
    )

    document.add_heading("借款规定", level=2)
    document.add_paragraph(
        "出差前可申请备用金借款，单次上限 5000 元。出差返回后 7 个工作日内"
        "完成借款冲销，未及时冲销将暂停后续借款申请。"
    )

    document.add_heading("报销时限", level=2)
    document.add_paragraph(
        "费用发生后 30 天内提交报销单。跨月或跨年报销需在系统中说明原因，"
        "无合理原因的延迟报销财务有权退回。"
    )

    document.add_heading("违规处理", level=2)
    document.add_paragraph(
        "虚报、伪造、重复报销属于严重违纪行为，一经查实按公司规定处理，"
        "情节严重的解除劳动合同并保留追究法律责任的权利。"
    )

    table = document.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    data = [
        ["费用类型", "标准", "说明"],
        ["高铁", "二等座", "商务座需提前审批"],
        ["住宿", "500/350 元", "按城市分类执行"],
        ["餐补", "80 元/天", "按出差天数计算"],
    ]
    for row_index, row in enumerate(data):
        for col_index, value in enumerate(row):
            table.cell(row_index, col_index).text = value

    document.save(str(path))
    print(f"已生成: {path}")


def _make_long_report() -> None:
    path = SAMPLE_DIR / "09_知识库运维周报合集.txt"
    special = {
        52: "本周完成知识库全文检索服务升级，检索平均耗时从 8.2 秒降至 1.3 秒，"
            "上线后用户搜索失败率下降 60%。",
        63: "风险事件：主数据库磁盘使用率达 91%，已紧急扩容并完成数据迁移，服务未中断。",
        76: "风险事件：3 号机房空调冷媒泄漏，机房温度升至 28.5℃，"
            "已临时开启备用空调，预计 2 天内完成修复。",
        88: "本周完成新员工培训，主题为《提示词工程与知识库维护》，共 12 人参加。",
    }
    start = datetime.date(2026, 1, 5)
    lines: list[str] = []
    for week in range(1, 101):
        week_start = start + datetime.timedelta(weeks=week - 1)
        week_end = week_start + datetime.timedelta(days=6)
        lines.append(f"# 第 {week} 周周报（{week_start} 至 {week_end}）")
        lines.append("")
        lines.append("负责人：张伟")
        lines.append("")
        lines.append("## 本周完成")
        lines.append("")
        lines.append(f"- 巡检全部核心服务，处理告警 {week % 5 + 1} 起，均在时限内闭环。")
        lines.append(f"- 完成知识库例行更新，本周新增和修订文档 {week % 7 + 3} 篇。")
        if week in special:
            lines.append(f"- {special[week]}")
        lines.append("")
        lines.append("## 风险与问题")
        lines.append("")
        if week not in special:
            lines.append("- 无重大风险；磁盘、内存和带宽水位均在阈值以内。")
        else:
            lines.append("- 详见上文风险事件，已安排责任人跟进并写入下周计划。")
        lines.append("")
        lines.append("## 下周计划")
        lines.append("")
        lines.append("- 继续执行知识库更新和核心服务巡检。")
        lines.append(f"- 完成第 {week + 1} 周容量评估并输出周报。")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成: {path}")


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    _make_docx()
    _make_long_report()


if __name__ == "__main__":
    main()
