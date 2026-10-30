"""Paper figures: database schema and system architecture.

Run `python scripts/make_figures.py` (needs the `figures` extra) to write PDF and PNG files
to results/figures/.

- schema: tables, primary keys and foreign keys are read from the live DuckDB schema
  (src/teleownermap/schema.py), so the figure can't drift from the code. Only the layer
  grouping and box positions are set here; a table missing from LAYOUT is an error.
- architecture: the pipeline from docs/architecture.md, with each stage's built/planned
  status set by hand in STAGES. Update it as stages get built.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from teleownermap.schema import connect  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "results" / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 6.5,
        "pdf.fonttype": 42,  # embed TrueType so the PDF text stays selectable
        "ps.fonttype": 42,
    }
)

INK = "#222222"
MUTED = "#666666"
ARROW = "#555555"

# --- Schema ---------------------------------------------------------------------------------

# Layers from docs/data_model.md: (label, band fill, header fill, (x0, y0, x1, y1) in inches).
# Records sit on the left, the statement tables in a middle column and entities on the right,
# so foreign-key arrows fan out between columns without crossing any box.
SCHEMA_W, SCHEMA_H = 7.5, 5.55
BANDS = {
    "provenance": ("Provenance", "#eef2f7", "#c9d6e6", (0.05, 0.05, 1.65, 5.5)),
    "statements": ("What sources say", "#eef5ee", "#cfe3cf", (1.75, 0.05, 5.05, 5.5)),
    "computed": ("Computed on top\n(rebuildable)", "#f7f2e8", "#e8d9b8", (5.15, 1.45, 7.45, 5.5)),
    "user": ("User and reproducibility", "#f4eef5", "#e0cfe3", (5.15, 0.05, 7.45, 1.35)),
}

# table -> (layer, center x, top y), inches.
LAYOUT = {
    "sources": ("provenance", 0.85, 4.25),
    "records": ("provenance", 0.85, 3.05),
    "entity_records": ("statements", 2.5, 5.15),
    "identifiers": ("statements", 2.5, 4.42),
    "attributes": ("statements", 2.5, 3.69),
    "events": ("statements", 2.5, 2.825),
    "licenses": ("statements", 2.5, 1.825),
    "relationships": ("statements", 2.5, 1.095),
    "entities": ("statements", 4.2, 3.2),
    "match_evidence": ("computed", 6.0, 4.6),
    "match_links": ("computed", 6.0, 3.26),
    "evidence": ("computed", 6.0, 2.4),
    "reviews": ("user", 6.0, 1.08),
    "runs": ("user", 6.0, 0.43),
}
BOX_WIDTHS = {"entities": 1.45}

# References the database can't express as foreign keys: (table, target, column, curvature).
# Drawn dashed; reviews -> match_links bows right to pass beside the evidence box.
LOGICAL_REFS = [
    ("reviews", "match_links", "target_id", 0.3),
    ("reviews", "relationships", "target_id", 0.0),
]
# Array columns that point at records (listed in the box, no arrow, to limit clutter).
ARRAY_REFS = {"match_evidence": ["record_ids[]"], "evidence": ["record_ids[]"]}

BOX_W = 1.3
HEADER_H = 0.2
LINE_H = 0.135


def _schema_keys() -> tuple[dict[str, list[str]], list[tuple[str, str, str]]]:
    """Primary-key columns per table and (table, referenced table, column) foreign keys."""
    con = connect()
    rows = con.execute(
        "SELECT table_name, constraint_type, constraint_column_names, referenced_table "
        "FROM duckdb_constraints() "
        "WHERE constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')"
    ).fetchall()
    tables = [r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()]
    pks: dict[str, list[str]] = {t: [] for t in tables}
    fks = []
    for table, kind, cols, ref in rows:
        if kind == "PRIMARY KEY":
            pks[table] = list(cols)
        else:
            fks += [(table, ref, c) for c in cols]
    missing = set(tables) ^ set(LAYOUT)
    if missing:
        raise ValueError(f"LAYOUT and schema.py disagree on tables: {sorted(missing)}")
    return pks, fks


def _table_box(ax, name: str, header_fill: str, lines: list[tuple[str, str]]):
    _, cx, top = LAYOUT[name]
    w = BOX_WIDTHS.get(name, BOX_W)
    h = HEADER_H + LINE_H * max(len(lines), 1) + 0.06
    x0, y0 = cx - w / 2, top - h
    box = FancyBboxPatch(
        (x0, y0),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=0.04",
        fc="white",
        ec=INK,
        lw=0.6,
        zorder=3,
    )
    ax.add_patch(box)
    header = FancyBboxPatch(
        (x0, top - HEADER_H),
        w,
        HEADER_H,
        boxstyle="round,pad=0,rounding_size=0.04",
        fc=header_fill,
        ec=INK,
        lw=0.6,
        zorder=4,
    )
    ax.add_patch(header)
    ax.text(
        cx, top - HEADER_H / 2, name, ha="center", va="center", weight="bold", color=INK, zorder=5
    )
    for i, (tag, col) in enumerate(lines):
        y = top - HEADER_H - 0.03 - LINE_H * (i + 0.5)
        ax.text(
            x0 + 0.06,
            y,
            tag,
            ha="left",
            va="center",
            weight="bold",
            color=MUTED,
            fontsize=5.5,
            zorder=5,
        )
        ax.text(x0 + 0.3, y, col, ha="left", va="center", color=INK, zorder=5)
    return box


def schema_figure() -> plt.Figure:
    pks, fks = _schema_keys()
    fig = plt.figure(figsize=(SCHEMA_W, SCHEMA_H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SCHEMA_W)
    ax.set_ylim(0, SCHEMA_H)
    ax.axis("off")

    for label, fill, _, (x0, y0, x1, y1) in BANDS.values():
        ax.add_patch(
            FancyBboxPatch(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                boxstyle="round,pad=0,rounding_size=0.08",
                fc=fill,
                ec="none",
                zorder=0,
            )
        )
        ax.text(
            x0 + 0.1,
            y1 - 0.1,
            label,
            ha="left",
            va="top",
            weight="bold",
            color=MUTED,
            fontsize=7,
            zorder=1,
        )

    boxes = {}
    for name, (layer, _, _) in LAYOUT.items():
        fk_cols = [c for t, _, c in fks if t == name]
        self_refs = {c for t, r, c in fks if t == name and r == name}
        lines = [("PK", c) for c in pks[name]]
        lines += [
            ("FK", c + (" (self)" if c in self_refs else "")) for c in fk_cols if c not in pks[name]
        ]
        lines += [("ref", c) for c in ARRAY_REFS.get(name, [])]
        lines += [("ref", c) for t, _, c, _ in LOGICAL_REFS if t == name][:1]
        boxes[name] = _table_box(ax, name, BANDS[layer][2], lines)

    def anchors(src: str, tgt: str, right_side: bool = False):
        """Arrow ends on the facing sides of two boxes, so lines stay between columns.

        Each end's height is the other box's centre clamped to its own box, which keeps
        lines near horizontal and spreads arrowheads along the target's edge. Boxes in the
        same column connect top to bottom, or right side to right side for a bowed arrow.
        """
        a, b = boxes[src], boxes[tgt]
        ax0, ay0, aw, ah = a.get_x(), a.get_y(), a.get_width(), a.get_height()
        bx0, by0, bw, bh = b.get_x(), b.get_y(), b.get_width(), b.get_height()

        def clamp(v, lo, hi):
            return min(max(v, lo + 0.08), hi - 0.08)

        if right_side:
            return (ax0 + aw, ay0 + ah / 2), (bx0 + bw, by0 + bh / 2)
        if bx0 + bw < ax0 or ax0 + aw < bx0:
            left = bx0 + bw < ax0
            ya = clamp(by0 + bh / 2, ay0, ay0 + ah)
            yb = clamp(ay0 + ah / 2, by0, by0 + bh)
            return ((ax0 if left else ax0 + aw), ya), ((bx0 + bw if left else bx0), yb)
        up = by0 > ay0
        cx = ax0 + aw / 2
        return (cx, ay0 + ah if up else ay0), (bx0 + bw / 2, by0 if up else by0 + bh)

    def arrow(src, tgt, dashed=False, rad=0.0):
        start, end = anchors(src, tgt, right_side=rad != 0)
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                shrinkA=1,
                shrinkB=1,
                arrowstyle="-|>,head_length=3,head_width=1.6",
                color=ARROW,
                lw=0.6,
                linestyle=(0, (3, 2)) if dashed else "-",
                connectionstyle=f"arc3,rad={rad}",
                zorder=2,
            )
        )

    # One arrow per (table, referenced table) pair; the box lists every FK column.
    for t, r in dict.fromkeys((t, r) for t, r, _ in fks if t != r):
        arrow(t, r)
    for t, r, _, rad in LOGICAL_REFS:
        arrow(t, r, dashed=True, rad=rad)

    # Key, in the free space under the provenance tables.
    key = [
        ("PK", "primary key"),
        ("FK", "foreign key (solid arrow)"),
        ("ref", "reference the database\ndoesn't enforce (dashed\narrow, or array of IDs)"),
    ]
    y = 1.9
    for tag, text in key:
        ax.text(0.2, y, tag, ha="left", va="top", weight="bold", color=MUTED, fontsize=5.5)
        ax.text(0.48, y, text, ha="left", va="top", color=MUTED, fontsize=5.5, linespacing=1.3)
        y -= 0.16 * (text.count("\n") + 1) + 0.06
    return fig


# --- Architecture ---------------------------------------------------------------------------

STATUS_STYLE = {
    "built": {"fc": "#cfe3cf", "ls": "-"},
    "partial": {"fc": "#eef5ee", "ls": "-"},
    "planned": {"fc": "white", "ls": (0, (4, 2))},
}
STATUS_LABEL = {"built": "Built", "partial": "Partly built", "planned": "Planned"}

# (stage, what it does, where it lives in the repo, status), top to bottom.
STAGES = [
    (
        "1  Sources",
        "FCC ULS, Form 602, GLEIF bulk downloads; dated, SHA-256 fingerprinted",
        "ingest/  →  data/ (gitignored)",
        "planned",
    ),
    (
        "2  Raw records",
        "Extracted rows and passages with locator and parser version; never edited",
        "schema.py: sources, records",
        "built",
    ),
    (
        "3  Statements",
        "Entities, identifiers, attributes, licenses, relationships, events",
        "schema.py",
        "built",
    ),
    (
        "4  Computed layer",
        "Entity matching (Splink), inferred links, timing evidence",
        "tables defined in schema.py",
        "planned",
    ),
    (
        "5  Metrics",
        "Absorbing Markov chain, entropy, anonymity set, hops; control reach",
        "metrics/ownership.py",
        "built",
    ),
    (
        "6  Outputs",
        "Markdown report built; library search API and web app planned",
        "ground_truth.py  →  results/dev_cases.md",
        "partial",
    ),
    (
        "7  User review",
        "Append-only, encrypted match decisions; audit-trail export",
        "reviews table in schema.py",
        "planned",
    ),
]


def _stage_box(ax, x0, y0, w, h, status):
    style = STATUS_STYLE[status]
    box = FancyBboxPatch(
        (x0, y0),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=0.05",
        fc=style["fc"],
        ec=INK,
        lw=0.7,
        ls=style["ls"],
        zorder=3,
    )
    ax.add_patch(box)
    return box


def architecture_figure() -> plt.Figure:
    W, H = 7.5, 6.1
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    x0, w, h, gap, top = 0.15, 4.6, 0.56, 0.18, 5.95
    boxes = []
    for i, (name, what, where, status) in enumerate(STAGES):
        y0 = top - h - i * (h + gap)
        boxes.append(_stage_box(ax, x0, y0, w, h, status))
        ax.text(
            x0 + 0.1,
            y0 + h - 0.12,
            name,
            ha="left",
            va="top",
            weight="bold",
            fontsize=7.5,
            color=INK,
            zorder=5,
        )
        ax.text(
            x0 + w - 0.1,
            y0 + h - 0.12,
            STATUS_LABEL[status],
            ha="right",
            va="top",
            fontsize=5.5,
            color=MUTED,
            style="italic",
            zorder=5,
        )
        ax.text(x0 + 0.1, y0 + 0.27, what, ha="left", va="center", color=INK, zorder=5)
        ax.text(
            x0 + 0.1,
            y0 + 0.11,
            where,
            ha="left",
            va="center",
            color=MUTED,
            family="DejaVu Sans Mono",
            fontsize=5.8,
            zorder=5,
        )
    for a, b in zip(boxes, boxes[1:], strict=False):
        ax.add_patch(
            FancyArrowPatch(
                (a.get_x() + 0.5, a.get_y()),
                (b.get_x() + 0.5, b.get_y() + b.get_height()),
                arrowstyle="-|>,head_length=3,head_width=1.6",
                color=ARROW,
                lw=0.7,
                zorder=2,
            )
        )

    # Side inputs: hand-built ground truth feeds the statements; answer keys check outputs.
    sx, sw, sh = 5.15, 2.2, 0.62

    def side(stage_idx, title, body, where, status, linestyle):
        target = boxes[stage_idx]
        y0 = target.get_y() + (target.get_height() - sh) / 2
        _stage_box(ax, sx, y0, sw, sh, status)
        ax.text(
            sx + 0.08, y0 + sh - 0.1, title, ha="left", va="top", weight="bold", color=INK, zorder=5
        )
        ax.text(sx + 0.08, y0 + 0.28, body, ha="left", va="center", color=INK, zorder=5)
        ax.text(
            sx + 0.08,
            y0 + 0.11,
            where,
            ha="left",
            va="center",
            color=MUTED,
            family="DejaVu Sans Mono",
            fontsize=5.5,
            zorder=5,
        )
        ax.add_patch(
            FancyArrowPatch(
                (sx, y0 + sh / 2),
                (x0 + w, y0 + sh / 2),
                arrowstyle="-|>,head_length=3,head_width=1.6",
                color=ARROW,
                lw=0.7,
                linestyle=linestyle,
                zorder=2,
            )
        )

    side(
        2,
        "Hand-built case graphs",
        "Verified ground truth, one row per statement",
        "ground_truth/graphs/*.csv",
        "built",
        "-",
    )
    side(
        5,
        "Evaluation answer keys",
        "Held-out cases, negative controls",
        "ground_truth/negative_controls.csv",
        "partial",
        (0, (4, 2)),
    )

    # Legend.
    lx, ly = 5.15, 5.95
    ax.text(lx, ly, "Status", ha="left", va="top", weight="bold", color=MUTED, fontsize=7)
    for i, status in enumerate(STATUS_STYLE):
        y = ly - 0.3 - i * 0.24
        _stage_box(ax, lx, y - 0.08, 0.3, 0.16, status)
        ax.text(lx + 0.4, y, STATUS_LABEL[status], ha="left", va="center", color=INK)

    # Engineering strip.
    ax.add_patch(
        FancyBboxPatch(
            (0.15, 0.1),
            W - 0.3,
            0.42,
            boxstyle="round,pad=0,rounding_size=0.05",
            fc="#f2f2f2",
            ec="none",
            zorder=1,
        )
    )
    ax.text(0.25, 0.4, "Engineering", ha="left", va="center", weight="bold", color=MUTED)
    ax.text(
        0.25,
        0.22,
        "Python ≥ 3.11 · DuckDB · NumPy · SciPy · hatchling build · pytest · "
        "ruff lint and format checks in GitHub Actions · AGPL-3.0",
        ha="left",
        va="center",
        color=INK,
    )
    return fig


# --- Pipeline -------------------------------------------------------------------------------

# (step, what happens, what it produces, status), left to right. Same stages as STAGES,
# described as data flow rather than repo layout.
PIPELINE = [
    (
        "Collect",
        "FCC ULS, Form 602 and GLEIF bulk downloads",
        "dated, fingerprinted snapshots",
        "planned",
    ),
    (
        "Extract",
        "Parse rows and passages with exact locators; never edited",
        "raw records",
        "partial",
    ),
    (
        "Record statements",
        "One row per source statement: share ranges, dates, legal status",
        "entities and ownership / control links",
        "built",
    ),
    (
        "Match and infer",
        "Splink 'possibly same' links, inferred links, timing evidence",
        "explained candidate links",
        "planned",
    ),
    (
        "Measure",
        "Absorbing Markov chain up from each licensee; separate control reach",
        "owner probabilities, entropy, anonymity set, hops (as ranges)",
        "built",
    ),
    (
        "Present",
        "Every result traced to its sources; unverified matches shown separately",
        "report built; API and web app planned",
        "partial",
    ),
]


def _wrap(text: str, width: int) -> str:
    return textwrap.fill(text, width=width, break_on_hyphens=False)


def pipeline_figure() -> plt.Figure:
    W, H = 7.5, 3.0
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    x0, w, gap, y0, h = 0.1, 1.1, 0.14, 0.95, 1.2
    boxes = []
    for i, (step, what, out, status) in enumerate(PIPELINE):
        bx = x0 + i * (w + gap)
        boxes.append(_stage_box(ax, bx, y0, w, h, status))
        ax.text(
            bx + 0.07,
            y0 + h - 0.08,
            f"{i + 1} {step}",
            ha="left",
            va="top",
            weight="bold",
            fontsize=6.0,
            color=INK,
            zorder=5,
        )
        ax.text(
            bx + 0.07,
            y0 + h - 0.3,
            _wrap(what, 22),
            ha="left",
            va="top",
            fontsize=5.8,
            color=INK,
            linespacing=1.25,
            zorder=5,
        )
        ax.text(
            bx + 0.07,
            y0 + 0.07,
            "→ " + _wrap(out, 21).replace("\n", "\n    "),
            ha="left",
            va="bottom",
            fontsize=5.6,
            color=MUTED,
            style="italic",
            linespacing=1.25,
            zorder=5,
        )
    for a, b in zip(boxes, boxes[1:], strict=False):
        y = y0 + h / 2
        ax.add_patch(
            FancyArrowPatch(
                (a.get_x() + w, y),
                (b.get_x(), y),
                shrinkA=1,
                shrinkB=1,
                arrowstyle="-|>,head_length=3,head_width=1.6",
                color=ARROW,
                lw=0.7,
                zorder=2,
            )
        )

    def centre_x(i):
        return boxes[i].get_x() + w / 2

    # Hand-built ground truth enters at the statements step (built).
    gx, gw, gy, gh = centre_x(2) - 0.95, 1.9, 2.4, 0.4
    _stage_box(ax, gx, gy, gw, gh, "built")
    ax.text(
        gx + gw / 2,
        gy + gh - 0.08,
        "Hand-built ground-truth case graphs",
        ha="center",
        va="top",
        weight="bold",
        fontsize=6.2,
        color=INK,
        zorder=5,
    )
    ax.text(
        gx + gw / 2,
        gy + 0.07,
        "verified quotes, one row per statement",
        ha="center",
        va="bottom",
        fontsize=5.6,
        color=MUTED,
        style="italic",
        zorder=5,
    )
    ax.add_patch(
        FancyArrowPatch(
            (centre_x(2), gy),
            (centre_x(2), y0 + h),
            shrinkA=1,
            shrinkB=1,
            arrowstyle="-|>,head_length=3,head_width=1.6",
            color=ARROW,
            lw=0.7,
            zorder=2,
        )
    )

    # User review loop (planned): decisions on matches feed back into matching.
    rx, rw, ry, rh = centre_x(4) - 0.95, 1.9, 0.12, 0.5
    _stage_box(ax, rx, ry, rw, rh, "planned")
    ax.text(
        rx + rw / 2,
        ry + rh - 0.08,
        "User review",
        ha="center",
        va="top",
        weight="bold",
        fontsize=6.2,
        color=INK,
        zorder=5,
    )
    ax.text(
        rx + rw / 2,
        ry + 0.07,
        "confirm or reject matches; audit trail",
        ha="center",
        va="bottom",
        fontsize=5.6,
        color=MUTED,
        style="italic",
        zorder=5,
    )
    for start, end in (
        ((centre_x(5), y0), (rx + rw, ry + rh / 2)),
        ((rx, ry + rh / 2), (centre_x(3), y0)),
    ):
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                shrinkA=1,
                shrinkB=1,
                connectionstyle="angle,angleA=90,angleB=0"
                if start[1] > end[1]
                else "angle,angleA=0,angleB=90",
                arrowstyle="-|>,head_length=3,head_width=1.6",
                color=ARROW,
                lw=0.7,
                linestyle=(0, (4, 2)),
                zorder=2,
            )
        )

    # Status key, top right.
    kx, ky = 4.75, 2.75
    for i, status in enumerate(STATUS_STYLE):
        x = kx + i * 0.9
        _stage_box(ax, x, ky - 0.07, 0.24, 0.14, status)
        ax.text(x + 0.3, ky, STATUS_LABEL[status], ha="left", va="center", fontsize=5.8, color=INK)
    return fig


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, make in (
        ("schema", schema_figure),
        ("architecture", architecture_figure),
        ("pipeline", pipeline_figure),
    ):
        fig = make()
        for ext in ("pdf", "png"):
            fig.savefig(OUT_DIR / f"{name}.{ext}", dpi=300)
        plt.close(fig)
        print(f"wrote {OUT_DIR / name}.pdf/.png")


if __name__ == "__main__":
    main()
