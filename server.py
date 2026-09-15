import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("gymmaster")

SITE = "caveathletics"
KEY = os.environ["GYMMASTER_KEY"]
PORTAL_KEY = os.environ.get("PORTAL_KEY", "")
BASE = "https://" + SITE + ".gymmasteronline.com/gatekeeper_api/v2"
PORTAL = "https://" + SITE + ".gymmasteronline.com/portal/api/v1/members"


def owe_amount(member):
    owe = member.get("owe") or {}
    try:
        return float(owe.get("__decimal__", 0) or 0)
    except Exception:
        return 0.0


def load_gatekeeper_members():
    members = []
    last_id = None
    for _ in range(20):
        url = BASE + "/members"
        if last_id is not None:
            url = url + "?last_id=" + str(last_id)
        r = requests.get(url, auth=(SITE, KEY), timeout=60)
        r.raise_for_status()
        data = r.json()
        batch = data.get("members") or []
        if not batch:
            break
        members.extend(batch)
        if not data.get("hasmore"):
            break
        last_id = batch[-1].get("memberid") or batch[-1].get("id")
        if last_id is None:
            break
    return members


def load_portal_phones():
    phones = {}
    status = "portal key not set"
    if not PORTAL_KEY:
        return phones, status
    try:
        r = requests.get(PORTAL, params={"api_key": PORTAL_KEY}, timeout=90)
        raw = r.text[:200].replace("\n", " ")
        if r.status_code != 200:
            return phones, "HTTP " + str(r.status_code) + " " + raw
        data = r.json()
        err = data.get("error")
        if err:
            return phones, "portal error: " + str(err)
        rows = data.get("result")
        if rows is None:
            rows = data if isinstance(data, list) else []
        if not isinstance(rows, list):
            return phones, "unexpected json keys: " + ",".join(list(data.keys())[:8])
        with_phone = 0
        for row in rows:
            mid = row.get("id")
            if mid is None:
                continue
            cell = str(row.get("phonecell") or "").strip()
            home = str(row.get("phonehome") or "").strip()
            phone = cell or home
            if phone:
                phones[int(mid)] = phone
                with_phone += 1
            else:
                phones[int(mid)] = "no phone"
        status = "ok rows=" + str(len(rows)) + " with_phone=" + str(with_phone)
    except Exception as e:
        status = "exception: " + type(e).__name__ + " " + str(e)[:120]
    return phones, status


@mcp.tool()
def get_debtors() -> str:
    members = load_gatekeeper_members()
    phones, portal_status = load_portal_phones()
    lines = ["portal: " + portal_status]
    lines.append("name | ID | owing | phone")
    count = 0
    for m in members:
        amount = owe_amount(m)
        if amount <= 0:
            continue
        mid = m.get("memberid") or m.get("id") or "?"
        name = m.get("name") or "Unknown"
        if str(mid).isdigit() and int(mid) in phones:
            phone = phones[int(mid)]
        else:
            phone = "no phone"
        lines.append(name + " | ID " + str(mid) + " | $" + str(amount) + " | " + phone)
        count += 1
    if count == 0:
        return "portal: " + portal_status + "\nNo one owing."
    return "\n".join(lines)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
