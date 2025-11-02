import asyncio
import aiohttp
import feedparser
from datetime import datetime
from logger import logger
from yaml import safe_load
from sender import Mail_sender
from logger import logger, PM
from yamlconfig import yamlconfig


class Processor:
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")

    async def get_entries(self, session, url, limit=3):
        """异步获取一个 feed 的若干条最新文章"""
        headers = {"User-Agent": yamlconfig().config_yaml()["user_agent"]}
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                text = await resp.text()
                feed = feedparser.parse(text)
                results = []
                for e in feed.entries[:limit]:
                    title = e.get("title", "(无标题)")
                    link = e.get("link", "#")
                    date = e.get("published", "未知日期")
                    results.append({"title": title, "link": link, "date": date})
                return feed.feed.get("title", url), results  # type: ignore
        except Exception as ex:
            logger.error(f"无法解析：{url} - {ex}")
            return url, []

    async def collect_all(self):
        """根据 feeds.yaml 中配置异步收集所有主题的更新"""
        cfg = yamlconfig()
        all_data = {}

        async with aiohttp.ClientSession() as session:
            for topic, urls in cfg.feeds_yaml()['feeds'].items():
                tasks = [self.get_entries(session, url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                topic_data = []
                for r in results:
                    if isinstance(r, Exception):
                        logger.warning(f"{topic} 某 feed 抓取失败：{r}")
                        continue
                    feed_title, entries = r # type: ignore
                    topic_data.append({"feed_title": feed_title, "entries": entries})

                all_data[topic] = topic_data
        return all_data

    def generate_email_html(self, all_data):
        """生成邮件 HTML 格式内容"""
        html = [
            f"<h2>📅 每日资讯汇总 - {self.today}</h2>",
            "<hr>",
        ]

        for topic, feeds in all_data.items():
            html.append(f"<h3>📰 {topic}</h3>")
            for fdata in feeds:
                html.append(f"<p><b>{fdata['feed_title']}</b></p><ul>")
                for e in fdata["entries"]:
                    html.append(
                        f"<li><a href='{e['link']}'>{e['title']}</a> "
                        f"<small>（{e['date']}）</small></li>"
                    )
                html.append("</ul>")
            html.append("<hr>")

        return "\n".join(html)


async def main():
    processor = Processor()
    all_data = await processor.collect_all()
    html_content = processor.generate_email_html(all_data)

    message_info = {
        "recipient_email": "huangguo02@qq.com",
        "subject": "每日资讯汇总",
        "message": html_content,
    }

    try:
        Mail_sender.send_mail(messageinfo=message_info)
        logger.info("✅ 邮件发送成功")
    except Exception as ex:
        logger.error(f"📧 邮件发送失败，将保存为本地文件 - {ex}")
        filename = PM.path.parent / "emails" / f"daily_feed_{PM.today_format()}.html"
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ 已保存本地文件：{filename}")


if __name__ == "__main__":
    asyncio.run(main())

