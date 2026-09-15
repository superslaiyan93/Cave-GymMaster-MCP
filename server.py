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
        r = requests.get(url, auth=(SITE, KEY), timeout=30)
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
    if not PORTAL_KEY:
        return phones
    try:
        r = requests.get(PORTAL, params={"api_key": PORTAL_KEY}, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows = data.get("result")
        if rows is None:
            rows = data if isinstance(data, list) else []
        for row in rows:
            mid = row.get("id")
            if mid is None:
                continue
            cell = (row.get("phonecell") or "").strip()
            home = (row.get("phonehome") or "").strip()
            phones[int(mid)] = cell or home or "no phone"
    except Exception:
        return phones
    return phones


@mcp.tool()
def get_debtors() -> str:
    members = load_gatekeeper_members()
    phones = load_portal_phones()
    lines = []
    for m in members:
        amount = owe_amount(m)
        if amount <= 0:
            continue
        mid = m.get("memberid") or m.get("id") or "?"
        name = m.get("name") or "Unknown"
        phone = phones.get(int(mid) if str(mid).isdigit() else -1, "no phone")
        if not PORTAL_KEY:
            phone = "portal key not set"
        line = name + " | ID " + str(mid) + " | $" + str(amount) + " | " + phone
        lines.append(line)
    if not lines:
        return "No one owing."
    header = "name | ID | owing | phone"
    return header + "\n" + "\n".join(lines)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
