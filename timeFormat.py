from datetime import datetime, timezone, timedelta
from dateutil import parser

def format_for_web(dt_str: str) -> str:
    """
    将各种日期字符串规范化为网页友好的格式:
    'Nov 3, 2025 · 08:18 CST'
    （默认东八区北京时间，跨平台安全）
    """
    try:
        clean_str = dt_str.strip().strip("()").strip()
        dt = parser.parse(clean_str)
        
        # 无时区 → 默认视为 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # 转为北京时间
        beijing_tz = timezone(timedelta(hours=8))
        dt_bj = dt.astimezone(beijing_tz)

        # 兼容 Windows：不能用 %-d
        formatted = dt_bj.strftime("%b %d, %Y · %H:%M CST")
        # 去掉前导零（例如 03 → 3）
        formatted = formatted.replace(" 0", " ")

        return formatted

    except Exception as e:
        return dt_str

