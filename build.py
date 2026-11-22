#!/usr/bin/env python3
"""Build script for physik-sims.

Scans sims/**/*.html, validates metadata and PHYSICS_CONTRACT rules,
generates inline SVG QR codes (pure Python stdlib, no dependencies),
and writes index.html + catalog.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://fabian-crypto-sudo.github.io/physik-sims/"

REQUIRED_META = (
    "id",
    "title",
    "subject",
    "topic",
    "grade",
    "tags",
    "summary",
    "controls",
    "representations",
)

# ---------------------------------------------------------------------------
# Pure-Python QR Code Encoder (ISO/IEC 18004, Model 2, Byte Mode, EC Level M)
# ---------------------------------------------------------------------------

_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _init_gf() -> None:
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]


_init_gf()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        root = _GF_EXP[i]
        nxt = [0] * (len(poly) + 1)
        for idx, coeff in enumerate(poly):
            nxt[idx] ^= coeff
            nxt[idx + 1] ^= _gf_mul(coeff, root)
        poly = nxt
    return poly


def _rs_remainder(data: list[int], ec_len: int) -> list[int]:
    gen = _rs_generator(ec_len)
    buf = list(data) + [0] * ec_len
    for i in range(len(data)):
        factor = buf[i]
        if factor != 0:
            for j in range(len(gen)):
                buf[i + j] ^= _gf_mul(gen[j], factor)
    return buf[len(data) :]


# Version -> (total_codewords, ec_per_block, [(count, data_codewords_per_block), ...], alignment_centers)
_QR_M_SPEC: dict[int, tuple[int, int, list[tuple[int, int]], list[int]]] = {
    1: (26, 10, [(1, 16)], []),
    2: (44, 16, [(1, 28)], [6, 18]),
    3: (70, 26, [(1, 44)], [6, 22]),
    4: (100, 18, [(2, 32)], [6, 26]),
    5: (134, 24, [(2, 43)], [6, 30]),
    6: (172, 16, [(4, 27)], [6, 34]),
    7: (196, 18, [(4, 31)], [6, 22, 38]),
    8: (242, 22, [(2, 38), (2, 39)], [6, 24, 42]),
    9: (292, 22, [(3, 36), (2, 37)], [6, 26, 46]),
    10: (346, 26, [(4, 43), (1, 44)], [6, 28, 50]),
}

_REM_BITS = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 0, 8: 0, 9: 0, 10: 0}


def _select_qr_version(byte_len: int) -> int:
    for ver in range(1, 11):
        _, _, blocks, _ = _QR_M_SPEC[ver]
        data_cw = sum(cnt * dcw for cnt, dcw in blocks)
        cc_bits = 8 if ver <= 9 else 16
        avail_bits = data_cw * 8
        needed_bits = 4 + cc_bits + byte_len * 8
        if needed_bits <= avail_bits:
            return ver
    raise ValueError(f"URL too long for QR versions 1-10 ({byte_len} bytes)")


def _encode_qr_codewords(payload: bytes, ver: int) -> list[int]:
    _, ec_per_block, blocks, _ = _QR_M_SPEC[ver]
    data_cw = sum(cnt * dcw for cnt, dcw in blocks)
    cc_bits = 8 if ver <= 9 else 16

    bits: list[int] = []

    def push_bits(val: int, width: int) -> None:
        for shift in range(width - 1, -1, -1):
            bits.append((val >> shift) & 1)

    push_bits(0b0100, 4)  # Byte mode indicator
    push_bits(len(payload), cc_bits)
    for b in payload:
        push_bits(b, 8)

    max_bits = data_cw * 8
    term_len = min(4, max_bits - len(bits))
    push_bits(0, term_len)
    while len(bits) % 8 != 0:
        bits.append(0)

    cw: list[int] = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for b in bits[i : i + 8]:
            byte_val = (byte_val << 1) | b
        cw.append(byte_val)

    pad_bytes = (0xEC, 0x11)
    pad_idx = 0
    while len(cw) < data_cw:
        cw.append(pad_bytes[pad_idx % 2])
        pad_idx += 1

    data_blocks: list[list[int]] = []
    ec_blocks: list[list[int]] = []
    offset = 0
    for count, dcw in blocks:
        for _ in range(count):
            blk = cw[offset : offset + dcw]
            offset += dcw
            data_blocks.append(blk)
            ec_blocks.append(_rs_remainder(blk, ec_per_block))

    interleaved: list[int] = []
    max_dcw = max(len(b) for b in data_blocks)
    for i in range(max_dcw):
        for blk in data_blocks:
            if i < len(blk):
                interleaved.append(blk[i])
    for i in range(ec_per_block):
        for eblk in ec_blocks:
            interleaved.append(eblk[i])
    return interleaved


def _format_bits_m(mask_id: int) -> int:
    # EC level M = 0b00
    data = (0b00 << 3) | (mask_id & 0b111)
    rem = data << 10
    poly = 0x537
    for shift in range(14, 9, -1):
        if rem & (1 << shift):
            rem ^= poly << (shift - 10)
    return ((data << 10) | rem) ^ 0x5412


def _version_bits(ver: int) -> int:
    rem = ver << 12
    poly = 0x1F25
    for shift in range(17, 11, -1):
        if rem & (1 << shift):
            rem ^= poly << (shift - 12)
    return (ver << 12) | rem


def _build_qr_matrix(text: str) -> list[list[int]]:
    payload = text.encode("utf-8")
    ver = _select_qr_version(len(payload))
    size = 17 + 4 * ver
    codewords = _encode_qr_codewords(payload, ver)
    _, _, _, align_centers = _QR_M_SPEC[ver]

    # -1 = unset, 0 = light, 1 = dark
    grid = [[-1] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def set_mod(r: int, c: int, val: int, is_func: bool = True) -> None:
        grid[r][c] = val
        if is_func:
            reserved[r][c] = True

    def place_finder(top: int, left: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = top + dr, left + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                if 0 <= dr <= 6 and 0 <= dc <= 6:
                    dark = (
                        dr in (0, 6)
                        or dc in (0, 6)
                        or (2 <= dr <= 4 and 2 <= dc <= 4)
                    )
                    set_mod(r, c, 1 if dark else 0)
                else:
                    set_mod(r, c, 0)

    place_finder(0, 0)
    place_finder(0, size - 7)
    place_finder(size - 7, 0)

    # Timing patterns
    for i in range(8, size - 8):
        bit = 1 if i % 2 == 0 else 0
        if not reserved[6][i]:
            set_mod(6, i, bit)
        if not reserved[i][6]:
            set_mod(i, 6, bit)

    # Dark module
    set_mod(4 * ver + 9, 8, 1)

    # Alignment patterns
    for cr in align_centers:
        for cc in align_centers:
            if reserved[cr][cc]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    dark = max(abs(dr), abs(dc)) != 1
                    set_mod(cr + dr, cc + dc, 1 if dark else 0)

    # Reserve format info cells
    for i in range(9):
        if i != 6:
            reserved[8][i] = True
            reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True

    # Version info for >= 7
    if ver >= 7:
        vbits = _version_bits(ver)
        for i in range(18):
            bit = (vbits >> i) & 1
            r = i // 3
            c = size - 11 + (i % 3)
            set_mod(r, c, bit)
            set_mod(c, r, bit)

    # Convert codewords + remainder bits into bit stream
    bitstream: list[int] = []
    for cw in codewords:
        for shift in range(7, -1, -1):
            bitstream.append((cw >> shift) & 1)
    bitstream.extend([0] * _REM_BITS[ver])

    # Place data bits in zig-zag
    b_idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for dc in (0, -1):
                c = col + dc
                if not reserved[r][c]:
                    val = bitstream[b_idx] if b_idx < len(bitstream) else 0
                    grid[r][c] = val
                    b_idx += 1
        col -= 2
        upward = not upward

    def mask_fn(mask_id: int, r: int, c: int) -> bool:
        if mask_id == 0:
            return (r + c) % 2 == 0
        if mask_id == 1:
            return r % 2 == 0
        if mask_id == 2:
            return c % 3 == 0
        if mask_id == 3:
            return (r + c) % 3 == 0
        if mask_id == 4:
            return (r // 2 + c // 3) % 2 == 0
        if mask_id == 5:
            return ((r * c) % 2 + (r * c) % 3) == 0
        if mask_id == 6:
            return (((r * c) % 2) + ((r * c) % 3)) % 2 == 0
        return (((r + c) % 2) + ((r * c) % 3)) % 2 == 0

    def apply_format(mat: list[list[int]], mask_id: int) -> None:
        fb = _format_bits_m(mask_id)
        # Bits 14..0
        for i in range(6):
            bit = (fb >> (14 - i)) & 1
            mat[8][i] = bit
            mat[size - 1 - i][8] = bit
        mat[8][7] = (fb >> 8) & 1
        mat[size - 7][8] = (fb >> 8) & 1
        mat[8][8] = (fb >> 7) & 1
        mat[8][size - 8] = (fb >> 7) & 1
        mat[7][8] = (fb >> 6) & 1
        mat[8][size - 7] = (fb >> 6) & 1
        for i in range(6):
            bit = (fb >> (5 - i)) & 1
            mat[5 - i][8] = bit
            mat[8][size - 6 + i] = bit

    def penalty(mat: list[list[int]]) -> int:
        score = 0
        # Rule 1: runs of 5+
        for r in range(size):
            run_row = 1
            run_col = 1
            for c in range(1, size):
                if mat[r][c] == mat[r][c - 1]:
                    run_row += 1
                else:
                    if run_row >= 5:
                        score += 3 + (run_row - 5)
                    run_row = 1
                if mat[c][r] == mat[c - 1][r]:
                    run_col += 1
                else:
                    if run_col >= 5:
                        score += 3 + (run_col - 5)
                    run_col = 1
            if run_row >= 5:
                score += 3 + (run_row - 5)
            if run_col >= 5:
                score += 3 + (run_col - 5)
        # Rule 2: 2x2 blocks
        for r in range(size - 1):
            for c in range(size - 1):
                v = mat[r][c]
                if v == mat[r][c + 1] == mat[r + 1][c] == mat[r + 1][c + 1]:
                    score += 3
        # Rule 3: finder-like patterns 10111010000 or 00001011101
        p1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
        p2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]
        for r in range(size):
            row = mat[r]
            col_arr = [mat[k][r] for k in range(size)]
            for i in range(size - 10):
                if row[i : i + 11] == p1 or row[i : i + 11] == p2:
                    score += 40
                if col_arr[i : i + 11] == p1 or col_arr[i : i + 11] == p2:
                    score += 40
        # Rule 4: dark ratio
        dark = sum(sum(row) for row in mat)
        pct = (dark * 100) / (size * size)
        k = int(abs(pct - 50) // 5)
        score += k * 10
        return score

    best_score = 10**9
    best_mat: list[list[int]] = []
    for mask_id in range(8):
        cand = [row[:] for row in grid]
        for r in range(size):
            for c in range(size):
                if not reserved[r][c] and mask_fn(mask_id, r, c):
                    cand[r][c] ^= 1
        apply_format(cand, mask_id)
        sc = penalty(cand)
        if sc < best_score:
            best_score = sc
            best_mat = cand

    return best_mat


def qr_svg(url: str, size_px: int = 132, quiet: int = 2) -> str:
    """Render an inline SVG QR code with compact horizontal run-length paths."""
    mat = _build_qr_matrix(url)
    n = len(mat)
    vb = n + 2 * quiet
    paths: list[str] = []
    for r, row in enumerate(mat):
        c = 0
        while c < n:
            if row[c] == 1:
                start = c
                while c < n and row[c] == 1:
                    c += 1
                width = c - start
                paths.append(f"M{start + quiet},{r + quiet}h{width}v1h-{width}z")
            else:
                c += 1
    d = "".join(paths)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb} {vb}" '
        f'width="{size_px}" height="{size_px}" role="img" '
        f'aria-label="QR-Code für {html.escape(url)}" shape-rendering="crispEdges">'
        f'<rect width="{vb}" height="{vb}" fill="#ffffff" rx="2"/>'
        f'<path d="{d}" fill="#0f172a"/>'
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# Metadata Parsing & PHYSICS_CONTRACT Linting
# ---------------------------------------------------------------------------

_META_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
_META_LINE_RE = re.compile(r"^\s*@([a-zA-Z0-9_-]+)\s*:\s*(.+?)\s*$")
_EXTERNAL_TAG_RE = re.compile(
    r"""<(?:script|link|img|iframe)\b[^>]*(?:src|href)\s*=\s*["']https?://""",
    re.IGNORECASE,
)
_EXTERNAL_NET_RE = re.compile(
    r"""(?:fetch\s*\(\s*["']https?://|XMLHttpRequest|@import\s+url\s*\(\s*["']?https?://)""",
    re.IGNORECASE,
)


def parse_sim_file(path: Path, root: Path, base_url: str) -> tuple[dict[str, Any], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    rel_path = path.relative_to(root).as_posix()

    meta_raw: dict[str, str] = {}
    for match in _META_COMMENT_RE.finditer(text[:4000]):
        block = match.group(1)
        if "@title:" in block or "@id:" in block:
            for line in block.splitlines():
                m = _META_LINE_RE.match(line)
                if m:
                    meta_raw[m.group(1).lower()] = m.group(2).strip()
            break

    if not meta_raw:
        errors.append(f"{rel_path}: Standardisierter Metadaten-Header (<!-- @id: ... -->) fehlt.")

    for key in REQUIRED_META:
        if not meta_raw.get(key):
            errors.append(f"{rel_path}: Pflicht-Metadatum @{key} fehlt oder ist leer.")

    subject = meta_raw.get("subject", "").lower()
    if subject and subject not in {"physik", "mathe"}:
        errors.append(f"{rel_path}: @subject muss 'physik' oder 'mathe' sein (gefunden: {subject!r}).")

    # Single-File & Touch/Retina Contract Checks
    if _EXTERNAL_TAG_RE.search(text) or _EXTERNAL_NET_RE.search(text):
        errors.append(f"{rel_path}: Externe HTTP(S)-Abhängigkeiten gefunden (Single-File-Verstoß).")

    if not re.search(r"touch-action\s*:\s*none", text):
        errors.append(f"{rel_path}: CSS 'touch-action: none' für Touch-Ergonomie fehlt.")

    if "devicePixelRatio" not in text:
        errors.append(f"{rel_path}: 'devicePixelRatio'-Skalierung für Retina-Displays fehlt.")

    if "pointerdown" not in text:
        errors.append(f"{rel_path}: Pointer Events ('pointerdown') fehlen.")

    if not re.search(r"Math\.min\([^\n;]{1,100}0\.05", text):
        errors.append(f"{rel_path}: Frame-Delta-Clamping (~0.05s) nicht erkannt.")

    def split_csv(val: str) -> list[str]:
        items: list[str] = []
        buf: list[str] = []
        depth = 0
        for ch in val:
            if ch == "(":
                depth += 1
            elif ch == ")" and depth > 0:
                depth -= 1
            if ch == "," and depth == 0:
                part = "".join(buf).strip()
                if part:
                    items.append(part)
                buf = []
            else:
                buf.append(ch)
        part = "".join(buf).strip()
        if part:
            items.append(part)
        return items

    def split_pipe(val: str) -> list[str]:
        return [item.strip() for item in val.split("|") if item.strip()]

    clean_base = base_url.rstrip("/") + "/"
    url = f"{clean_base}{rel_path}"
    presets = split_csv(meta_raw.get("presets", ""))

    entry: dict[str, Any] = {
        "id": meta_raw.get("id", path.stem),
        "title": meta_raw.get("title", path.stem),
        "subject": subject or "physik",
        "topic": meta_raw.get("topic", "Allgemein"),
        "grade": meta_raw.get("grade", "Sek I / Sek II"),
        "tags": split_csv(meta_raw.get("tags", "")),
        "summary": meta_raw.get("summary", ""),
        "controls": split_pipe(meta_raw.get("controls", "")),
        "representations": split_csv(meta_raw.get("representations", "")),
        "presets": [
            {"name": p, "url": f"{url}?preset={p}"}
            for p in presets
        ],
        "path": rel_path,
        "url": url,
    }
    return entry, errors


# ---------------------------------------------------------------------------
# Index HTML Generation
# ---------------------------------------------------------------------------

def _subject_label(subject: str) -> str:
    return "Physik" if subject == "physik" else "Mathematik"


def render_index_html(sims: list[dict[str, Any]], base_url: str) -> str:
    topics = sorted({s["topic"] for s in sims})
    grades = sorted({s["grade"] for s in sims})

    cards_html: list[str] = []
    for s in sims:
        svg_code = qr_svg(s["url"], size_px=124, quiet=2)
        search_blob = " ".join(
            [
                s["title"],
                s["topic"],
                s["grade"],
                s["summary"],
                " ".join(s["tags"]),
                " ".join(s["controls"]),
                " ".join(s["representations"]),
            ]
        ).lower()

        tags_html = "".join(
            f'<span class="tag">{html.escape(t)}</span>' for t in s["tags"]
        )
        controls_html = "".join(
            f"<li>{html.escape(c)}</li>" for c in s["controls"]
        )
        repr_html = "".join(
            f'<span class="pill">{html.escape(r)}</span>' for r in s["representations"]
        )
        presets_html = ""
        if s["presets"]:
            preset_links = "".join(
                f'<a class="preset-link" href="{html.escape(p["url"])}" '
                f'data-rel="{html.escape(s["path"])}?preset={html.escape(p["name"])}">'
                f'?preset={html.escape(p["name"])}</a>'
                for p in s["presets"]
            )
            presets_html = f'<div class="presets"><span class="meta-label">AB-Presets:</span>{preset_links}</div>'

        cards_html.append(
            f"""
      <article class="card"
        data-subject="{html.escape(s['subject'])}"
        data-topic="{html.escape(s['topic'])}"
        data-grade="{html.escape(s['grade'])}"
        data-search="{html.escape(search_blob)}">
        <div class="card-top">
          <div class="badges">
            <span class="badge badge-{html.escape(s['subject'])}">{html.escape(_subject_label(s['subject']))}</span>
            <span class="badge badge-neutral">{html.escape(s['grade'])}</span>
            <span class="badge badge-topic">{html.escape(s['topic'])}</span>
          </div>
          <h2>{html.escape(s['title'])}</h2>
          <p class="summary">{html.escape(s['summary'])}</p>
        </div>

        <div class="card-details">
          <div class="detail-block">
            <span class="meta-label">Bedienung (Fidget &amp; Labor):</span>
            <ul class="controls-list">{controls_html}</ul>
          </div>
          <div class="detail-block">
            <span class="meta-label">Repräsentationsebenen:</span>
            <div class="pills">{repr_html}</div>
          </div>
          {presets_html}
          <div class="tags">{tags_html}</div>
        </div>

        <div class="card-footer">
          <div class="actions">
            <a class="btn btn-primary" href="{html.escape(s['path'])}">Simulation öffnen</a>
            <button type="button" class="btn btn-ghost copy-url-btn" data-url="{html.escape(s['url'])}">Link kopieren</button>
            <button type="button" class="btn btn-ghost toggle-qr-btn" aria-expanded="false">QR-Code</button>
          </div>
          <div class="qr-drawer" hidden>
            <div class="qr-box">
              {svg_code}
            </div>
            <div class="qr-meta">
              <code class="qr-url">{html.escape(s['url'])}</code>
              <button type="button" class="btn btn-small download-qr-btn" data-filename="qr-{html.escape(s['id'])}.svg">QR als SVG laden</button>
            </div>
          </div>
        </div>
      </article>"""
        )

    topic_options = "".join(
        f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in topics
    )
    grade_options = "".join(
        f'<option value="{html.escape(g)}">{html.escape(g)}</option>' for g in grades
    )

    count_text = f"{len(sims)} Simulation" + ("" if len(sims) == 1 else "en")

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>physik-sims — Interaktive Physik- &amp; Mathe-Simulationen</title>
  <style>
    :root {{
      --bg: #0b1020;
      --surface: #131b31;
      --surface-2: #192441;
      --border: rgba(148, 163, 184, 0.2);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-2: #a78bfa;
      --physik: #38bdf8;
      --mathe: #34d399;
      --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      background: radial-gradient(circle at 20% 0%, #15203f 0%, var(--bg) 55%);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      min-height: 100dvh;
    }}
    .wrap {{
      max-width: 1180px;
      margin: 0 auto;
      padding: max(24px, env(safe-area-inset-top)) 20px max(48px, env(safe-area-inset-bottom));
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 24px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--border);
    }}
    .eyebrow {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 4px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(1.5rem, 3vw, 2.2rem);
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      margin: 6px 0 0;
      color: var(--muted);
      max-width: 68ch;
      font-size: 0.96rem;
    }}
    .stats {{
      font-size: 0.88rem;
      color: var(--muted);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 14px;
      white-space: nowrap;
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: 1.8fr 1fr 1fr auto;
      gap: 10px;
      margin-bottom: 24px;
    }}
    @media (max-width: 820px) {{
      .toolbar {{ grid-template-columns: 1fr 1fr; }}
      .toolbar input[type="search"] {{ grid-column: 1 / -1; }}
    }}
    input[type="search"], select {{
      min-height: 42px;
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 0.95rem;
      outline: none;
    }}
    input[type="search"]:focus, select:focus {{
      border-color: var(--accent);
    }}
    .subject-pills {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .filter-pill {{
      min-height: 42px;
      padding: 0 14px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--muted);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .filter-pill.active {{
      background: rgba(56, 189, 248, 0.16);
      border-color: var(--accent);
      color: var(--text);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 18px;
    }}
    .card {{
      background: linear-gradient(180deg, rgba(25, 36, 65, 0.72) 0%, rgba(19, 27, 49, 0.94) 100%);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 14px;
      transition: border-color 0.15s ease, transform 0.15s ease;
    }}
    .card:hover {{
      border-color: rgba(56, 189, 248, 0.5);
    }}
    .badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 10px;
    }}
    .badge {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid transparent;
    }}
    .badge-physik {{
      background: rgba(56, 189, 248, 0.15);
      color: #7dd3fc;
      border-color: rgba(56, 189, 248, 0.35);
    }}
    .badge-mathe {{
      background: rgba(52, 211, 153, 0.15);
      color: #6ee7b7;
      border-color: rgba(52, 211, 153, 0.35);
    }}
    .badge-neutral {{
      background: rgba(148, 163, 184, 0.12);
      color: var(--text);
    }}
    .badge-topic {{
      background: rgba(167, 139, 250, 0.14);
      color: #ddd6fe;
    }}
    h2 {{
      margin: 0 0 6px;
      font-size: 1.2rem;
    }}
    .summary {{
      margin: 0;
      color: #cbd5e1;
      font-size: 0.93rem;
    }}
    .card-details {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      font-size: 0.85rem;
      border-top: 1px solid var(--border);
      padding-top: 12px;
    }}
    .meta-label {{
      display: block;
      color: var(--muted);
      font-weight: 600;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 4px;
    }}
    .controls-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--text);
    }}
    .controls-list li {{ margin-bottom: 2px; }}
    .pills, .presets, .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .pill {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 0.8rem;
    }}
    .preset-link {{
      color: #bae6fd;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.28);
      border-radius: 6px;
      padding: 2px 8px;
      text-decoration: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.78rem;
    }}
    .preset-link:hover {{ background: rgba(56, 189, 248, 0.22); }}
    .tag {{
      color: var(--muted);
      font-size: 0.78rem;
    }}
    .tag::before {{ content: "#"; opacity: 0.7; }}
    .card-footer {{
      border-top: 1px solid var(--border);
      padding-top: 12px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .btn {{
      min-height: 40px;
      padding: 8px 13px;
      border-radius: 10px;
      border: 1px solid var(--border);
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      touch-action: manipulation;
    }}
    .btn-primary {{
      background: var(--accent);
      color: #082f49;
      border-color: transparent;
      flex: 1 1 auto;
    }}
    .btn-primary:hover {{ filter: brightness(1.08); }}
    .btn-ghost {{
      background: var(--surface-2);
      color: var(--text);
    }}
    .btn-ghost:hover {{ border-color: var(--accent); }}
    .btn-small {{
      min-height: 34px;
      padding: 5px 10px;
      font-size: 0.8rem;
      background: var(--surface-2);
      color: var(--text);
    }}
    .qr-drawer {{
      margin-top: 12px;
      padding: 12px;
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      display: flex;
      gap: 12px;
      align-items: center;
    }}
    .qr-drawer[hidden] {{ display: none; }}
    .qr-box {{
      flex: 0 0 auto;
      line-height: 0;
    }}
    .qr-meta {{
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
      align-items: flex-start;
    }}
    .qr-url {{
      font-size: 0.75rem;
      color: var(--muted);
      word-break: break-all;
    }}
    .empty {{
      text-align: center;
      padding: 48px 16px;
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
    }}
    footer {{
      margin-top: 36px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 0.84rem;
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px;
    }}
    footer code {{ color: var(--text); }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <div class="eyebrow">Taktiles Physik- &amp; Mathe-Labor</div>
        <h1>physik-sims</h1>
        <p class="subtitle">
          Eigenständige Single-File-Simulationen für iPad, Beamer und Arbeitsblätter —
          ohne externe Abhängigkeiten, direkt anfassbar und als QR-Code verlinkbar.
        </p>
      </div>
      <div class="stats" id="visible-count">{html.escape(count_text)}</div>
    </header>

    <section class="toolbar" aria-label="Filter und Suche">
      <input id="search-input" type="search" placeholder="Suche nach Thema, Tag, Größe oder Steuerung…" autocomplete="off">
      <select id="topic-select" aria-label="Thema filtern">
        <option value="">Alle Themen</option>
        {topic_options}
      </select>
      <select id="grade-select" aria-label="Stufe filtern">
        <option value="">Alle Stufen</option>
        {grade_options}
      </select>
      <div class="subject-pills" role="group" aria-label="Fach">
        <button type="button" class="filter-pill active" data-subject="">Alle</button>
        <button type="button" class="filter-pill" data-subject="physik">Physik</button>
        <button type="button" class="filter-pill" data-subject="mathe">Mathe</button>
      </div>
    </section>

    <main class="grid" id="sim-grid">
      {"".join(cards_html)}
    </main>

    <div class="empty" id="empty-state" hidden>
      Keine Simulation passt zu den aktuellen Filterkriterien.
    </div>

    <footer>
      <span>Basis-URL für QR-Codes: <code>{html.escape(base_url)}</code></span>
      <span>Katalog für AB-Pipeline: <a href="catalog.json" style="color: var(--accent);">catalog.json</a></span>
    </footer>
  </div>

  <script>
    (function () {{
      const searchInput = document.getElementById("search-input");
      const topicSelect = document.getElementById("topic-select");
      const gradeSelect = document.getElementById("grade-select");
      const subjectButtons = Array.from(document.querySelectorAll(".filter-pill"));
      const cards = Array.from(document.querySelectorAll(".card"));
      const countEl = document.getElementById("visible-count");
      const emptyEl = document.getElementById("empty-state");
      let activeSubject = "";

      function applyFilters() {{
        const q = searchInput.value.trim().toLowerCase();
        const topic = topicSelect.value;
        const grade = gradeSelect.value;
        let visible = 0;

        for (const card of cards) {{
          const matchSubject = !activeSubject || card.dataset.subject === activeSubject;
          const matchTopic = !topic || card.dataset.topic === topic;
          const matchGrade = !grade || card.dataset.grade === grade;
          const matchQuery = !q || (card.dataset.search || "").includes(q);
          const show = matchSubject && matchTopic && matchGrade && matchQuery;
          card.hidden = !show;
          if (show) visible++;
        }}

        countEl.textContent = visible + (visible === 1 ? " Simulation" : " Simulationen");
        emptyEl.hidden = visible > 0;
      }}

      searchInput.addEventListener("input", applyFilters);
      topicSelect.addEventListener("change", applyFilters);
      gradeSelect.addEventListener("change", applyFilters);

      for (const btn of subjectButtons) {{
        btn.addEventListener("click", function () {{
          activeSubject = btn.dataset.subject || "";
          for (const b of subjectButtons) b.classList.toggle("active", b === btn);
          applyFilters();
        }});
      }}

      document.getElementById("sim-grid").addEventListener("click", async function (ev) {{
        const toggleBtn = ev.target.closest(".toggle-qr-btn");
        if (toggleBtn) {{
          const card = toggleBtn.closest(".card");
          const drawer = card.querySelector(".qr-drawer");
          const open = drawer.hidden;
          drawer.hidden = !open;
          toggleBtn.setAttribute("aria-expanded", String(open));
          return;
        }}

        const copyBtn = ev.target.closest(".copy-url-btn");
        if (copyBtn) {{
          const url = copyBtn.dataset.url;
          const orig = copyBtn.textContent;
          try {{
            await navigator.clipboard.writeText(url);
            copyBtn.textContent = "Kopiert!";
          }} catch (_) {{
            copyBtn.textContent = url;
          }}
          setTimeout(() => {{ copyBtn.textContent = orig; }}, 1600);
          return;
        }}

        const dlBtn = ev.target.closest(".download-qr-btn");
        if (dlBtn) {{
          const drawer = dlBtn.closest(".qr-drawer");
          const svg = drawer.querySelector("svg");
          if (!svg) return;
          const blob = new Blob([svg.outerHTML], {{ type: "image/svg+xml;charset=utf-8" }});
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = dlBtn.dataset.filename || "qr.svg";
          a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 1000);
        }}
      }});
    }})();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build index.html and catalog.json for physik-sims.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Public GitHub Pages base URL")
    parser.add_argument("--check", action="store_true", help="Exit non-zero on PHYSICS_CONTRACT violations")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    sims_dir = root / "sims"
    if not sims_dir.is_dir():
        print("Error: sims/ directory not found.", file=sys.stderr)
        return 1

    html_files = sorted(sims_dir.rglob("*.html"))
    if not html_files:
        print("Error: No simulation HTML files found under sims/.", file=sys.stderr)
        return 1

    entries: list[dict[str, Any]] = []
    all_errors: list[str] = []
    seen_ids: set[str] = set()

    for file_path in html_files:
        entry, errors = parse_sim_file(file_path, root, args.base_url)
        sim_id = entry["id"]
        if sim_id in seen_ids:
            errors.append(f"{entry['path']}: Doppelte @id '{sim_id}'.")
        seen_ids.add(sim_id)
        entries.append(entry)
        all_errors.extend(errors)

    for err in all_errors:
        print(f"[CONTRACT] {err}", file=sys.stderr)

    if args.check and all_errors:
        return 1

    entries.sort(key=lambda e: (e["subject"], e["topic"], e["title"]))

    catalog = {
        "base_url": args.base_url.rstrip("/") + "/",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count": len(entries),
        "simulations": entries,
    }
    (root / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (root / "index.html").write_text(
        render_index_html(entries, catalog["base_url"]),
        encoding="utf-8",
    )
    print(f"Built index.html and catalog.json for {len(entries)} simulation(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
