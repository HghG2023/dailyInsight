import asyncio
from feedcollector import FeedCollector
from sender import Mail_sender 
from logger import logger, PM
from yamlconfig import yamlconfig


async def main():
    collector = FeedCollector()
    all_data = await collector.collect_all()
    html_content = collector.generate_email_html(all_data)


    message_info = {
        # "recipient_email": receiver,
        "subject": "每日资讯汇总",
        "message": html_content,
    }

    message_list = [
                        {
                            **message_info,  # 解包模板字典
                            "recipient_email": receiver
                        }
                        for receiver in yamlconfig().config_yaml()["receiver"]["email"]
                    ]

    try:
        await Mail_sender.send_batch(message_list)
    except Exception as ex:
        filename = PM.path.parent / "emails" / f"daily_feed_{PM.today_format()}.html"
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ 已保存本地文件：{filename}")


if __name__ == "__main__":
    asyncio.run(main())
