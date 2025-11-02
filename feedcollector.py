import asyncio
import aiohttp
import feedparser
from datetime import datetime
from html import escape
from logger import logger
from yamlconfig import yamlconfig  # 假设已实现加载 feeds.yaml / config.yaml

class FeedCollector:

    async def get_entries(self, session, feed_info: dict):
        """异步获取一个 feed 的若干条最新文章"""
        url = feed_info.get("url")
        name = feed_info.get("name", url)
        limit = feed_info.get("limit", 3)
        headers = {"User-Agent": yamlconfig().config_yaml().get("user_agent", "Mozilla/5.0")}

        try:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"请求失败：{url}（HTTP {resp.status}）")
                    return name, []

                text = await resp.text()
                feed = feedparser.parse(text)
                results = []

                for e in feed.entries[:limit]:
                    title = str(e.get("title", "(无标题)")).strip()
                    link = e.get("link", "#")
                    date = e.get("published") or e.get("updated") or e.get("pubDate") or "未知日期"
                    results.append({"title": title, "link": link, "date": date})

                feed_title = feed.feed.get("title", name) # type: ignore
                return feed_title, results

        except asyncio.TimeoutError:
            logger.error(f"请求超时：{url}")
        except Exception as ex:
            logger.error(f"无法解析：{url} - {ex}")

        return name, []

    async def collect_all(self):
        """根据 feeds.yaml 中配置异步收集所有主题的更新"""
        cfg = yamlconfig()
        feeds_cfg = cfg.feeds_yaml().get("feeds", {})
        all_data = {}

        async with aiohttp.ClientSession() as session:
            for topic, feed_list in feeds_cfg.items():
                if not feed_list:
                    continue
                tasks = [self.get_entries(session, f) for f in feed_list]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                topic_data = []
                for r in results:
                    if isinstance(r, Exception):
                        logger.warning(f"[{topic}] 某 feed 抓取失败：{r}")
                        continue
                    feed_title, entries = r # type: ignore
                    topic_data.append({"feed_title": feed_title, "entries": entries})

                all_data[topic] = topic_data

        return all_data

    def generate_email_html(self, all_data):
        """生成邮件 HTML 格式内容"""
        today = datetime.now().strftime("%Y-%m-%d")
        html = [
            "<style>"
            "body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; line-height:1.6; }"
            "h2 { color:#333; }"
            "h3 { color:#2b6cb0; margin-top:1em; }"
            "a { text-decoration:none; color:#1a73e8; }"
            "a:hover { text-decoration:underline; }"
            "</style>",
            f"<h2>📅 每日资讯汇总 - {today}</h2>",
            "<hr style='border:none;border-top:2px solid #ddd;'>"
        ]

        for topic, feeds in all_data.items():
            topic_title = topic.replace("_", " ").title()
            html.append(f"<h3>📰 {escape(topic_title)}</h3>")

            for fdata in feeds:
                feed_title = escape(fdata.get("feed_title", "未知来源"))
                entries = fdata.get("entries", [])
                html.append(f"<p><b>{feed_title}</b></p><ul style='margin-top:0;margin-bottom:1em;'>")

                if not entries:
                    html.append(
                        f"<li>无更新</li>"
                        f"<small style='color:#666;'>({date})</small><br>"
                        )

                for e in entries:
                    title = escape(e.get("title", "无标题"))
                    link = escape(e.get("link", "#"))
                    date = escape(e.get("date", "未知日期"))

                    html.append(
                        f"<li style='margin-bottom:6px;'>"
                        f"<a href='{link}' target='_blank'>{title}</a> "
                        f"<small style='color:#666;'>({date})</small><br>"
                        f"</li>"
                    )

                html.append("</ul>")
            html.append("<hr style='border:none;border-top:1px dashed #ccc;'>")

        html.append("<p style='font-size:0.9em;color:#999;'>Generated automatically by DailyFeedBot</p>")
        return "\n".join(html)
