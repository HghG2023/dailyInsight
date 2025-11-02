import requests
import feedparser
import yaml
from datetime import datetime
from sender import Mail_sender
from logger import logger, PM

class Feed:
    def __init__(self):
        self.load()

    def load(self):
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        with open("feeds.yaml", "r", encoding="utf-8") as f:
            self.feeds = yaml.safe_load(f)

Feedset = Feed()


class Processor:
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")

    def get_entries(self, url, limit=3):
        """获取一个 feed 的若干条最新文章"""
        headers = {"User-Agent": Feedset.config["user_agent"]}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(resp.text)
            results = []
            for e in feed.entries[:limit]:
                title = e.get("title", "(无标题)")
                link = e.get("link", "#")
                date = e.get("published", "未知日期")
                results.append({"title": title, "link": link, "date": date})
            return feed.feed.get("title", url), results # type: ignore
        except Exception as ex:
            logger.error(f"无法解析：{url} - {ex}")
            return url, []

    def collect_all(self):
        """根据 feeds.yaml 中配置收集所有主题的更新"""
        all_data = {}
        for topic, urls in Feedset.feeds["feeds"].items():
            topic_data = []
            for url in urls:
                feed_title, entries = self.get_entries(url)
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


if __name__ == "__main__":
    processor = Processor()
    all_data = processor.collect_all()
    html_content = processor.generate_email_html(all_data)
    massage_info = {"recipient_email": "huangguo02@qq.com",
                    "subject": "每日资讯汇总",
                    "message": html_content
                    }

    try:
        Mail_sender.send_mail(messageinfo=massage_info)
    except Exception as ex:
        logger.error(f"邮件发送失败, 存储文件 - {ex}")
            # 保存为文件（可直接作为邮件正文）
        filename = PM.path.parent / "emails" / f"daily_feed_{PM.today_format()}.html"
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("✅ 已生成 ，可用于邮件发送")
