#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poster bot — Nhậu Phi Trường.
Mỗi lần chạy:
  1) Ping wp-cron.php để đẩy các bài ĐẶT LỊCH (future) tới hạn -> publish.
  2) Đọc REST lấy các bài đã publish gần đây.
  3) Bài nào CHƯA gửi thì bắn thông báo về nhóm Telegram (kèm ảnh + link).
Trạng thái lưu ở state.json (danh sách id đã gửi). Lần đầu: coi toàn bộ bài
hiện có là "đã gửi" (baseline) để không spam cả kho cũ — chỉ bài MỚI mới báo.
"""
import os, json, sys, html, re, time
import requests

SITE   = os.environ.get("SITE", "https://nhauphitruong.com").rstrip("/")
TOKEN  = os.environ["TELEGRAM_TOKEN"]
CHAT   = os.environ["TELEGRAM_CHAT_ID"]
STATE  = os.environ.get("STATE_FILE", "state.json")
UA     = "Mozilla/5.0 (compatible; NPT-Poster/1.0)"
TG     = f"https://api.telegram.org/bot{TOKEN}"

def log(*a): print(*a, flush=True)

def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            s = json.load(f)
    except Exception:
        s = {}
    s.setdefault("initialized", False)
    s.setdefault("sent_ids", [])
    return s

def save_state(s):
    s["sent_ids"] = s["sent_ids"][-300:]  # giữ 300 id gần nhất
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def ping_wpcron():
    try:
        requests.get(f"{SITE}/wp-cron.php?doing_wp_cron", headers={"User-Agent": UA}, timeout=25)
        log("wp-cron pinged")
    except Exception as e:
        log("wp-cron ping skip:", e)

def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()

def fetch_recent(n=30):
    url = (f"{SITE}/wp-json/wp/v2/posts?per_page={n}&status=publish"
           f"&orderby=date&order=desc&_embed=wp:featuredmedia")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
    r.raise_for_status()
    return r.json()

def featured_url(post):
    try:
        media = post.get("_embedded", {}).get("wp:featuredmedia", [])
        if media and isinstance(media, list):
            src = media[0].get("source_url")
            if src: return src
    except Exception:
        pass
    return None

def tg_send(post):
    title = strip_html(post["title"]["rendered"])
    excerpt = strip_html(post.get("excerpt", {}).get("rendered", ""))
    if len(excerpt) > 280: excerpt = excerpt[:279].rstrip() + "…"
    link = post["link"]
    img  = featured_url(post)
    cap = (f"📰 <b>Bài mới trên web</b>\n\n"
           f"<b>{html.escape(title)}</b>\n"
           f"{html.escape(excerpt)}\n\n"
           f"🔗 {html.escape(link)}")
    try:
        if img:
            r = requests.post(f"{TG}/sendPhoto", data={
                "chat_id": CHAT, "photo": img,
                "caption": cap[:1024], "parse_mode": "HTML"}, timeout=40)
            if r.json().get("ok"):
                return True
            log("sendPhoto fail -> fallback text:", r.text[:200])
        r = requests.post(f"{TG}/sendMessage", data={
            "chat_id": CHAT, "text": cap[:4096], "parse_mode": "HTML",
            "disable_web_page_preview": "false"}, timeout=40)
        ok = r.json().get("ok")
        if not ok: log("sendMessage fail:", r.text[:300])
        return bool(ok)
    except Exception as e:
        log("tg_send error:", e); return False

def main():
    ping_wpcron()
    time.sleep(3)  # cho wp-cron kịp flip future->publish
    state = load_state()
    try:
        posts = fetch_recent()
    except Exception as e:
        log("fetch error:", e); sys.exit(0)  # thất bại tạm thời -> im lặng, lần sau thử lại
    posts = sorted(posts, key=lambda p: p["id"])  # cũ -> mới
    ids_now = [p["id"] for p in posts]

    if not state["initialized"]:
        state["sent_ids"] = ids_now
        state["initialized"] = True
        save_state(state)
        log(f"Baseline: {len(ids_now)} bài coi như đã gửi. Không spam kho cũ.")
        return

    sent = set(state["sent_ids"])
    new_posts = [p for p in posts if p["id"] not in sent]
    if not new_posts:
        log("Không có bài mới."); return
    log(f"{len(new_posts)} bài mới -> gửi Telegram")
    for p in new_posts:
        if tg_send(p):
            state["sent_ids"].append(p["id"])
            log("  đã gửi:", p["id"], strip_html(p["title"]["rendered"])[:60])
            time.sleep(1.5)
    save_state(state)

if __name__ == "__main__":
    main()
