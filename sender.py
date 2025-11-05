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
        self.lock = asyncio.Lock()      # 防止并发访问
        self.conn_lock = asyncio.Lock() # 防止并发重连
        self.FailedSend = []

    # -----------------------------
    # 建立连接（只在必要时执行）
    # -----------------------------
    def connect(self):
        """初始化并连接邮件服务器"""
        if self.connected:
            return  # 已连接直接返回

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

    # -----------------------------
    # 异步单封邮件发送
    # -----------------------------
    async def send_mail(self, messageinfo: dict, type_="html"):
        for key in ["recipient_email", "subject", "message"]:
            if key not in messageinfo:
                raise ValueError(f"缺少必要的参数：{key}")

        msg = MIMEText(messageinfo["message"], type_, "utf-8")
        msg["From"] = formataddr(("通知服务", self.server_info["email"]))
        msg["To"] = messageinfo["recipient_email"]
        msg["Subject"] = messageinfo["subject"]

        async with self.lock:  # 保证线程安全
            # 检查连接是否正常（仅当断开时尝试重连）
            if not self.connected or not self.server:
                async with self.conn_lock:
                    if not self.connected:
                        logger.info("🔄 检测到连接断开，尝试重连...")
                        self.connect()

            sender_email = self.server_info["email"]
            try:
                await asyncio.to_thread(
                    self.server.sendmail,  # type: ignore
                    sender_email,
                    messageinfo["recipient_email"],
                    msg.as_string()
                )
                logger.info(f"✅ 邮件已发送至 {messageinfo['recipient_email']}")
                await asyncio.sleep(1.2)

            except smtplib.SMTPServerDisconnected:
                logger.warning("⚠️ SMTP 连接意外断开，准备重新连接...")
                async with self.conn_lock:
                    self.connected = False
                    self.connect()
                await asyncio.to_thread(
                    self.server.sendmail,  # type: ignore
                    sender_email,
                    messageinfo["recipient_email"],
                    msg.as_string()
                )
                logger.info(f"✅ 邮件已重新发送至 {messageinfo['recipient_email']}")

            except Exception as e:
                self.FailedSend.append(messageinfo)
                logger.error(f"❌ 邮件 {messageinfo['recipient_email']} 发送失败: {e}")

    # -----------------------------
    # 批量发送（只连接一次）
    # -----------------------------
    async def send_batch(self, messages: list[dict]):
        if not messages:
            logger.warning("⚠️ 未提供任何邮件任务")
            return

        # 🔐 确保全局只连接一次
        if not self.connected:
            async with self.conn_lock:
                if not self.connected:
                    self.connect()

        semaphore = asyncio.Semaphore(3)

        async def safe_send(msg):
            async with semaphore:
                await self.send_mail(msg)

        await asyncio.gather(*(safe_send(m) for m in messages), return_exceptions=True)
        logger.info("📬 所有邮件任务已完成")

        await self.final_check_async()
        await asyncio.to_thread(self.disconnect)

    # -----------------------------
    # 异步重试失败邮件
    # -----------------------------
    async def final_check_async(self):
        if not self.FailedSend:
            return

        logger.info(f"📦 检测到 {len(self.FailedSend)} 封未发送成功的邮件，正在重试...")

        retry_limit = 3
        remaining = []

        for msg in list(self.FailedSend):
            success = False
            for attempt in range(retry_limit):
                try:
                    await self.send_mail(msg)
                    success = True
                    break
                except Exception as e:
                    logger.error(f"❌ 重试第 {attempt + 1} 次失败: {e}")
                    await asyncio.sleep(2)
            if not success:
                remaining.append(msg)

        if remaining:
            logger.warning(f"⚠️ 仍有 {len(remaining)} 封邮件最终未能发送。")
        else:
            logger.info("✅ 所有失败邮件已补发成功。")

        self.FailedSend = remaining

    # -----------------------------
    # 同步重试 + 安全断开
    # -----------------------------
    def final_check(self):
        if not self.FailedSend:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.final_check_async())
        else:
            loop.create_task(self.final_check_async())

    def disconnect(self):
        self.final_check()
        if self.server:
            try:
                self.server.quit()
                logger.info("📭 已断开邮件服务器连接")
            except Exception as e:
                logger.warning(f"断开连接时出错: {e}")
            finally:
                self.server = None
                self.connected = False


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
