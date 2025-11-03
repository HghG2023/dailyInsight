import smtplib
import asyncio
from email.mime.text import MIMEText
from email.utils import formataddr
import time
from logger import logger
from yamlconfig import yamlconfig


class Mail:
    def __init__(self):
        self.server_info = yamlconfig().config_yaml()["sender"]
        self.server = None
        self.connected = False
        self.lock = asyncio.Lock()  # 用于防止并发操作同一连接
        self.FailedSend = [] # 记录发送失败的任务

    def connect(self):
        """初始化并连接邮件服务器"""
        info = self.server_info
        sender_email = info["email"]
        smtp_server = info["server"]
        smtp_port = info["port"]
        password = info["password"]

        try:
            if smtp_port == 465:
                self.server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
            else:
                self.server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
                self.server.starttls()
            self.server.login(sender_email, password)
            self.connected = True
            logger.info(f"📬 邮件服务器已连接: {smtp_server}:{smtp_port}")
        except Exception as e:
            logger.error(f"❌ 邮件服务器连接失败: {e}")
            self.server = None
            self.connected = False
            raise ConnectionError("无法连接邮件服务器")


    def final_check(self):
        # 若存在发送失败的邮件，尝试重发
        if getattr(self, "FailedSend", None):
            if self.FailedSend:
                logger.info(f"📦 检测到 {len(self.FailedSend)} 封未发送成功的邮件，正在重试...")

                retry_limit = 3
                remaining = []

                for msg in self.FailedSend:
                    success = False
                    for attempt in range(retry_limit):
                        try:
                            # 同步调用异步函数
                            asyncio.run(self.send_mail(msg))
                            success = True
                            break
                        except Exception as e:
                            logger.error(f"❌ 重试第 {attempt + 1} 次失败: {e}")
                            time.sleep(2)
                    if not success:
                        remaining.append(msg)

                if remaining:
                    logger.warning(f"⚠️ 仍有 {len(remaining)} 封邮件最终未能发送。")
                else:
                    logger.info("✅ 所有失败邮件已补发成功。")

    def disconnect(self):
        """安全退出连接（在断开前同步重发所有失败邮件）"""
        self.final_check()

        # 断开连接
        if self.server:
            try:
                self.server.quit()
                logger.info("📭 已断开邮件服务器连接")
            except Exception as e:
                logger.warning(f"断开连接时出错: {e}")
            finally:
                self.server = None
                self.connected = False


    async def send_mail(self, messageinfo: dict, type_="html"):
        """异步发送单封邮件（带重连保护）"""
        for key in ["recipient_email", "subject", "message"]:
            if key not in messageinfo:
                raise ValueError(f"缺少必要的参数：{key}")

        msg = MIMEText(messageinfo["message"], type_ , "utf-8")
        msg["From"] = formataddr(("通知服务", self.server_info["email"]))
        msg["To"] = messageinfo["recipient_email"]
        msg["Subject"] = messageinfo["subject"]

        async with self.lock:  # 🔒 确保连接在同一时间只被一个任务使用
            if not self.connected or not self.server:
                self.connect()

            sender_email = self.server_info["email"]
            try:
                await asyncio.to_thread(
                    self.server.sendmail, # type: ignore
                    sender_email,
                    messageinfo["recipient_email"],
                    msg.as_string()
                )
                logger.info(f"✅ 邮件已发送至 {messageinfo['recipient_email']}")
                # 限速防止 QQ 邮箱 454 错误
                await asyncio.sleep(1.5)

            except smtplib.SMTPServerDisconnected:
                logger.warning("⚠️ SMTP 连接中断，尝试重连...")
                self.connected = False
                self.connect()
                await asyncio.to_thread(
                    self.server.sendmail, # type: ignore
                    sender_email,
                    messageinfo["recipient_email"],
                    msg.as_string()
                )
                logger.info(f"✅ 邮件已重新发送至 {messageinfo['recipient_email']}")

            except Exception as e:
                self.FailedSend.append(messageinfo)
                logger.error(f"❌ 邮件{messageinfo['recipient_email']}发送失败: {e}")
                self.disconnect()  # 出错时断开连接，避免状态不一致

    async def send_batch(self, messages: list[dict]):
        """异步批量发送邮件（控制并发 + 自动限速 + 独立错误处理）"""
        if not messages:
            logger.warning("⚠️ 未提供任何邮件任务")
            return

        semaphore = asyncio.Semaphore(3)  # 限制最大并发数为3

        async def safe_send(msg):
            async with semaphore:
                await self.send_mail(msg)

        # ✅ gather 并发执行，但确保每个任务独立，不会中断其它任务
        await asyncio.gather(*(safe_send(m) for m in messages), return_exceptions=True)
        logger.info("📬 所有邮件任务已完成")

        # 所有任务结束后安全断开
        self.disconnect()


    # - "huangguo02@qq.com"
    # - "1906318962@qq.com"
    # - "2023020417@buct.edu.cn"



# 示例
if __name__ == "__main__":
    async def main():
        test_msg = {
            "recipient_email": "test@example.com",
            "subject": "测试邮件",
            "message": "<h3>异步发送测试</h3>"
        }
        try:
            Mail_sender = Mail()
            await Mail_sender.send_batch([test_msg])
        except Exception as e:
            logger.error(e)
        finally:
            Mail_sender.disconnect()

    asyncio.run(main())
