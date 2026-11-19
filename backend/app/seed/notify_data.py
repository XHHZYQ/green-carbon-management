"""消息通知域示例数据（B6）。

覆盖：通知渠道（notify_channel）、通知模板（notify_template）、通知规则（notify_rule）、
站内消息（notify_message）、发送记录（notify_send_log）。

用法：
    uv run python -m app.seed.run_seed
"""

import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notify import (
    NotifyChannel,
    NotifyMessage,
    NotifyRule,
    NotifySendLog,
    NotifyTemplate,
)
from app.models.sys import SysUser

random.seed(20260310)

# 渠道：(编码, 名称, 类型, 配置)
CHANNELS = [
    ("CH_INTERNAL", "站内消息", "internal", {"keep_days": 90}),
    ("CH_EMAIL", "邮件通知", "email",
     {"smtp_host": "smtp.green.com", "smtp_port": 465, "sender": "noreply@green.com", "ssl": True}),
    ("CH_SMS", "短信通知", "sms",
     {"provider": "aliyun", "sign_name": "绿色低碳园区", "template_code": "SMS_2026"}),
    ("CH_WEBHOOK", "Webhook 推送", "webhook",
     {"url": "https://open.green.com/hook/notify", "method": "POST", "timeout": 5}),
]

# 模板：(编码, 名称, 渠道类型, 标题, 内容, 变量)
TEMPLATES = [
    ("TPL_ALARM", "告警通知", "internal", "【告警】{device_name} 触发 {alarm_type}",
     "设备 {device_name} 于 {time} 触发 {alarm_type} 告警，当前值 {value}，请及时处理。", "device_name,alarm_type,time,value"),
    ("TPL_QUOTA", "定额超标预警", "email", "【预警】{area_name} {energy_name} 用量超定额",
     "区域 {area_name} 的 {energy_name} 本月已用 {used}，超出定额 {quota}，请关注。", "area_name,energy_name,used,quota"),
    ("TPL_WO_ASSIGN", "工单指派", "sms", "【工单】您有新的工单待处理",
     "工单 {wo_no}（{wo_title}）已指派给您，请于 {deadline} 前处理完成。", "wo_no,wo_title,deadline"),
    ("TPL_WO_DONE", "工单完成", "internal", "【工单】{wo_no} 已处理完成",
     "工单 {wo_no} 已由 {operator} 处理完成，用时 {cost}，感谢配合。", "wo_no,operator,cost"),
    ("TPL_DAILY", "日报推送", "email", "【日报】园区能碳日报 {date}",
     "截止 {date}，园区累计用电 {power}，碳排放 {emission}，环比 {rate}。", "date,power,emission,rate"),
    ("TPL_REPORT", "报表订阅", "webhook", "【报表】{report_name} 已生成",
     "您订阅的 {report_name} 已生成，下载地址：{url}。", "report_name,url"),
]

# 规则：(名称, 事件类型, 条件, 渠道编码, 接收人用户名)
RULES = [
    ("设备告警自动通知", "alarm.created",
     {"level": ["warning", "critical"]}, ["CH_INTERNAL", "CH_SMS"], ["ops", "admin"]),
    ("区域定额超标预警", "quota.exceed",
     {"threshold": 100, "unit": "%"}, ["CH_EMAIL", "CH_INTERNAL"], ["energy", "admin"]),
    ("工单指派通知", "wo.assigned",
     {"status": "assigned"}, ["CH_SMS", "CH_INTERNAL"], ["ops"]),
    ("能碳日报推送", "report.daily",
     {"cron": "0 8 * * *"}, ["CH_EMAIL"], ["admin", "energy"]),
    ("报表订阅推送", "report.subscribe",
     {"subscribe": True}, ["CH_WEBHOOK", "CH_EMAIL"], ["admin"]),
]

# 消息标题池，按 msg_type / level 组合生成
MESSAGE_SAMPLES = [
    ("1#配电房 A 相电流越限", "设备 1#配电房 A 相电流达到 320A，超过告警阈值 300A，请及时处理。"),
    ("2#空调机组通信中断", "2#空调机组已连续 10 分钟无法采集数据，疑似通信中断，请检查网络。"),
    ("A 区照明回路用电异常", "A 区照明回路近 1 小时用电量较基线上升 35%，存在异常，请排查。"),
    ("B 区本月用电超定额预警", "B 区本月用电已达 12,860 kWh，超出定额 5%，请注意节能。"),
    ("工单 WO20260301 已指派", "您有新的巡查工单 WO20260301，请于今日 18:00 前处理完成。"),
    ("工单 WO20260228 处理完成", "工单 WO20260228（空调滤网清洗）已处理完成，感谢配合。"),
    ("园区能碳日报已生成", "2026-03-09 园区能碳日报已生成，累计用电 42,180 kWh，碳排放 24.6 tCO2e。"),
    ("光伏发电量日报", "昨日光伏发电量 3,260 kWh，替代减排 1.86 tCO2e，运行正常。"),
    ("碳报告月度订阅推送", "您订阅的《2026年2月碳排放报告》已生成，请前往报表中心查看。"),
    ("储能系统告警解除", "储能系统 SOC 偏低告警已于 09:12 自动解除，当前运行正常。"),
]


async def seed_notify_domain(session: AsyncSession) -> dict[str, int]:
    """写入消息通知域示例数据（先重置后写入）。"""
    await session.execute(delete(NotifySendLog))
    await session.execute(delete(NotifyMessage))
    await session.execute(delete(NotifyRule))
    await session.execute(delete(NotifyTemplate))
    await session.execute(delete(NotifyChannel))
    await session.commit()

    now = datetime.now().astimezone()

    # ---------------- 渠道 ----------------
    channels: dict[str, NotifyChannel] = {}
    for code, name, ctype, config in CHANNELS:
        ch = NotifyChannel(
            channel_code=code,
            channel_name=name,
            channel_type=ctype,
            config_json=config,
            enable_status=1,
            created_at=now - timedelta(days=random.randint(60, 180)),
        )
        session.add(ch)
        channels[code] = ch
    await session.flush()

    # ---------------- 模板 ----------------
    templates: list[NotifyTemplate] = []
    for code, name, ctype, title, content, variables in TEMPLATES:
        tpl = NotifyTemplate(
            template_code=code,
            template_name=name,
            channel_type=ctype,
            title=title,
            content=content,
            variables=variables,
            status=1,
            created_at=now - timedelta(days=random.randint(30, 150)),
        )
        session.add(tpl)
        templates.append(tpl)
    await session.flush()

    # ---------------- 规则 ----------------
    users = {u.username: u for u in (await session.execute(select(SysUser))).scalars().all()}
    rules: list[NotifyRule] = []
    for name, event, cond, channel_codes, receiver_names in RULES:
        ch_ids = [str(channels[c].id) for c in channel_codes if c in channels]
        rec_ids = [str(users[n].id) for n in receiver_names if n in users]
        rule = NotifyRule(
            rule_name=name,
            event_type=event,
            condition_json=cond,
            channel_ids=",".join(ch_ids) or None,
            receiver_ids=",".join(rec_ids) or None,
            enable_status=1,
            created_at=now - timedelta(days=random.randint(20, 120)),
        )
        session.add(rule)
        rules.append(rule)
    await session.flush()

    # ---------------- 站内消息 ----------------
    user_list = list(users.values())
    msg_types = ["internal", "internal", "internal", "email", "sms"]
    levels = ["info", "info", "warning", "warning", "critical"]
    message_count = 0
    for _ in range(40):
        title, content = random.choice(MESSAGE_SAMPLES)
        send_time = now - timedelta(
            days=random.randint(0, 89),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        is_read = random.random() < 0.55
        session.add(
            NotifyMessage(
                title=title,
                content=content,
                msg_type=random.choice(msg_types),
                level=random.choice(levels),
                receiver_id=random.choice(user_list).id,
                read_status=1 if is_read else 0,
                read_time=send_time + timedelta(hours=random.randint(1, 48)) if is_read else None,
                send_time=send_time,
            )
        )
        message_count += 1

    # ---------------- 发送记录 ----------------
    fail_reasons = ["邮件服务器连接超时", "短信网关返回余额不足", "Webhook 响应非 2xx", "接收人手机号无效"]
    log_count = 0
    for _ in range(25):
        rule = random.choice(rules)
        tpl = random.choice(templates)
        ch = random.choice(list(channels.values()))
        send_time = now - timedelta(
            days=random.randint(0, 89),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        failed = random.random() < 0.15
        session.add(
            NotifySendLog(
                rule_id=rule.id,
                template_id=tpl.id,
                channel_id=ch.id,
                receiver=random.choice(user_list).real_name or random.choice(user_list).username,
                title=tpl.title,
                content=tpl.content,
                send_status="failed" if failed else "success",
                error_msg=random.choice(fail_reasons) if failed else None,
                send_time=send_time,
            )
        )
        log_count += 1

    await session.commit()
    return {
        "通知渠道": len(channels),
        "通知模板": len(templates),
        "通知规则": len(rules),
        "站内消息": message_count,
        "发送记录": log_count,
    }
