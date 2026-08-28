#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indexer bot — Nhậu Phi Trường (chạy hàng ngày). Mẫu báo cáo giống bot Tuấn Tú.
  1) Đọc sitemap (Rank Math) -> gom toàn bộ URL.
  2) URL Inspection API kiểm tra TỪNG URL: đã index / chưa index / lỗi.
  3) Ép index lại (Indexing API) các URL CHƯA index.
  4) Báo cáo về nhóm Telegram: đã/chưa/lỗi + danh sách URL chưa index + coverageState.
Cần secret GOOGLE_SA_JSON (SA là Chủ sở hữu property URL-prefix trong Search Console).
"""
import os, json, time, html, datetime as dt
import xml.etree.ElementTree as ET
import requests

SITE     = os.environ.get("SITE", "https://nhauphitruong.com").rstrip("/")
SITE_URL = os.environ.get("SC_SITE_URL", SITE + "/")   # property URL-prefix SA sở hữu
TOKEN    = os.environ["TELEGRAM_TOKEN"]
CHAT     = os.environ["TELEGRAM_CHAT_ID"]
SA_RAW   = os.environ.get("GOOGLE_SA_JSON", "").strip()
MAX_INSPECT = int(os.environ.get("MAX_INSPECT", "180"))  # quota URL Inspection ~2000/ngày
MAX_PUSH    = int(os.environ.get("MAX_PUSH", "180"))     # quota Indexing ~200/ngày
UA  = "Mozilla/5.0 (compatible; NPT-Indexer/2.0)"
TG  = f"https://api.telegram.org/bot{TOKEN}"
NS  = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
SCOPES = ["https://www.googleapis.com/auth/indexing",
          "https://www.googleapis.com/auth/webmasters.readonly"]

def log(*a): print(*a, flush=True)

def get(url):
    return requests.get(url, headers={"User-Agent": UA}, timeout=40)

def parse_sitemap(url, out, depth=0):
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
    else:
        for u in root.findall(f"{NS}url"):
            loc = u.findtext(f"{NS}loc")
            if loc: out.append(loc)

def make_session():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = json.loads(SA_RAW)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return AuthorizedSession(creds)

# nhãn coverageState tiếng Việt gọn
COV_VI = {
    "Submitted and indexed": "Đã gửi & đã index",
    "Indexed, not submitted in sitemap": "Đã index (ngoài sitemap)",
    "Discovered - currently not indexed": "Đã phát hiện, chưa index",
    "Crawled - currently not indexed": "Đã thu thập, chưa index",
    "URL is unknown to Google": "Google chưa biết URL",
    "Page with redirect": "Trang chuyển hướng",
    "Duplicate without user-selected canonical": "Trùng lặp, chưa chọn canonical",
    "Excluded by 'noindex' tag": "Bị chặn bởi thẻ noindex",
}

def inspect(sess, url):
    """Trả (state, cov) — state: indexed|not|error ; cov: coverageState gốc."""
    try:
        r = sess.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                      json={"inspectionUrl": url, "siteUrl": SITE_URL}, timeout=40)
        if r.status_code != 200:
            log("inspect", r.status_code, url, r.text[:120]); return ("error", f"HTTP {r.status_code}")
        idx = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
        verdict = idx.get("verdict", "")            # PASS / NEUTRAL / FAIL / VERDICT_UNSPECIFIED
        cov = idx.get("coverageState", "Unknown")
        if verdict == "PASS":
            return ("indexed", cov)
        return ("not", cov)
    except Exception as e:
        log("inspect exc", url, e); return ("error", str(e)[:60])

def push(sess, url):
    try:
        r = sess.post("https://indexing.googleapis.com/v3/urlNotifications:publish",
                      json={"url": url, "type": "URL_UPDATED"}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        log("push exc", url, e); return False

def tg(msg):
    try:
        requests.post(f"{TG}/sendMessage", data={
            "chat_id": CHAT, "text": msg, "parse_mode": "HTML",
            "disable_web_page_preview": "true"}, timeout=40)
    except Exception as e:
        log("tg err", e)

def main():
    urls = []
    parse_sitemap(f"{SITE}/sitemap_index.xml", urls)
    if not urls:
        parse_sitemap(f"{SITE}/wp-sitemap.xml", urls)
    urls = list(dict.fromkeys(urls))  # unique giữ thứ tự
    total = len(urls)
    host = SITE.split("//")[-1]
    today = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=7)

    if not SA_RAW:
        tg(f"🔎 <b>Báo cáo Index</b> — {today:%d/%m/%Y}\n🌐 {host}\n"
           f"⚠️ Chưa cấu hình Google (thiếu GOOGLE_SA_JSON) — sitemap {total} URL.")
        return

    sess = make_session()

    indexed = notidx = errcnt = 0
    not_list = []  # (url, cov)
    for u in urls[:MAX_INSPECT]:
        state, cov = inspect(sess, u)
        if state == "indexed": indexed += 1
        elif state == "not":
            notidx += 1; not_list.append((u, cov))
        else: errcnt += 1
        time.sleep(0.25)  # tôn trọng 600 req/phút

    # ép index lại các URL chưa index
    pushed = 0
    for u, _ in not_list[:MAX_PUSH]:
        if push(sess, u): pushed += 1
        time.sleep(0.2)

    inspected = min(total, MAX_INSPECT)
    lines = [f"📊 <b>Báo cáo Index</b> — {today:%d/%m/%Y}",
             f"🌐 {host}",
             f"✅ Đã index: <b>{indexed}</b>/{inspected}",
             f"🟡 Chưa index: <b>{notidx}</b>",
             f"🔴 Lỗi/Unknown: <b>{errcnt}</b>",
             f"🚀 Vừa ép index lại: <b>{pushed}</b>"]
    if total > MAX_INSPECT:
        lines.append(f"ℹ️ Kiểm tra {MAX_INSPECT}/{total} URL (giới hạn quota/ngày)")

    if not_list:
        lines.append("\n<b>Một số URL chưa index:</b>")
        for u, cov in not_list[:10]:
            covvi = COV_VI.get(cov, cov)
            lines.append(f"• {html.escape(u)} — <i>{html.escape(covvi)}</i>")
        if len(not_list) > 10:
            lines.append(f"… và {len(not_list)-10} URL khác")
    else:
        lines.append("\n🎉 Tất cả URL đã được index.")

    tg("\n".join(lines))
    log(f"done: indexed={indexed} not={notidx} err={errcnt} pushed={pushed}")

if __name__ == "__main__":
    main()
