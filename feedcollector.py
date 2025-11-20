import asyncio
import aiohttp
import feedparser
from datetime import datetime
from html import escape
import requests
from logger import logger
from timeFormat import format_for_web
from yamlconfig import yamlconfig  # 假设已实现加载 feeds.yaml / config.yaml

class FeedCollector:

    _TEST = {"test": [{
                        "url": "https://blog.google/rss/",
                        "name": "Google Blog",
                        "limit": 3
                      }]
    }
    
    def __init__(self,cfg = None):
        self.header = {"User-Agent": yamlconfig().config_yaml().get("user_agent")}
        self.daily_quote = (requests.get("https://v1.hitokoto.cn/", headers=self.header).json().get("hitokoto") 
                            or 
                            requests.get("https://api.codelife.cc/yiyan/random", headers=self.header).json().get("data").get("hitokoto")
                            or
                            "今日罢工~~~")   
        self.feeds_cfg = yamlconfig().feeds_yaml().get("feeds", {}) if cfg is None else cfg  
        self.claims = """
                        <hr style="border:none;border-top:1px solid #ddd;margin-top:20px;margin-bottom:20px;">
                        
                        <p style="font-size:13px; color:#666; line-height:1.6;">
                        📎 <b>版权声明与免责声明 / Copyright & Disclaimer</b><br>
                        本邮件内容基于公开的 <a href="https://en.wikipedia.org/wiki/RSS" target="_blank" style="color:#1a73e8;text-decoration:none;">RSS 源</a> 自动生成，仅展示来源网站的标题、摘要与原文链接，用于学习与信息分享。<br>
                        所有文章及内容版权归原作者及所属媒体所有，若涉及版权问题，请联系以便及时处理。<br>
                        本邮件不代表任何媒体立场，不承担因内容使用或转载所产生的法律责任。<br>
                        📬 如果你喜欢这份每日资讯，欢迎转发分享，但请保留完整来源说明。<br><br>

                        This email is generated from publicly available <a href="https://en.wikipedia.org/wiki/RSS" target="_blank" style="color:#1a73e8;text-decoration:none;">RSS feeds</a> and only includes titles, summaries, and links to the original articles for educational and informational purposes.<br>
                        All articles and content are copyrighted by the original authors and their respective media. Please contact us if any copyright concerns arise.<br>
                        This email does not represent the views of any media outlet and we assume no responsibility for any legal issues arising from the use or redistribution of its content.<br>
                        📬 Feel free to forward this daily digest, but please retain full source attribution.
                        </p>
                    """

    async def get_entries(self, session, feed_info: dict):
        """异步获取一个 feed 的若干条最新文章"""
        url = feed_info.get("url")
        name = feed_info.get("name", url)
        limit = feed_info.get("limit", 3)
        headers = self.header

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
                    results.append({"title": title, "link": link, "date": format_for_web(date)}) # type: ignore

                feed_title = feed.feed.get("title", name) # type: ignore
                return feed_title, results

        except asyncio.TimeoutError:
            logger.error(f"请求超时：{url}")
        except Exception as ex:
            logger.error(f"无法解析：{url} - {ex}")

        return name, []

    async def collect_all(self):
        """根据 feeds.yaml 中配置异步收集所有主题的更新"""
        feeds_cfg = self.feeds_cfg
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
        # 💡 每日格言区域（如果提供）
        if self.daily_quote:
            # html.append(f"<div class='quote'>💭 果哥偷文~ </div>")
            html.append(f"<div class='quote'>💭 {self.daily_quote}</div>")

        html.append("<hr style='border:none;border-top:2px solid #ddd;'>")


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
                        f"<small style='color:#666;'>({today})</small><br>"
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

        html.append(self.claims)
        return "\n".join(html)

if __name__ == "__main__":
    # print(type(FeedCollector().feeds_cfg))
    ...