import asyncio
import os
import aiofiles
from feedcollector import FeedCollector
from sender import Mail
from logger import logger, PM
from yamlconfig import yamlconfig

async def save_to_public(html_content):
    base = PM.base_path.parent / "PublicEmailsHtml"
    real_file = base / f"daily_feed_{PM.today_format()}.html"
    link_file = base / "daily_feed_latest.html"

    base.mkdir(parents=True, exist_ok=True)

    # 1. 写真实文件（异步）
    if html_content:
        async with aiofiles.open(real_file, "w", encoding="utf-8") as f:
            await f.write(html_content)
        logger.info(f"✨ 已写入：{real_file}")

        # 2. 更新软链接（同步但极快，不需要异步）
        if link_file.exists() or link_file.is_symlink():
            link_file.unlink()

        os.symlink(real_file.name, link_file)
        logger.info(f"🔗 已更新 latest 链接 → {link_file}")

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
            await save_to_public(html_content)
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
    if yamlconfig().config_yaml()["debug"] == False: 
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"{'x'*20}任务失败：{e}")
        finally:
            with open(PM.path / f"{PM.today_format()}.log", "r", encoding="utf-8") as f:
                print("-"*100)
                print(f.read())
                print("-"*100)
    else:
        print(f"{PM.today_format()} Debug Mode On", )
