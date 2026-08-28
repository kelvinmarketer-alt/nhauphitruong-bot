# nhauphitruong-bot

Bot Telegram cho **nhauphitruong.com** → nhóm *Seo Web Nhậu Phi Trường*.

## Kiến trúc

| Việc | Ở đâu | Lịch |
|---|---|---|
| Báo **bài đặt lịch** + **bài đăng lên web** (real-time, kèm ảnh/link) | mu-plugin `npt-telegram-posts.php` trên WordPress | ngay khi lên lịch / đăng |
| **Ép index** + báo cáo trạng thái (đã/chưa index, kiểu Tuấn Tú) | `indexer.py` (GitHub Actions) | 08:00 VN mỗi ngày |
| **Heartbeat** ping wp-cron để bài đặt lịch đăng đúng giờ | `poster.py` (GitHub Actions) | mỗi 15 phút |

> Thông báo bài viết do **mu-plugin làm real-time** (thấy cả bài đặt lịch). GitHub Actions
> chỉ lo ép index + ping wp-cron. Vì vậy không có thông báo trùng.

## Secrets (GitHub → Settings → Secrets and variables → Actions)
| Secret | Dùng cho |
|---|---|
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | báo cáo index |
| `GOOGLE_SA_JSON` | Google Indexing API + URL Inspection (SA là Chủ sở hữu property URL-prefix) |

## mu-plugin
File `wp-content/mu-plugins/npt-telegram-posts.php` (token/chat nhúng trong file, chạy server-side).
Hook `transition_post_status`: → `future` báo "ĐÃ LÊN LỊCH"; → `publish` báo "Bài mới". Mỗi bài
báo 1 lần (dùng post meta chống trùng). Chỉ áp dụng `post_type = post`.

## Báo cáo index
`indexer.py` đọc sitemap → URL Inspection API phân loại đã/chưa index → ép index (Indexing API)
các URL chưa index → gửi báo cáo về nhóm. SA `npt-indexer@mephil-fb-bot.iam.gserviceaccount.com`.
