# nhauphitruong-bot

Bot Telegram cho **nhauphitruong.com** → nhóm *Seo Web Nhậu Phi Trường*.

## 3 việc bot làm

| Việc | File | Lịch | Mô tả |
|---|---|---|---|
| Báo bài mới + bài đặt lịch lên web | `poster.py` | mỗi 30' | Ping `wp-cron.php` để đẩy bài **đặt lịch** tới hạn → publish, rồi báo mọi bài **mới publish** về nhóm (ảnh + link). |
| Ép index hàng ngày | `indexer.py` | 08:00 VN | Đọc sitemap → gửi URL mới/sửa lên Google Indexing API + IndexNow → báo tóm tắt về nhóm. |

Chạy trên **GitHub Actions** (miễn phí, repo public). Không đụng gì tới theme/website.

## Secrets (Settings → Secrets and variables → Actions)

| Secret | Bắt buộc | Ghi chú |
|---|---|---|
| `TELEGRAM_TOKEN` | ✅ | Token bot |
| `TELEGRAM_CHAT_ID` | ✅ | ID nhóm (số âm) |
| `GOOGLE_SA_JSON` | tùy | Toàn bộ JSON service account để **ép index Google**. Xem dưới. |
| `INDEXNOW_KEY` | tùy | Key IndexNow (Bing/Cốc Cốc). Cần đặt file `<key>.txt` ở gốc web. |

### Bật ép-index Google (5 phút, chỉ bạn làm được)
1. Google Cloud Console → tạo Project → bật **Indexing API**.
2. Tạo **Service Account** → tạo key JSON → tải về.
3. Mở JSON, copy `client_email` (dạng `...@...iam.gserviceaccount.com`).
4. [Search Console](https://search.google.com/search-console) của nhauphitruong.com → **Cài đặt → Người dùng và quyền → Thêm người dùng** → dán email đó → quyền **Chủ sở hữu**.
5. Dán **toàn bộ nội dung file JSON** vào secret `GOOGLE_SA_JSON`.
→ Lần index kế tiếp sẽ tự đẩy Google. (Quota mặc định ~200 URL/ngày.)

## Trạng thái
`state.json` lưu id các bài đã báo. Lần chạy đầu: coi toàn bộ bài hiện có là "đã báo"
(không dội kho cũ) — chỉ bài mới sau đó mới thông báo.

## Chạy tay
Actions → chọn workflow (`poster`/`indexer`) → **Run workflow**.
