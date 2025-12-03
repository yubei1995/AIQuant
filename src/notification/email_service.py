import os
from dotenv import load_dotenv
from typing import List, Optional
from .email_sender import EmailSender

# 加载环境变量
load_dotenv()

def send_email_notification(
    to_list: List[str],
    subject: str,
    content: str,
    attachment_paths: Optional[List[str]] = None
) -> bool:
    """
    发送邮件通知服务
    自动从环境变量(.env)中读取 GMAIL_USER 和 GMAIL_PASS 进行发送
    
    Args:
        to_list: 收件人邮箱列表
        subject: 邮件主题
        content: 邮件正文 (支持HTML)
        attachment_paths: 附件路径列表
        
    Returns:
        bool: 发送是否成功
    """
    # 1. 获取配置
    username = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")
    
    if not username or not password:
        print("❌ 邮件发送失败: 未在环境变量(.env)中找到 GMAIL_USER 或 GMAIL_PASS 配置")
        print("   请检查 .env 文件是否存在且配置正确")
        return False
        
    # 2. 初始化发送器
    # 如果需要支持其他邮箱服务，这里可以扩展逻辑读取 HOST/PORT 配置
    sender = EmailSender(username=username, password=password)
    
    # 3. 执行发送
    return sender.send_email(
        to_list=to_list,
        subject=subject,
        content=content,
        attachment_paths=attachment_paths
    )
