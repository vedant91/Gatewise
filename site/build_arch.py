"""Build the Gatewise architecture diagram (version 2: workflow, sandbox containerisation, memory, roadmap).
Writes site/assets/architecture.svg (self-contained, logos embedded), site/assets/architecture.png and architecture-dark.png,
site/architecture.html (a standalone page) and refreshes the inline copy inside site/index.html (between the ARCH markers).
Solid boxes are built today. Dashed boxes are planned.
Run:  python site/build_arch.py"""
import base64, html, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
LOGOS = os.path.join(HERE, "assets", "logos")
esc = html.escape


def uri(key):
    p = os.path.join(LOGOS, key + ".svg")
    if not os.path.exists(p):
        return None
    return "data:image/svg+xml;base64," + base64.b64encode(open(p, "rb").read()).decode()


def rect(x, y, w, h, cls, r=16):
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>'


def text(x, y, s, cls="t", anchor="start"):
    return f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(s)}</text>'


def logo(key, x, y, s=30):
    u = uri(key)
    return f'<image href="{u}" x="{x}" y="{y}" width="{s}" height="{s}"/>' if u else ""


def chip(x, y, w, h, label, key=None, big=None, sub=None, nxt=False):
    """A white badge so brand logos stay legible in light and dark mode."""
    cx = x + w / 2
    out = [rect(x, y, w, h, "chip next" if nxt else "chip", 12)]
    if key and uri(key):
        out += [logo(key, cx - 16, y + 16, 32), text(cx, y + h - 16, label, "chiptxt", "middle")]
    elif big:
        out += [text(cx, y + 52, big, "chipbig", "middle"), text(cx, y + h - 16, label, "chiptxt", "middle")]
    else:
        out.append(text(cx, y + h / 2 + (0 if not sub else -6), label, "chiptxt b", "middle"))
        if sub:
            out.append(text(cx, y + h / 2 + 16, sub, "chipsub", "middle"))
    return "".join(out)


def rchip(x, y, w, h, title, sub, key=None):
    """A planned item: dashed, with an optional logo on the left and two short lines."""
    out = [rect(x, y, w, h, "chip next", 12)]
    tx = x + 16
    if key and uri(key):
        out.append(logo(key, x + 14, y + h / 2 - 15, 30))
        tx = x + 54
    return "".join(out) + text(tx, y + h / 2 - 3, title, "chiptxt b") + text(tx, y + h / 2 + 18, sub, "chipsub")


def tag(x, y, kind):
    label, w = ("Today", 64) if kind == "today" else ("Next", 54)
    return rect(x, y, w, 24, "tag " + kind, 12) + text(x + w / 2, y + 17, label, "tagtxt " + kind, "middle")


def badge(cx, cy, n):
    return f'<circle class="badge" cx="{cx}" cy="{cy}" r="14"/>' + text(cx, cy + 5, str(n), "badgetxt", "middle")


def line(pts, both=False):
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    ms = ' marker-start="url(#ah)"' if both else ""
    return f'<path class="wire" d="{d}" marker-end="url(#ah)"{ms}/>'


def pill(cx, cy, label, w=64):
    return rect(cx - w / 2, cy - 14, w, 28, "pill", 14) + text(cx, cy + 5, label, "pilltxt", "middle")


def build():
    o = []
    # ====================================================== column A: you and your AI
    o.append(rect(30, 70, 250, 570, "card"))
    o += [text(52, 108, "Your AI client", "h"), text(52, 132, "Brings its own model and key", "s")]
    o += [chip(46, 160, 110, 100, "Claude Code", "claude"), chip(164, 160, 110, 100, "Cursor", "cursor"),
          chip(46, 274, 110, 100, "Codex", sub="OpenAI"), chip(164, 274, 110, 100, "Claude Desktop", "anthropic")]
    o.append(rect(46, 396, 228, 120, "say", 14))
    o += [text(60, 430, "“I am making the", "q"), text(60, 452, "sandbox...”", "q"),
          text(60, 486, "Every step explained", "s2"), text(60, 504, "in plain words", "s2")]
    o.append(rect(46, 532, 228, 92, "say", 14))
    o += [text(60, 564, "“Rejected. It would lock", "q"), text(60, 586, "out legitimate users.”", "q"), text(60, 612, "Your AI relays the verdict", "s2")]

    # ====================================================== column B: the MCP server
    o.append(rect(350, 70, 470, 570, "card hero"))
    o += [rect(366, 86, 40, 40, "chip", 8), logo("modelcontextprotocol", 370, 90, 32), text(416, 114, "Gatewise MCP server", "h"),
          logo("python", 770, 90, 30), text(374, 150, "Runs on your machine. No model inside.", "s")]
    tools = [("gatewise_sandbox", "start, reset"), ("gatewise_investigate", "scan, locate, explain"), ("gatewise_prove", "before, after"),
             ("gatewise_fix", "plan, verify, court"), ("gatewise_deliver", "pull_request, report")]
    for i, (n, a) in enumerate(tools):
        y = 172 + i * 80
        o += [rect(374, y, 422, 66, "tool", 12), text(394, y + 29, n, "mono b"), text(394, y + 51, a, "mono2")]
    o += [rect(374, 586, 422, 44, "engine", 12), text(585, 614, "Engine: scan, locate, verify, court, passport", "mono2 c", "middle")]

    # ====================================================== column C: the sandbox
    o.append(rect(870, 70, 700, 570, "card"))
    o += [rect(894, 86, 40, 40, "chip", 8), logo("docker", 898, 90, 32), text(944, 114, "Sandbox", "h"),
          text(894, 148, "Where the app is attacked and the fix is judged", "s")]
    o += [rect(894, 164, 652, 156, "zone", 14), tag(912, 152, "today")]
    o += [chip(914, 186, 112, 100, "FastAPI", "fastapi"), chip(1038, 186, 112, 100, "SQLite", "sqlite"),
          chip(1162, 186, 112, 100, "Chrome", "googlechrome"), chip(1286, 186, 112, 100, "pytest", "pytest"),
          text(1418, 220, "Temp copy,", "s"), text(1418, 242, "localhost only,", "s"), text(1418, 264, "fake data", "s")]
    o += [rect(894, 340, 652, 284, "zone next", 14), tag(912, 328, "next"), text(918, 378, "One Docker container per run", "h")]
    for i, (name, keys, cap) in enumerate([("App container", ("fastapi", "sqlite"), "your app copy"),
                                           ("Browser container", ("googlechrome",), "Playwright replays leaks"),
                                           ("Judge container", ("pytest",), "7 gates and the Court")]):
        x = 914 + i * 208
        cx = x + 98
        o += [rect(x, 396, 196, 130, "cbox", 12), text(cx, 422, name, "chiptxt b", "middle")]
        if len(keys) == 2:
            o += [logo(keys[0], cx - 36, 438, 30), logo(keys[1], cx + 6, 438, 30)]
        else:
            o.append(logo(keys[0], cx - 15, 438, 30))
        o.append(text(cx, 502, cap, "chipsub", "middle"))
    for x, w, label in [(914, 130, "network off"), (1054, 150, "read-only disk"), (1214, 196, "CPU and memory caps"), (1420, 106, "one per run")]:
        o += [rect(x, 544, w, 44, "chip next", 12), text(x + w / 2, 572, label, "chiptxt", "middle")]

    # ====================================================== row 2
    o.append(rect(30, 700, 250, 300, "card accent"))
    o += ['<circle class="person" cx="155" cy="764" r="17"/>', '<path class="person" d="M121 818 C121 792 189 792 189 818 L189 828 L121 828 Z"/>',
          text(155, 866, "You", "h", "middle"), text(155, 892, "Review, then click Merge", "s", "middle")]
    o.append(rect(350, 700, 470, 300, "card"))
    o += [text(374, 738, "Proof you can check", "h"), chip(374, 762, 134, 110, "Passport", sub="signed"), chip(518, 762, 134, 110, "Report", sub="before and after"),
          chip(662, 762, 134, 110, "Event log", sub="every step")]
    o += [rect(374, 892, 422, 92, "zone next", 14), tag(392, 880, "next"), text(396, 930, "Transparency log", "chiptxt b"), text(396, 952, "A public record of every passport", "chipsub")]
    o.append(rect(870, 700, 340, 300, "card"))
    o += [rect(894, 716, 38, 38, "chip", 8), logo("github", 898, 720, 30), text(944, 742, "GitHub pull request", "h"),
          chip(894, 770, 140, 110, "Branch", "git"), chip(1048, 770, 140, 110, "Pull request", "github"), text(894, 898, "One commit per fix", "s")]
    o += [rect(894, 920, 292, 64, "zone next", 14), tag(908, 908, "next"), logo("githubactions", 910, 936, 26), text(948, 954, "CI release gate", "chiptxt b"), text(948, 974, "Blocks the merge on a leak", "chipsub")]
    o.append(rect(1230, 700, 340, 300, "card"))
    o += [text(1254, 738, "Memory", "h"), tag(1486, 722, "today"), text(1254, 762, "The authorization graph", "s")]
    users = [(1290, 788), (1290, 822), (1290, 856)]
    items = [(1500, 788), (1500, 822), (1500, 856)]
    for (a, b, leak) in [(0, 0, 0), (0, 1, 1), (1, 1, 0), (1, 2, 0), (2, 0, 1), (2, 2, 0)]:
        o.append(f'<path class="edge{" leak" if leak else ""}" d="M{users[a][0]} {users[a][1]} L{items[b][0]} {items[b][1]}"/>')
    o += [f'<circle class="nu" cx="{x}" cy="{y}" r="10"/>' for x, y in users]
    o += [f'<rect class="ni" x="{x - 10}" y="{y - 10}" width="20" height="20" rx="4"/>' for x, y in items]
    o += [text(1290, 882, "users", "s2", "middle"), text(1500, 882, "items and doors", "s2", "middle")]
    o += [rect(1254, 910, 292, 78, "zone next", 14), tag(1268, 898, "next"), logo("neo4j", 1270, 934, 28), text(1310, 944, "Graph database", "chiptxt b"),
          text(1310, 966, "Learns, seeds the next scan", "chipsub")]

    # ====================================================== roadmap
    o.append(rect(30, 1100, 1540, 170, "card next"))
    o += [text(54, 1142, "Planned next", "h"), rect(1288, 1124, 28, 18, "zone", 4), text(1324, 1139, "Built today", "s"),
          rect(1440, 1124, 28, 18, "zone next", 4), text(1476, 1139, "Planned", "s")]
    plan = [("Policy as code", "OPA, Cedar", None), ("OpenAPI discovery", "routes and roles", None), ("More stacks", "Node, Django", "nodedotjs"),
            ("Multi-agent Court", "specialist attackers", None), ("Cloud sandboxes", "ephemeral, per pull request", "docker"), ("Team dashboard", "runs across repos", None)]
    for i, (t, sub, key) in enumerate(plan):
        o.append(rchip(54 + i * 244, 1170, 232, 76, t, sub, key))

    # ====================================================== wires and workflow numbers
    o += [line([(155, 700), (155, 640)]), pill(155, 670, "you ask", 84), badge(98, 670, 1)]
    o += [line([(280, 300), (350, 300)], both=True), pill(315, 270, "MCP", 54), badge(315, 330, 2)]
    for n, y in zip((3, 4, 5, 6), (205, 285, 365, 445)):
        o += [line([(820, y), (870, y)]), badge(845, y - 22, n)]
    o += [line([(585, 640), (585, 700)]), badge(622, 670, 7), line([(820, 850), (870, 850)])]
    o += [line([(1400, 640), (1400, 700)]), pill(1400, 670, "learns", 70)]
    o += [line([(1040, 1000), (1040, 1044), (155, 1044), (155, 1002)]), pill(600, 1044, "the merge link", 150), badge(500, 1044, 8)]

    defs = '<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="ahead"/></marker></defs>'
    style = """<style>
.arch{--surface:#fff;--sunken:#f5f6f9;--line:#dfe3ec;--ink:#0d1117;--mut:#566073;--accent:#2447f5;--soft:#e7ebff;--bg:#fff}
@media (prefers-color-scheme:dark){.arch{--surface:#10141b;--sunken:#0d1015;--line:#222836;--ink:#eef1f7;--mut:#939db0;--accent:#8aa0ff;--soft:#161e3d;--bg:#090b0f}}
.arch.dark{--surface:#10141b;--sunken:#0d1015;--line:#222836;--ink:#eef1f7;--mut:#939db0;--accent:#8aa0ff;--soft:#161e3d;--bg:#090b0f}
.arch text{font-family:"Hanken Grotesk","Segoe UI",system-ui,sans-serif;fill:var(--ink)}
.arch .card{fill:var(--surface);stroke:var(--line);stroke-width:1.5}.arch .card.hero{stroke:var(--accent);stroke-width:2}.arch .card.accent{fill:var(--soft);stroke:none}
.arch .card.next,.arch .zone.next,.arch .cbox{fill:none;stroke:var(--accent);stroke-width:1.5;stroke-dasharray:8 6}.arch .cbox{fill:var(--surface);stroke-dasharray:6 5}
.arch .zone{fill:none;stroke:var(--line);stroke-width:1.5}
.arch .tool{fill:var(--sunken)}.arch .engine{fill:var(--soft)}.arch .say{fill:var(--soft)}
.arch .chip{fill:#fff;stroke:#dfe3ec;stroke-width:1.5}.arch .chip.next{stroke:var(--accent);stroke-dasharray:5 4}
.arch text.chiptxt{fill:#0d1117;font-size:14px;font-weight:600}.arch text.chiptxt.b{font-size:15px;font-weight:700}
.arch text.chipsub{fill:#566073;font-size:13px}.arch text.chipbig{fill:#2447f5;font-size:40px;font-weight:700}
.arch .card.next text.chiptxt,.arch .zone.next ~ text.chiptxt{fill:#0d1117}
.arch text.h{font-size:19px;font-weight:700}.arch text.s{font-size:14px;fill:var(--mut)}.arch text.s2{font-size:13px;fill:var(--mut)}.arch text.q{font-size:16px;font-weight:600}
.arch text.mono{font-family:"JetBrains Mono",Consolas,monospace;font-size:15px}.arch text.mono2{font-family:"JetBrains Mono",Consolas,monospace;font-size:13px;fill:var(--mut)}
.arch text.b{font-weight:700}.arch text.c{fill:var(--ink)}
.arch .wire{fill:none;stroke:var(--mut);stroke-width:2;stroke-linejoin:round}.arch .ahead{fill:var(--mut)}
.arch .pill{fill:var(--accent)}.arch text.pilltxt{fill:#fff;font-size:13px;font-weight:600}
.arch .badge{fill:var(--ink)}.arch text.badgetxt{fill:var(--bg);font-size:14px;font-weight:700}
.arch .tag.today{fill:var(--accent)}.arch text.tagtxt.today{fill:#fff;font-size:13px;font-weight:700}
.arch .tag.next{fill:var(--bg);stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3}.arch text.tagtxt.next{fill:var(--accent);font-size:13px;font-weight:700}
.arch .person{fill:var(--accent)}
.arch .nu{fill:var(--accent)}.arch .ni{fill:var(--mut)}.arch .edge{stroke:var(--line);stroke-width:2.5}.arch .edge.leak{stroke:#d92d20;stroke-dasharray:5 4}
</style>"""
    return ('<svg class="arch" xmlns="http://www.w3.org/2000/svg" viewBox="0 40 1600 1240" role="img" '
            'aria-label="Architecture and workflow: you ask your AI client, which calls the five tools of the Gatewise MCP server. The server drives a sandbox today a local process and next a Docker container per run, '
            'a real browser and a judge, remembers what it learns in an authorization graph, signs a passport, opens a GitHub pull request, and you click Merge. Planned items are dashed.">'
            + style + defs + "".join(o) + "</svg>")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">
<title>Gatewise architecture</title>
<style>
@font-face{font-family:"Bricolage Grotesque";src:url(assets/fonts/bricolage.woff2) format("woff2");font-weight:500 800;font-display:swap}
@font-face{font-family:"Hanken Grotesk";src:url(assets/fonts/hanken.woff2) format("woff2");font-weight:400 700;font-display:swap}
@font-face{font-family:"JetBrains Mono";src:url(assets/fonts/jbmono.woff2) format("woff2");font-weight:400 600;font-display:swap}
:root{--bg:#fff;--ink:#0d1117;--mut:#566073;--line:#dfe3ec;--sunken:#f5f6f9}
@media (prefers-color-scheme:dark){:root{--bg:#090b0f;--ink:#eef1f7;--mut:#939db0;--line:#222836;--sunken:#0d1015}}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 "Hanken Grotesk","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:48px 28px 64px}
h1{font:700 clamp(2rem,4vw,3.2rem)/1.12 "Bricolage Grotesque","Segoe UI",system-ui,sans-serif;letter-spacing:-.03em;margin:0 0 10px}
p.lead{color:var(--mut);margin:0 0 26px;max-width:64ch}
.tags{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 28px}.tags span{padding:9px 16px;border:1px solid var(--line);border-radius:10px;font-weight:600;font-size:.92rem;background:var(--sunken)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:14px;padding:12px}
.scroll svg{display:block;min-width:1100px;width:100%;height:auto}
a{color:inherit}
</style></head><body><div class="wrap">
<h1>How Gatewise works</h1>
<p class="lead">You ask your AI. It calls five tools, numbered 3 to 7 below. Solid boxes are built today. Dashed boxes are what we plan to build next.</p>
<div class="tags"><span>Sandbox only</span><span>No model inside</span><span>A human merges</span></div>
<div class="scroll">__SVG__</div>
<p style="margin-top:22px"><a href="index.html">Back to the site</a></p>
</div></body></html>"""


def export_png(svg):
    """Light and dark PNGs at 2x, straight from the page, so the logos and fonts render exactly as on screen."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed, skipped PNG export")
        return
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name, mode in (("architecture.png", "light"), ("architecture-dark.png", "dark")):
            ctx = b.new_context(viewport={"width": 1700, "height": 1400}, device_scale_factor=2, color_scheme=mode)
            pg = ctx.new_page()
            pg.goto("file:///" + os.path.join(HERE, "architecture.html").replace("\\", "/"))
            pg.add_style_tag(content=".scroll{border:0;padding:0}.wrap{padding:0}h1,p.lead,.tags,a,p[style]{display:none}.scroll svg{min-width:0}body{background:" + ("#fff" if mode == "light" else "#090b0f") + "}")
            pg.wait_for_timeout(700)
            pg.locator("svg.arch").screenshot(path=os.path.join(HERE, "assets", name))
            ctx.close()
        b.close()
    print("exported assets/architecture.png and architecture-dark.png")


def main():
    svg = build()
    with open(os.path.join(HERE, "assets", "architecture.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    with open(os.path.join(HERE, "architecture.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__SVG__", svg))
    p = os.path.join(HERE, "index.html")
    s = open(p, encoding="utf-8").read()
    block = '<!--ARCH--><div class="archwrap reveal"><div class="archscroll">' + svg + '</div></div><!--/ARCH-->'
    if "<!--ARCH-->" in s:
        s = re.sub(r"<!--ARCH-->.*?<!--/ARCH-->", lambda m: block, s, flags=re.S)
    else:
        a = s.index('<div class="flow reveal">')
        b = s.index("</p>", s.index('<p class="flownote reveal">')) + 4
        s = s[:a] + block + s[b:]
    if ".archwrap" not in s:
        s = s.replace(".reveal{opacity:0;transform:translateY(16px)", ".archwrap{margin-top:40px}.archscroll{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r);background:var(--surface);padding:12px}.archscroll svg{display:block;min-width:1100px;width:100%;height:auto}\n.reveal{opacity:0;transform:translateY(16px)", 1)
    else:
        s = s.replace(".archscroll svg{display:block;min-width:960px;", ".archscroll svg{display:block;min-width:1100px;")
    open(p, "w", encoding="utf-8").write(s)
    print("architecture built:", len(svg), "bytes of svg")
    export_png(svg)


if __name__ == "__main__":
    main()
