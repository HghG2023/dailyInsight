import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from logger import logger
from yamlconfig import yamlconfig
# server_info = {
#     "email": "hg020309@gmail.com",
#     "password": "arel dreq ecvw bpwq",
#     "server": "smtp.gmail.com",
#     "port": 587
#     }

class Mail:
    def __init__(self):
        self.server_info = yamlconfig().config_yaml()["sender"]

    def send_mail(self, messageinfo: dict):

        serverinfo = self.server_info

        for key in ["recipient_email", "subject", "message"]:
            if key not in messageinfo:
                raise ValueError(f"缺少必要的参数：{key}")
        for key in ["email", "password", "server", "port"]:
            if key not in serverinfo:
                raise ValueError(f"缺少必要的参数：{key}")
        
        sender_email = serverinfo["email"]
        smtp_server = serverinfo["server"]
        smtp_port = serverinfo["port"]
        password = serverinfo["password"]

        msg = MIMEText(messageinfo["message"], "html", "utf-8")
        msg["From"] = formataddr(("通知服务", sender_email))
        msg["To"] = messageinfo["recipient_email"]
        msg["Subject"] = messageinfo["subject"]

        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, messageinfo["recipient_email"], msg.as_string())
            server.quit()
            logger.info("✅ 已发送！")
        except Exception as e:
            logger.error(f"❌ 发送失败: {e}")




# gmail_app_psw = 'arel dreq ecvw bpwq'
# Gmail SMTP 配置
Mail_sender = Mail()

if __name__ == "__main__":
    
    Mail_sender = Mail()

    message_info = {"recipient_email": "huangguo02@qq.com", 
                    "subject": "test", 
                    "message": "你好，今天记得开心！"
                    }


    Mail_sender.send_mail(messageinfo=message_info)
