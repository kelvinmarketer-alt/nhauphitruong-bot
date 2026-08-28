#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heartbeat — Nhậu Phi Trường.
Chỉ ping wp-cron.php để các bài ĐẶT LỊCH tới hạn tự chuyển sang publish đúng giờ
(dù web ít traffic). Việc BÁO Telegram (đặt lịch + đăng bài) do mu-plugin
`npt-telegram-posts.php` xử lý real-time ngay trên WordPress — KHÔNG báo ở đây
để tránh trùng thông báo.
"""
import os, requests
SITE = os.environ.get("SITE", "https://nhauphitruong.com").rstrip("/")
try:
    r = requests.get(f"{SITE}/wp-cron.php?doing_wp_cron",
                     headers={"User-Agent": "NPT-Heartbeat/1.0"}, timeout=25)
    print("wp-cron pinged:", r.status_code)
except Exception as e:
    print("wp-cron ping skip:", e)
