import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from typing import List, Optional

class EmailSender:
    """
    邮件发送器
    支持发送HTML格式报告和附件
    """
    def __init__(self, username: str, password: str, host: str = "smtp.gmail.com", port: int = 587):
        """
        初始化邮件发送器
        
        Args:
            username: 发件人邮箱 (Gmail地址)
            password: 邮箱密码 (对于Gmail，通常需要使用"应用专用密码")
            host: SMTP服务器地址 (默认Gmail: smtp.gmail.com)
            port: SMTP端口 (默认Gmail TLS端口: 587)
        """
        self.username = username
        self.password = password
        self.host = host
        self.port = port

    def send_email(
        self, 
        to_list: List[str], 
        subject: str, 
        content: str, 
        attachment_paths: Optional[List[str]] = None,
        is_html: bool = True
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_list: 收件人邮箱列表
            subject: 邮件主题
            content: 邮件正文
            attachment_paths: 附件文件路径列表
            is_html: 正文是否为HTML格式
            
        Returns:
            bool: 发送是否成功
        """
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ",".join(to_list)
        msg['Subject'] = subject

        # 添加正文
        msg.attach(MIMEText(content, 'html' if is_html else 'plain', 'utf-8'))

        # 添加附件
        if attachment_paths:
            for file_path in attachment_paths:
                if not os.path.exists(file_path):
                    print(f"⚠️ 警告: 附件不存在，已跳过: {file_path}")
                    continue
                
                try:
                    filename = os.path.basename(file_path)
                    # 判断是否为图片，图片可以用MIMEImage，其他用MIMEApplication
                    # 这里为了通用简单，统一处理，或者根据扩展名简单判断
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                        
                    part = MIMEApplication(file_data)
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(part)
                    # print(f"  已添加附件: {filename}")
                except Exception as e:
                    print(f"❌ 添加附件失败 {file_path}: {e}")

        # 发送邮件
        try:
            # print(f"正在连接SMTP服务器 {self.host}:{self.port}...")
            server = smtplib.SMTP(self.host, self.port)
            server.ehlo()
            server.starttls() # 启用TLS加密
            server.ehlo()
            
            # print("正在登录...")
            server.login(self.username, self.password)
            
            # print("正在发送...")
            server.sendmail(self.username, to_list, msg.as_string())
            server.quit()
            print(f"✅ 邮件已成功发送给: {to_list}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("❌ 发送失败: 认证错误。请检查邮箱和密码（Gmail请使用应用专用密码）。")
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            
        return False
