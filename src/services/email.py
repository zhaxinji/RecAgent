import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import BackgroundTasks
from typing import List, Optional
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

def send_email(
    email_to: str,
    subject: str,
    html_content: str,
    cc: Optional[List[str]] = None,
) -> None:
    """
    发送邮件的通用函数
    
    参数:
        email_to: 接收者邮箱
        subject: 邮件主题
        html_content: HTML格式的邮件内容
        cc: 抄送列表
    """
    if not settings.SMTP_HOST or not settings.SMTP_PORT:
        logger.warning("SMTP服务器未配置，无法发送邮件")
        return

    message = MIMEMultipart()
    message["From"] = settings.EMAILS_FROM_EMAIL
    message["To"] = email_to
    message["Subject"] = subject
    
    if cc:
        message["Cc"] = ", ".join(cc)
        
    message.attach(MIMEText(html_content, "html"))
    
    try:
        if settings.SMTP_TLS:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
        recipients = [email_to]
        if cc:
            recipients.extend(cc)
            
        server.sendmail(settings.EMAILS_FROM_EMAIL, recipients, message.as_string())
        server.quit()
        logger.info(f"邮件已发送至 {email_to}")
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")

def send_email_background(
    background_tasks: BackgroundTasks,
    email_to: str,
    subject: str,
    html_content: str,
    cc: Optional[List[str]] = None,
) -> None:
    """
    在后台任务中发送邮件
    
    参数:
        background_tasks: FastAPI后台任务对象
        email_to: 接收者邮箱
        subject: 邮件主题
        html_content: HTML格式的邮件内容
        cc: 抄送列表
    """
    background_tasks.add_task(send_email, email_to, subject, html_content, cc)

def create_reset_password_content(username: str, token: str) -> str:
    """
    创建密码重置邮件的HTML内容
    
    参数:
        username: 用户名
        token: 重置令牌
        
    返回:
        HTML格式的邮件内容
    """
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    return f"""
    <html>
        <body>
            <p>尊敬的 {username}：</p>
            <p>您好！您最近请求重置您在 RecAgent 的密码。</p>
            <p>请点击下面的链接重置您的密码：</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p>如果您没有请求重置密码，请忽略此邮件。</p>
            <p>该链接将在 {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} 小时后失效。</p>
            <p>谢谢，</p>
            <p>RecAgent 团队</p>
        </body>
    </html>
    """

def send_reset_password_email(email: str, token: str, username: str) -> None:
    """
    发送密码重置邮件
    
    参数:
        email: 用户邮箱
        token: 重置令牌
        username: 用户名
    """
    subject = "RecAgent - 重置密码"
    html_content = create_reset_password_content(username, token)
    send_email(email_to=email, subject=subject, html_content=html_content)

def create_email_verification_content(username: str, token: str) -> str:
    """
    创建邮箱验证邮件的HTML内容
    
    参数:
        username: 用户名
        token: 验证令牌
        
    返回:
        HTML格式的邮件内容
    """
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    return f"""
    <html>
        <body>
            <p>尊敬的 {username}：</p>
            <p>感谢您注册 RecAgent！请点击下面的链接验证您的邮箱：</p>
            <p><a href="{verification_link}">{verification_link}</a></p>
            <p>如果您没有注册 RecAgent 账户，请忽略此邮件。</p>
            <p>该链接将在 24 小时后失效。</p>
            <p>谢谢，</p>
            <p>RecAgent 团队</p>
        </body>
    </html>
    """

def send_verification_email(email: str, token: str, username: str) -> None:
    """
    发送邮箱验证邮件
    
    参数:
        email: 用户邮箱
        token: 验证令牌
        username: 用户名
    """
    subject = "RecAgent - 验证您的邮箱"
    html_content = create_email_verification_content(username, token)
    send_email(email_to=email, subject=subject, html_content=html_content)

def send_welcome_email(email: str, username: str) -> None:
    """
    发送欢迎邮件
    
    参数:
        email: 用户邮箱
        username: 用户名
    """
    subject = "欢迎使用 RecAgent！"
    html_content = f"""
    <html>
        <body>
            <p>尊敬的 {username}：</p>
            <p>欢迎加入 RecAgent！</p>
            <p>我们很高兴您成为我们社区的一员。RecAgent 是一个面向推荐系统研究人员的智能研究助手平台，
            集成了文献管理、研究空白分析、实验设计和论文写作等功能，旨在提升研究效率和质量。</p>
            <p>如果您有任何问题或需要帮助，请随时联系我们的支持团队。</p>
            <p>祝您使用愉快！</p>
            <p>RecAgent 团队</p>
        </body>
    </html>
    """
    send_email(email_to=email, subject=subject, html_content=html_content) 