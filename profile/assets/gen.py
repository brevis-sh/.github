"""Generates the org profile's SVGs with every glyph as a path.

GitHub serves README images through a proxy and inside <img>, where an SVG
cannot load a web font. Text as paths renders the same in every browser,
in both GitHub themes, without a font on the viewer's machine.
"""
import os
import re
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
# IBM Plex, the TrueType folder of github.com/IBM/plex's release zip.
FONTS = Path(os.environ.get("PLEX_DIR", HERE / "plex" / "TrueType"))
# The site's icon sprite, from a checkout of brevis-sh/brevis.
ICONS = Path(os.environ.get("BREVIS_REPO", HERE.parents[2] / "brevis")) / "site" / "assets" / "icons.svg"
OUT = Path(os.environ.get("OUT_DIR", HERE))

# The site's palette (site/css/styles.css, docs/BRAND.md).
BG = "#141711"
SURFACE = "#1a1e15"
SURFACE2 = "#1f2419"
GREEN2 = "#38412b"
LIME = "#c7d66d"
OLIVE = "#7d8e50"
TEXT = "#ecefe4"
DIM = "#a3ad97"
GO = "#00add8"
BRAND = {
    "http": DIM, "files": DIM, "postgres": "#4169e1", "mysql": "#4479a1",
    "bigquery": "#669df6", "redshift": "#8c4fff", "pubsub": "#aecbfa",
    "s3": "#7aa116", "gcs": "#aecbfa", "kafka": DIM, "rabbitmq": "#ff6600",
    "sqs": "#ff4f8b", "go": GO, "python": "#3776ab", "docker": "#2496ed",
    "kubernetes": "#326ce5", "helm": "#525bec", "sql": DIM,
}


def fmt(v):
    s = f"{v:.1f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


class Face:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.upm = self.tt["head"].unitsPerEm
        self.glyphset = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        self.font.scale = (self.upm, self.upm)

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {"kern": True, "liga": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def width(self, text, size):
        return sum(p.x_advance for _, p in self.shape(text)) * size / self.upm

    def path(self, text, x, y, size, fill, anchor="start", opacity=None):
        s = size / self.upm
        w = self.width(text, size)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        d, cur = [], 0
        for info, pos in self.shape(text):
            name = self.order[info.codepoint]
            pen = SVGPathPen(self.glyphset, ntos=fmt)
            tp = TransformPen(pen, (s, 0, 0, -s, x + (cur + pos.x_offset) * s, y - pos.y_offset * s))
            self.glyphset[name].draw(tp)
            c = pen.getCommands()
            if c:
                d.append(c)
            cur += pos.x_advance
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        return f'<path fill="{fill}"{op} d="{" ".join(d)}"/>'


MONO = Face(FONTS / "IBM-Plex-Mono" / "IBMPlexMono-Regular.ttf")
MONO_M = Face(FONTS / "IBM-Plex-Mono" / "IBMPlexMono-Medium.ttf")
MONO_I = Face(FONTS / "IBM-Plex-Mono" / "IBMPlexMono-Italic.ttf")
SANS = Face(FONTS / "IBM-Plex-Sans" / "IBMPlexSans-Regular.ttf")
SANS_M = Face(FONTS / "IBM-Plex-Sans" / "IBMPlexSans-Medium.ttf")


def icons():
    """The site's sprite, symbol by symbol. Each is 24x24 and currentColor."""
    s = ICONS.read_text()
    return {m.group(1): m.group(0) for m in re.finditer(r'<symbol id="i-([a-z0-9]+)".*?</symbol>', s, re.S)}


ICON = icons()


def icon(name, x, y, size, color):
    return f'<use href="#i-{name}" x="{fmt(x)}" y="{fmt(y)}" width="{size}" height="{size}" color="{color}"/>'


def breve(x, y, box, color):
    """The README mark (.github/assets/brevis.svg): a 96 box, arc 66 wide and
    8.3 deep, stroke 9, round caps. Scaled to `box`, top-left at (x, y)."""
    k = box / 96
    x0, x1, yb, yc = x + 15 * k, x + 81 * k, y + 45 * k, y + 56 * k
    return (f'<path d="M{fmt(x0)} {fmt(yb)}C{fmt(x0)} {fmt(yc)} {fmt(x1)} {fmt(yc)} {fmt(x1)} {fmt(yb)}" '
            f'fill="none" stroke="{color}" stroke-width="{fmt(9 * k)}" stroke-linecap="round"/>')


def rect(x, y, w, h, fill, stroke=None, r=12, sw=1.5, opacity=None):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{r}" fill="{fill}"{st}{op}/>'


def grid_defs():
    return (f'<pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">'
            f'<circle cx="18" cy="18" r="1.3" fill="{GREEN2}"/></pattern>')


def svg(w, h, body, title, desc, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{title}</title>\n<desc id="d">{desc}</desc>\n'
            f'<defs>{defs}</defs>\n{body}\n</svg>\n')


def chip(x, y, label, face=MONO, size=19, icon_name=None, soon=False, h=40):
    """A chip like the site's: icon, name, optional `soon` badge. Returns svg, width."""
    pad = 14
    tw = face.width(label, size)
    iw = (22 + 8) if icon_name else 0
    bw = 0
    if soon:
        bw = MONO.width("soon", 13) + 22
    w = pad + iw + tw + (bw if soon else 0) + pad
    parts = [rect(x, y, w, h, SURFACE2, GREEN2, r=h / 2)]
    cx = x + pad
    if icon_name:
        parts.append(icon(icon_name, cx, y + (h - 22) / 2, 22, BRAND.get(icon_name, DIM)))
        cx += iw
    parts.append(face.path(label, cx, y + h / 2 + size * 0.36, size, TEXT))
    cx += tw
    if soon:
        bx = cx + 10
        parts.append(rect(bx, y + 9, bw - 10, h - 18, GREEN2, r=(h - 18) / 2))
        parts.append(MONO.path("soon", bx + (bw - 10) / 2, y + h / 2 + 13 * 0.36, 13, DIM, anchor="middle"))
    return "".join(parts), w


def banner():
    W, H = 1600, 560
    b = [rect(0, 0, W, H, BG, r=24), f'<rect width="{W}" height="{H}" rx="24" fill="url(#grid)"/>']
    m = 96
    # Lockup: mark optically centred on the wordmark's x-height, ~1.05x the type.
    ts = 92
    base = 132
    box = ts * 1.05
    xh = 0.516 * ts
    b.append(breve(m, base - xh / 2 - box / 2, box, LIME))
    x = m + box + 22
    b.append(MONO_M.path("brevis", x, base, ts, TEXT))
    x += MONO_M.width("brevis", ts)
    b.append(MONO_M.path(".sh", x, base, ts, OLIVE))
    # The pill, right.
    pill = "open source · built in Go · self-hosted"
    ps = 21
    pw = MONO.width(pill, ps) + 44
    b.append(rect(W - m - pw, base - 42, pw, 46, SURFACE, GREEN2, r=23))
    b.append(MONO.path(pill, W - m - pw / 2, base - 42 + 23 + ps * 0.36, ps, DIM, anchor="middle"))
    # Title, two colours: the one accent is "In Go."
    t1, t2 = "From raw data to modelled tables. ", "In Go."
    tsz = 66
    ty = 270
    b.append(SANS_M.path(t1, m, ty, tsz, TEXT))
    b.append(SANS_M.path(t2, m + SANS_M.width(t1, tsz), ty, tsz, LIME))
    # Lead, two lines (the site's hero lead).
    l1 = "Orchestration, extraction, ingestion and data modelling — Core, SDK, Gateway and SQL — unified in Go."
    l2 = "Open source, in your cluster, with no data passing through the orchestrator."
    b.append(SANS.path(l1, m, 328, 28, DIM))
    b.append(SANS.path(l2, m, 368, 28, DIM))
    # The rule, then Seneca on the left and the four pieces on the right.
    b.append(f'<path d="M{m} 428H{W - m}" stroke="{GREEN2}" stroke-width="1.5"/>')
    b.append(MONO_I.path("non exiguum temporis habemus, sed multum perdidimus", m, 478, 24, OLIVE))
    b.append(MONO.path("— Seneca, De Brevitate Vitae, I.3", m, 512, 20, DIM))
    # Four chips, right-aligned, each a Go module.
    chips = []
    total = 0
    for name in ["Core", "SDK", "Gateway", "SQL"]:
        s, w = chip(0, 0, name, MONO_M, 20, icon_name="go", h=44)
        chips.append((name, w))
        total += w + 14
    x = W - m - total + 14
    for name, w in chips:
        s, _ = chip(x, 466, name, MONO_M, 20, icon_name="go", h=44)
        b.append(s)
        x += w + 14
    defs = grid_defs() + ICON["go"]
    return svg(W, H, "\n".join(b), "brevis.sh — from raw data to modelled tables. In Go.",
               "The brevis.sh wordmark with its mark, the breve. Title: from raw data to modelled tables, in Go. "
               "Lead: orchestration, extraction, ingestion and data modelling, the Core, SDK, Gateway and SQL, "
               "unified in Go; open source, in your cluster, with no data passing through the orchestrator. "
               "Seneca: non exiguum temporis habemus, sed multum perdidimus. Four chips: Core, SDK, Gateway, SQL, "
               "each a Go module.", defs)


def row(x, y, w, h, name, desc, pill, wire_in, wire_out, wx0, wx1):
    """A data-plane row: name with the Go icon, a two-line description, the module pill."""
    p = [rect(x, y, w, h, SURFACE, GREEN2, r=16)]
    cy = y + h / 2
    if wire_in:
        p.append(f'<path d="M{fmt(wx0)} {fmt(cy)}H{fmt(x)}" stroke="{OLIVE}" stroke-width="2"/>')
        p.append(f'<path d="M{fmt(x - 10)} {fmt(cy - 6)}l10 6-10 6z" fill="{OLIVE}"/>')
    if wire_out:
        p.append(f'<path d="M{fmt(x + w)} {fmt(cy)}H{fmt(wx1)}" stroke="{OLIVE}" stroke-width="2"/>')
        p.append(f'<path d="M{fmt(wx1 - 10)} {fmt(cy - 6)}l10 6-10 6z" fill="{OLIVE}"/>')
    p.append(icon("go", x + 24, y + 22, 26, GO))
    p.append(MONO_M.path(name, x + 60, y + 44, 28, TEXT))
    pw = MONO.width(pill, 15) + 24
    p.append(rect(x + w - 24 - pw, y + 20, pw, 30, SURFACE2, GREEN2, r=15))
    p.append(MONO.path(pill, x + w - 24 - pw / 2, y + 20 + 15 + 15 * 0.36, 15, DIM, anchor="middle"))
    yy = y + 84
    for line in desc:
        p.append(SANS.path(line, x + 24, yy, 23, DIM))
        yy += 31
    return "\n".join(p)


def chips_row(x, y, items, maxw):
    """Chips wrapped into lines inside maxw. items: (label, icon, soon)."""
    p, cx, cy, gap = [], x, y, 10
    for label, ic, soon in items:
        s, w = chip(0, 0, label, MONO, 20, icon_name=ic, soon=soon, h=40)
        if cx + w > x + maxw and cx > x:
            cx, cy = x, cy + 40 + gap
        s, w = chip(cx, cy, label, MONO, 20, icon_name=ic, soon=soon, h=40)
        p.append(s)
        cx += w + gap
    return "\n".join(p), cy + 40


def ecosystem():
    W, H = 1500, 820
    b = [rect(0, 0, W, H, BG, r=24), f'<rect width="{W}" height="{H}" rx="24" fill="url(#grid)"/>']
    L, LW = 48, 410          # sources column
    M, MW = 506, 530         # data plane
    R, RW = 1084, 370        # destinations column
    # Control plane: the Core, apart, and no wire reaches it.
    b.append(MONO.path("control plane", M, 56, 18, OLIVE))
    b.append(rect(M, 70, MW, 118, SURFACE, LIME, r=16, sw=1.5))
    b.append(icon("go", M + 24, 92, 26, GO))
    b.append(MONO_M.path("Core", M + 60, 114, 28, TEXT))
    pw = MONO.width("brevis-sh/brevis", 15) + 24
    b.append(rect(M + MW - 24 - pw, 90, pw, 30, SURFACE2, GREEN2, r=15))
    b.append(MONO.path("brevis-sh/brevis", M + MW - 24 - pw / 2, 90 + 15 + 15 * 0.36, 15, DIM, anchor="middle"))
    b.append(SANS.path("Schedules, queues and starts one pod per step.", M + 24, 154, 23, DIM))
    b.append(SANS.path("Never touches the data.", M + 24, 183, 23, TEXT))
    # Data plane rows.
    b.append(MONO.path("data plane", M, 246, 18, OLIVE))
    rows = [
        ("SDK", ["A Go library that extracts, shapes", "and loads, inside your step."], "brevis/sdk", True, True),
        ("Gateway", ["Takes HTTP POST, answers 202 and writes", "in batches. No database of its own."], "brevis/gateway", True, True),
        ("SQL", ["Plain .sql files become tables and views,", "in dependency order."], "brevis/sql", False, True),
    ]
    y, rh, gap = 262, 140, 20
    ys = []
    for name, desc, pill, win, wout in rows:
        b.append(row(M, y, MW, rh, name, desc, pill, win, wout, L + LW + 8, R - 8))
        ys.append(y)
        y += rh + gap
    # Sources, aligned with the SDK and Gateway rows.
    b.append(MONO.path("where it comes from", L, 246, 18, OLIVE))
    b.append(SANS_M.path("the SDK fetches", L, ys[0] + 26, 21, TEXT))
    s, _ = chips_row(L, ys[0] + 40, [("HTTP", "http", False), ("Postgres", "postgres", False), ("MySQL", "mysql", False),
                                      ("files", "files", False), ("+ any HTTP API", None, False)], LW)
    b.append(s)
    b.append(SANS_M.path("pushed to the Gateway", L, ys[1] + 26, 21, TEXT))
    s, _ = chips_row(L, ys[1] + 40, [("webhooks and apps", "http", False), ("Pub/Sub", "pubsub", True), ("Kafka", "kafka", True),
                                      ("RabbitMQ", "rabbitmq", True), ("SQS", "sqs", True), ("+ any HTTP client", None, False)], LW)
    b.append(s)
    # Destinations.
    b.append(MONO.path("where it lands", R, 246, 18, OLIVE))
    b.append(SANS_M.path("tables", R, ys[0] + 26, 21, TEXT))
    s, yy = chips_row(R, ys[0] + 40, [("BigQuery", "bigquery", False), ("Postgres", "postgres", False),
                                       ("MySQL", "mysql", False), ("Redshift", "redshift", False)], RW)
    b.append(s)
    b.append(SANS_M.path("topics", R, ys[1] + 26, 21, TEXT))
    s, yy = chips_row(R, ys[1] + 40, [("Pub/Sub", "pubsub", False), ("Kafka", "kafka", True),
                                       ("RabbitMQ", "rabbitmq", True), ("SQS", "sqs", True)], RW)
    b.append(s)
    b.append(SANS_M.path("files in a bucket", R, ys[2] + 26, 21, TEXT))
    s, yy = chips_row(R, ys[2] + 40, [("S3", "s3", False), ("GCS", "gcs", False), ("+ any S3-compatible", None, False)], RW)
    b.append(s)
    # The foot line.
    b.append(f'<path d="M{L} {H - 60}H{W - L}" stroke="{GREEN2}" stroke-width="1.5"/>')
    b.append(SANS.path("Each piece is its own Go module, version and image. The Core orchestrates the others when you want it to — it is a prerequisite for none of them.",
                       L, H - 26, 21, DIM))
    defs = grid_defs() + "".join(ICON[k] for k in ["go", "http", "files", "postgres", "mysql", "bigquery", "redshift",
                                                    "pubsub", "s3", "gcs", "kafka", "rabbitmq", "sqs"])
    return svg(W, H, "\n".join(b), "The brevis.sh ecosystem: where data comes from, the four pieces, where it lands",
               "The control plane is the Core: it schedules, queues and starts one pod per step, and never touches the data; "
               "no line reaches it. The data plane is the SDK, which fetches from HTTP, Postgres, MySQL and files; the Gateway, "
               "which receives POSTs from webhooks and apps; and SQL, which models where the data already landed. "
               "Destinations: tables in BigQuery, Postgres, MySQL and Redshift; topics in Pub/Sub, with Kafka, RabbitMQ and SQS "
               "soon; files in S3, GCS or any S3-compatible bucket.", defs)


def tenses():
    """Seneca, X.2: life is divided into what was, what is, what will be. The
    console's overview is drawn the same way."""
    W, H = 1600, 300
    b = [rect(0, 0, W, H, BG, r=24), f'<rect width="{W}" height="{H}" rx="24" fill="url(#grid)"/>']
    cells = [
        ("quod fuit", "what ran", ["the runs, the success rate,", "and each run's own logs"]),
        ("quod est", "what is running", ["the DAG with each step's state,", "live, one box per step"]),
        ("quod futurum est", "what is next", ["the scheduled slots, and the", "backfill you asked for"]),
    ]
    m, gap = 64, 24
    cw = (W - 2 * m - 2 * gap) / 3
    for i, (lat, en, lines) in enumerate(cells):
        x = m + i * (cw + gap)
        b.append(rect(x, 56, cw, 188, SURFACE, GREEN2, r=16))
        b.append(MONO_I.path(lat, x + 28, 104, 26, OLIVE))
        b.append(SANS_M.path(en, x + 28, 150, 32, TEXT))
        yy = 190
        for ln in lines:
            b.append(SANS.path(ln, x + 28, yy, 22, DIM))
            yy += 30
    b.append(MONO.path("In tria tempora vita dividitur: quod fuit, quod est, quod futurum est. — De Brevitate Vitae, X.2",
                       W / 2, 282, 19, DIM, anchor="middle"))
    return svg(W, H, "\n".join(b), "Seneca's three tenses, as the console's overview draws them",
               "Three cards. Quod fuit, what ran: the runs, the success rate, and each run's own logs. Quod est, what is "
               "running: the DAG with each step's state, live. Quod futurum est, what is next: the scheduled slots and the "
               "backfill you asked for. Seneca, De Brevitate Vitae X.2: life is divided into three times, what was, what is, "
               "what will be.", grid_defs())


if __name__ == "__main__":
    (OUT / "banner.svg").write_text(banner())
    (OUT / "ecosystem.svg").write_text(ecosystem())
    (OUT / "tenses.svg").write_text(tenses())
    for f in OUT.glob("*.svg"):
        print(f.name, f.stat().st_size, "bytes")
