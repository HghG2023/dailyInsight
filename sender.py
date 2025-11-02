import smtplib
import asyncio
from email.mime.text import MIMEText
from email.utils import formataddr
from logger import logger
from yamlconfig import yamlconfig


class Mail:
    def __init__(self):
        self.server_info = yamlconfig().config_yaml()["sender"]
        self.server = None
        self.connected = False

    def connect(self):
        """初始化并连接邮件服务器"""
        info = self.server_info
        sender_email = info["email"]
        smtp_server = info["server"]
        smtp_port = info["port"]
        password = info["password"]

        try:
            if smtp_port == 465:
                self.server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                self.server = smtplib.SMTP(smtp_server, smtp_port)
                self.server.starttls()
            self.server.login(sender_email, password)
            self.connected = True
            logger.info(f"📬 邮件服务器已连接: {smtp_server}:{smtp_port}")
        except Exception as e:
            logger.error(f"❌ 邮件服务器连接失败: {e}")
            self.server = None
            self.connected = False
            # 关键：抛出异常让上层知道失败
            raise ConnectionError("无法连接邮件服务器")

    def disconnect(self):
        """安全退出连接"""
        if self.server:
            try:
                self.server.quit()
                logger.info("📭 已断开邮件服务器连接")
            except Exception as e:
                logger.warning(f"断开连接时出错: {e}")
            finally:
                self.server = None
                self.connected = False

    async def send_mail(self, messageinfo: dict):
        """异步发送邮件"""
        # 检查必要参数
        for key in ["recipient_email", "subject", "message"]:
            if key not in messageinfo:
                raise ValueError(f"缺少必要的参数：{key}")

        if not self.connected or not self.server:
            self.connect()

        sender_email = self.server_info["email"]

        msg = MIMEText(messageinfo["message"], "html", "utf-8")
        msg["From"] = formataddr(("通知服务", sender_email))
        msg["To"] = messageinfo["recipient_email"]
        msg["Subject"] = messageinfo["subject"]

        try:
            await asyncio.to_thread(
                self.server.sendmail, # type: ignore
                sender_email,
                messageinfo["recipient_email"],
                msg.as_string()
            )
            logger.info(f"✅ 邮件已发送至 {messageinfo['recipient_email']}")
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {e}")
            self.disconnect()  # 出错时断开，避免连接状态不一致

    async def send_batch(self, messages: list[dict]):
        """异步批量发送邮件"""
        try:
            if not self.connected:
                self.connect()
            tasks = [self.send_mail(msg) for msg in messages]
            await asyncio.gather(*tasks)
        finally:
            self.disconnect()


Mail_sender = Mail()


# 示例
if __name__ == "__main__":
    async def main():
        try:
            await Mail_sender.send_mail({
                "recipient_email": "test@example.com",
                "subject": "测试邮件",
                "message": "<h3>异步发送测试</h3>"
            })
        except Exception as e:
            logger.error(e)
        finally:
            Mail_sender.disconnect()

    asyncio.run(main())
