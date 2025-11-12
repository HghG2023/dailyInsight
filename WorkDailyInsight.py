import asyncio
from feedcollector import FeedCollector
from sender import Mail
from logger import logger, PM
from yamlconfig import yamlconfig

def save_to_public(html_content):
    filename = PM.base_path.parent /"PublicEmailsHtml" / f"daily_feed_{PM.today_format()}.html"
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"✅ 已保存本地文件：{filename.absolute()}")

async def main():
    try:
        local_html = PM.base_path.parent /"PublicEmailsHtml" / f"daily_feed_{PM.today_format()}.html"
        if local_html.exists():
            html_content = local_html.read_text(encoding="utf-8")
        else:
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
                            # for receiver in ["huangguo02@qq.com"]
                        ]

        try:
            Mail_sender = Mail()
            await Mail_sender.send_batch(message_list)
            save_to_public(html_content)
            # raise Exception("test")
        except Exception as ex:
            message_bigerror = "邮件系统故障失败:\n" + str(ex)
            raise Exception(message_bigerror)
    except Exception as e:
        logger.error(e)
        Mail_log = Mail()
        with open(PM.path / f"{PM.today_format()}.log", "r", encoding="utf-8") as f:
            log_content = f.read()
        await Mail_log.send_mail({
                                    "recipient_email": "huangguo02@qq.com",
                                    "subject": "Debug Log",
                                    "message": log_content,
                                    }, 
                                    "plain"
                                    )
        Mail_log.disconnect()


if __name__ == "__main__":
    # asyncio.run(main())
    with open(PM.path / f"{PM.today_format()}.log", "r", encoding="utf-8") as f:
        print("-"*100)
        print(f.read())
        print("-"*100)
    # save_to_public("test")
