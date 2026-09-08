import os, requests
from fastmcp import FastMCP

mcp = FastMCP("gymmaster")
SITE = "caveathletics"
KEY = os.environ["GYMMASTER_KEY"]
BASE = f"https://{SITE}.gymmasteronline.com/gatekeeper_api/v2"

@mcp.tool()
def get_debtors() -> str:
    r = requests.get(f"{BASE}/members", auth=(SITE, KEY), timeout=30)
    r.raise_for_status()
    owing = ) if float(m.get("owe", {}).get("__decimal__", 0)) > 0 f"{m.get('name')} owes ${m.get('owe', {}).get('__decimal__')}" for m in owing]
    return "\n".join(lines) or "No one owing."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
