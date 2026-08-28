#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indexer bot — Nhậu Phi Trường (chạy hàng ngày).
  1) Đọc sitemap (Rank Math) -> gom toàn bộ URL + lastmod.
  2) Chọn URL mới/ vừa sửa trong N ngày gần đây (+ trang chủ) để ép index.
  3) Nếu có GOOGLE_SA_JSON  -> gửi Google Indexing API (ép Google).
     Nếu có INDEXNOW_KEY    -> gửi IndexNow (Bing/Yandex/Cốc Cốc).
  4) Báo tóm tắt về nhóm Telegram.
Không có secret nào của Google/IndexNow thì vẫn báo cáo sitemap + hướng dẫn bật.
"""
import os, json, time, html, datetime as dt
import xml.etree.ElementTree as ET
import requests

SITE   = os.environ.get("SITE", "https://nhauphitruong.com").rstrip("/")
TOKEN  = os.environ["TELEGRAM_TOKEN"]
CHAT   = os.environ["TELEGRAM_CHAT_ID"]
SA_RAW = os.environ.get("GOOGLE_SA_JSON", "").strip()
IN_KEY = os.environ.get("INDEXNOW_KEY", "").strip()
DAYS   = int(os.environ.get("INDEX_DAYS", "3"))
MAXG   = int(os.environ.get("GOOGLE_MAX", "180"))  # quota mặc định Google ~200/ngày
UA     = "Mozilla/5.0 (compatible; NPT-Indexer/1.0)"
TG     = f"https://api.telegram.org/bot{TOKEN}"
NS     = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

def log(*a): print(*a, flush=True)

def get(url):
    return requests.get(url, headers={"User-Agent": UA}, timeout=40)

def parse_sitemap(url, out, depth=0):
    """Đệ quy: sitemap index -> các sitemap con -> url."""
    try:
        r = get(url)
        if r.status_code != 200: return
        root = ET.fromstring(r.content)
    except Exception as e:
        log("sitemap err", url, e); return
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex" and depth < 3:
        for sm in root.findall(f"{NS}sitemap"):
            loc = sm.findtext(f"{NS}loc")
            if loc: parse_sitemap(loc, out, depth+1)
    else:  # urlset
        for u in root.findall(f"{NS}url"):
            loc = u.findtext(f"{NS}loc")
            lastmod = u.findtext(f"{NS}lastmod")
            if loc: out[loc] = lastmod

def recent_urls(all_urls, days):
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    picked = []
    for loc, lastmod in all_urls.items():
        if not lastmod:
            continue
        try:
            d = dt.datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
            if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
            if d >= cutoff:
                picked.append(loc)
        except Exception:
            continue
    home = SITE + "/"
    if home not in picked: picked.append(home)
    return picked

def google_index(urls):
    if not SA_RAW: return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        info = json.loads(SA_RAW)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/indexing"])
        sess = AuthorizedSession(creds)
    except Exception as e:
        log("Google auth fail:", e); return {"ok": 0, "fail": 0, "err": str(e)}
    ok = fail = 0
    for u in urls[:MAXG]:
        try:
            r = sess.post("https://indexing.googleapis.com/v3/urlNotifications:publish",
                          json={"url": u, "type": "URL_UPDATED"}, timeout=30)
            if r.status_code == 200: ok += 1
            else: fail += 1; log("G fail", r.status_code, u, r.text[:120])
            time.sleep(0.2)
        except Exception as e:
            fail += 1; log("G exc", u, e)
    return {"ok": ok, "fail": fail}

def indexnow(urls):
    if not IN_KEY: return None
    host = SITE.split("//")[-1]
    payload = {"host": host, "key": IN_KEY,
               "keyLocation": f"{SITE}/{IN_KEY}.txt",
               "urlList": urls[:10000]}
    try:
        r = requests.post("https://api.indexnow.org/indexnow",
                          json=payload, headers={"Content-Type": "application/json; charset=utf-8"},
                          timeout=40)
        return {"status": r.status_code, "count": len(payload["urlList"])}
    except Exception as e:
        log("indexnow err", e); return {"status": "err", "count": 0}

def tg(msg):
    try:
        requests.post(f"{TG}/sendMessage", data={
            "chat_id": CHAT, "text": msg, "parse_mode": "HTML",
            "disable_web_page_preview": "true"}, timeout=40)
    except Exception as e:
        log("tg err", e)

def main():
    all_urls = {}
    parse_sitemap(f"{SITE}/sitemap_index.xml", all_urls)
    if not all_urls:
        parse_sitemap(f"{SITE}/wp-sitemap.xml", all_urls)
    total = len(all_urls)
    urls = recent_urls(all_urls, DAYS)
    log(f"sitemap tổng {total} URL, mới/sửa trong {DAYS} ngày: {len(urls)}")

    g = google_index(urls)
    ix = indexnow(urls)

    today = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=7)
    lines = [f"🔎 <b>Ép index hàng ngày</b> — {today:%d/%m/%Y}",
             f"Sitemap: <b>{total}</b> URL · cần đẩy (mới/sửa {DAYS} ngày): <b>{len(urls)}</b>"]
    if g is None:
        lines.append("• Google Indexing API: <i>chưa bật</i> (thêm secret GOOGLE_SA_JSON)")
    elif "err" in g:
        lines.append(f"• Google: ❌ lỗi xác thực ({html.escape(g['err'][:80])})")
    else:
        lines.append(f"• Google: ✅ {g['ok']} URL"+(f" · lỗi {g['fail']}" if g['fail'] else ""))
    if ix is None:
        lines.append("• IndexNow: <i>chưa bật</i> (thêm secret INDEXNOW_KEY)")
    else:
        lines.append(f"• IndexNow (Bing/Cốc Cốc): {ix['count']} URL · HTTP {ix['status']}")
    tg("\n".join(lines))
    log("done")

if __name__ == "__main__":
    main()
