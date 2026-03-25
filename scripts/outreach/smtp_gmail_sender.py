#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail SMTP 自动发邮件脚本
使用 Gmail SMTP 服务器发送邮件，更稳定可靠
"""

import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional


class GmailSMTPSender:
    """Gmail SMTP 邮件发送器"""
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    def __init__(self, 
                 sender_email: Optional[str] = None,
                 sender_password: Optional[str] = None,
                 sender_name: Optional[str] = None):
        """
        初始化 Gmail SMTP 发送器
        
        Args:
            sender_email: 发件人邮箱，不传则从环境变量 GMAIL_SENDER_EMAIL 读取
            sender_password: 应用专用密码，不传则从环境变量 GMAIL_APP_PASSWORD 读取
            sender_name: 发件人名称，不传则从环境变量 GMAIL_SENDER_NAME 读取
        """
        self.sender_email = sender_email or os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = sender_password or os.getenv("GMAIL_APP_PASSWORD")
        self.sender_name = sender_name or os.getenv("GMAIL_SENDER_NAME", "KOL Workflow")
        
        if not self.sender_email:
            raise ValueError("请设置 GMAIL_SENDER_EMAIL 环境变量或在初始化时传入 sender_email")
        if not self.sender_password:
            raise ValueError("请设置 GMAIL_APP_PASSWORD 环境变量或在初始化时传入 sender_password")
    
    def send_email(self, 
                   to: str, 
                   subject: str, 
                   body: str,
                   html: bool = False) -> bool:
        """
        发送单封邮件
        
        Args:
            to: 收件人邮箱
            subject: 邮件主题
            body: 邮件正文
            html: 是否为HTML格式
        
        Returns:
            bool: 发送是否成功
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.sender_name, self.sender_email))
            msg['To'] = to
            msg['Subject'] = subject
            
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))
            
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, [to], msg.as_string())
            
            print(f"✅ 邮件已发送至: {to}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print(f"❌ 认证失败，请检查邮箱和应用专用密码: {to}")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP错误: {to} - {e}")
            return False
        except Exception as e:
            print(f"❌ 发送失败: {to} - {e}")
            return False
    
    def send_batch(self, 
                   recipients: List[str], 
                   subject: str, 
                   body_template: str,
                   delay_between: int = 30,
                   html: bool = False,
                   name_field: str = "{{name}}") -> Dict:
        """
        批量发送邮件
        
        Args:
            recipients: 收件人邮箱列表
            subject: 邮件主题
            body_template: 邮件正文模板（可用 {{name}} 占位符）
            delay_between: 发送间隔（秒）
            html: 是否为HTML格式
            name_field: 姓名占位符
        
        Returns:
            dict: 发送结果统计
        """
        results = {"success": 0, "failed": 0, "failed_emails": []}
        
        print(f"\n📤 开始发送邮件，共 {len(recipients)} 封")
        print(f"   发件人: {self.sender_name} <{self.sender_email}>")
        print(f"   主题: {subject}")
        print(f"   间隔: {delay_between} 秒")
        print("-" * 50)
        
        for i, recipient in enumerate(recipients):
            print(f"\n[{i+1}/{len(recipients)}] 发送给: {recipient}")
            
            personalized_body = body_template.replace(name_field, recipient.split("@")[0])
            
            success = self.send_email(recipient, subject, personalized_body, html)
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_emails"].append(recipient)
            
            if i < len(recipients) - 1:
                print(f"⏳ 等待 {delay_between} 秒后发送下一封...")
                time.sleep(delay_between)
        
        return results
    
    def send_from_excel(self,
                        excel_path: str,
                        email_column: str = "联系方式",
                        subject_column: str = "邮件主题",
                        body_column: str = "邮件正文",
                        delay: int = 30,
                        html: bool = False) -> Dict:
        """
        从Excel文件读取并发送邮件
        
        Args:
            excel_path: Excel文件路径
            email_column: 邮箱列名
            subject_column: 主题列名（如果没有则使用默认主题）
            body_column: 正文列名（如果没有则使用默认正文）
            delay: 发送间隔（秒）
            html: 是否为HTML格式
        
        Returns:
            dict: 发送结果统计
        """
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel文件不存在: {excel_path}")
        
        df = pd.read_excel(excel_path)
        
        if email_column not in df.columns:
            raise ValueError(f"Excel中没有找到邮箱列: {email_column}")
        
        emails = df[email_column].dropna().tolist()
        emails = [str(e).strip() for e in emails if "@" in str(e)]
        
        if subject_column in df.columns:
            subjects = df[subject_column].fillna(DEFAULT_EMAIL_SUBJECT).tolist()
        else:
            subjects = [DEFAULT_EMAIL_SUBJECT] * len(emails)
        
        if body_column in df.columns:
            bodies = df[body_column].fillna(DEFAULT_EMAIL_BODY).tolist()
        else:
            bodies = [DEFAULT_EMAIL_BODY] * len(emails)
        
        results = {"success": 0, "failed": 0, "failed_emails": []}
        
        print(f"\n📤 开始发送邮件，共 {len(emails)} 封")
        print(f"   发件人: {self.sender_name} <{self.sender_email}>")
        print(f"   间隔: {delay} 秒")
        print("-" * 50)
        
        for i, (email, subject, body) in enumerate(zip(emails, subjects, bodies)):
            print(f"\n[{i+1}/{len(emails)}] 发送给: {email}")
            
            success = self.send_email(email, subject, body, html)
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
            
            if i < len(emails) - 1:
                print(f"⏳ 等待 {delay} 秒后发送下一封...")
                time.sleep(delay)
        
        return results


def load_recipients_from_csv(csv_path: str, email_column: str = "联系方式") -> list:
    """从CSV文件加载收件人列表"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if email_column not in df.columns:
        raise ValueError(f"CSV中没有找到列: {email_column}")
    
    emails = df[email_column].dropna().tolist()
    emails = [str(e).strip() for e in emails if "@" in str(e)]
    return emails


DEFAULT_EMAIL_SUBJECT = "【商务合作邀请】您好，我是XXX品牌方"

DEFAULT_EMAIL_BODY = """您好，

我在抖音上关注了您的内容，非常欣赏您的创作风格！

我们是XXX品牌，正在寻找优质达人合作。本次合作包括：
• 有竞争力的报酬
• 自由创作空间
• 长期合作机会

如果您对我们的合作感兴趣，欢迎回复这封邮件，我很期待能进一步沟通！

祝好，
XXX品牌商务团队
"""


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gmail SMTP 自动发邮件工具")
    parser.add_argument("--csv", "-c", help="CSV文件路径，包含邮箱地址列")
    parser.add_argument("--excel", "-e", help="Excel文件路径")
    parser.add_argument("--emails", nargs="+", help="直接指定邮箱地址")
    parser.add_argument("--subject", "-s", default=DEFAULT_EMAIL_SUBJECT, help="邮件主题")
    parser.add_argument("--body", "-b", default=DEFAULT_EMAIL_BODY, help="邮件正文模板")
    parser.add_argument("--delay", "-d", type=int, default=30, help="发送间隔（秒）")
    parser.add_argument("--html", action="store_true", help="发送HTML格式邮件")
    parser.add_argument("--test", "-t", help="发送测试邮件到指定邮箱")
    
    args = parser.parse_args()
    
    try:
        sender = GmailSMTPSender()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("\n请配置以下环境变量：")
        print("  GMAIL_SENDER_EMAIL=your_email@gmail.com")
        print("  GMAIL_APP_PASSWORD=your_app_password")
        print("\n获取应用专用密码：https://myaccount.google.com/apppasswords")
        return
    
    if args.test:
        print(f"🧪 发送测试邮件到: {args.test}")
        success = sender.send_email(args.test, "测试邮件", "这是一封测试邮件")
        if success:
            print("✅ 测试邮件发送成功！")
        else:
            print("❌ 测试邮件发送失败")
        return
    
    recipients = []
    if args.emails:
        recipients = args.emails
    elif args.csv:
        recipients = load_recipients_from_csv(args.csv)
    elif args.excel:
        results = sender.send_from_excel(args.excel, delay=args.delay, html=args.html)
        print("\n" + "=" * 50)
        print(f"📊 发送完成!")
        print(f"   成功: {results['success']}")
        print(f"   失败: {results['failed']}")
        if results['failed_emails']:
            print(f"   失败邮箱: {results['failed_emails']}")
        return
    else:
        print("⚠️ 请指定 --csv, --excel 或 --emails")
        return
    
    if not recipients:
        print("⚠️ 没有找到有效的邮箱地址")
        return
    
    results = sender.send_batch(
        recipients=recipients,
        subject=args.subject,
        body_template=args.body,
        delay_between=args.delay,
        html=args.html
    )
    
    print("\n" + "=" * 50)
    print(f"📊 发送完成!")
    print(f"   成功: {results['success']}")
    print(f"   失败: {results['failed']}")
    if results['failed_emails']:
        print(f"   失败邮箱: {results['failed_emails']}")


if __name__ == "__main__":
    main()
