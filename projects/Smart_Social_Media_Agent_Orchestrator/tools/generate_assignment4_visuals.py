"""
Generate all visual charts and diagrams for Assignment 4 report.
Outputs PNG files to: outputs/assignment4_visuals/
"""

import json
import os
import sys

# ── Try importing matplotlib ──────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not found. Installing...")
    os.system(f"{sys.executable} -m pip install matplotlib numpy")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True

# ── Paths ─────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_FILE = os.path.join(
    PROJECT_DIR,
    "outputs", "assignment4_experiment", "20260521_145921", "results.json"
)
OUT_DIR = os.path.join(PROJECT_DIR, "outputs", "assignment4_visuals")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────
C_ORIG = "#4A90D9"     # blue – original
C_IMPR = "#27AE60"     # green – improved
C_BG   = "#F8F9FA"
C_GRID = "#E0E0E0"
FONT_TITLE = {"fontsize": 13, "fontweight": "bold", "color": "#1A1A2E"}
FONT_LABEL = {"fontsize": 10, "color": "#333333"}
FONT_TICK  = {"fontsize": 9}


def styled_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(C_BG)
    ax.grid(axis="y", color=C_GRID, linewidth=0.8, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    if title:
        ax.set_title(title, **FONT_TITLE, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, **FONT_LABEL)
    if ylabel:
        ax.set_ylabel(ylabel, **FONT_LABEL)
    ax.tick_params(labelsize=9)


# ═══════════════════════════════════════════════════════════════════
# 1. AGGREGATE COMPARISON BAR CHART
# ═══════════════════════════════════════════════════════════════════
def chart_aggregate():
    metrics = ["Overall\nScore", "Correctness", "Requirement\nScore", "Completeness", "Failure\nRate"]
    orig   = [0.85, 0.85, 0.95, 0.86, 0.14]
    impr   = [1.00, 1.00, 1.00, 1.00, 0.00]

    x = np.arange(len(metrics))
    width = 0.32

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(C_BG)

    b1 = ax.bar(x - width/2, orig, width, color=C_ORIG, label="Original System", zorder=3, alpha=0.9)
    b2 = ax.bar(x + width/2, impr, width, color=C_IMPR, label="Improved System", zorder=3, alpha=0.9)

    # Value labels on bars
    for bar in b1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.01, f"{h:.2f}",
                ha="center", va="bottom", fontsize=8.5, color="#333", fontweight="bold")
    for bar in b2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.01, f"{h:.2f}",
                ha="center", va="bottom", fontsize=8.5, color="#1a6e3c", fontweight="bold")

    styled_ax(ax, title="Figure 1 — Aggregate Metric Comparison: Original vs Improved System",
              ylabel="Score (0–1)")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=9.5)
    ax.set_ylim(0, 1.18)
    ax.legend(fontsize=10, framealpha=0.9, loc="upper right")
    fig.tight_layout(pad=1.5)
    path = os.path.join(OUT_DIR, "fig1_aggregate_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# 2. PER-TEST OVERALL SCORE CHART
# ═══════════════════════════════════════════════════════════════════
def chart_per_test():
    with open(DATA_FILE) as f:
        data = json.load(f)

    cases = ["T1\nPilates", "T2\nAmbiguous", "T3\nOutdoor\nMat", "T4\nJewelry", "T5\nExact\nCaption", "T6\nTurkish", "T7\nCaption\nOnly"]
    case_ids = ["A4_T1_short_pilates", "A4_T2_ambiguous_this", "A4_T3_outdoor_mat_pilates",
                "A4_T4_jewelry_constraints", "A4_T5_exact_caption", "A4_T6_turkish_outdoor", "A4_T7_caption_only"]

    orig_scores = []
    impr_scores = []
    for cid in case_ids:
        o = next((r["overall_score"] for r in data if r["case_id"] == cid and r["system"] == "original_multi_agent"), 0)
        i = next((r["overall_score"] for r in data if r["case_id"] == cid and r["system"] == "improved_multi_agent"), 0)
        orig_scores.append(o)
        impr_scores.append(i)

    x = np.arange(len(cases))
    width = 0.32

    fig, ax = plt.subplots(figsize=(12, 5.5))
    fig.patch.set_facecolor(C_BG)

    b1 = ax.bar(x - width/2, orig_scores, width, color=C_ORIG, label="Original", zorder=3, alpha=0.9)
    b2 = ax.bar(x + width/2, impr_scores, width, color=C_IMPR, label="Improved", zorder=3, alpha=0.9)

    for bar, val in zip(b1, orig_scores):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8, color="#333", fontweight="bold")
    for bar, val in zip(b2, impr_scores):
        col = "#1a6e3c" if val >= 1.0 else "#cc5500"
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8, color=col, fontweight="bold")

    styled_ax(ax, title="Figure 2 — Per-Test Overall Score: Original vs Improved",
              ylabel="Overall Score (0–1)")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, fontsize=9)
    ax.set_ylim(0, 1.22)
    ax.legend(fontsize=10, framealpha=0.9)

    # Highlight T2 failure region
    ax.axvspan(0.5, 1.5, alpha=0.06, color="red", zorder=0)
    ax.text(1, 1.13, "← Ambiguous Prompt\nFailure Zone", ha="center", fontsize=8, color="#cc2222", style="italic")

    fig.tight_layout(pad=1.5)
    path = os.path.join(OUT_DIR, "fig2_per_test_scores.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# 3. LATENCY COMPARISON CHART
# ═══════════════════════════════════════════════════════════════════
def chart_latency():
    with open(DATA_FILE) as f:
        data = json.load(f)

    cases_short = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
    case_ids = ["A4_T1_short_pilates", "A4_T2_ambiguous_this", "A4_T3_outdoor_mat_pilates",
                "A4_T4_jewelry_constraints", "A4_T5_exact_caption", "A4_T6_turkish_outdoor", "A4_T7_caption_only"]

    orig_lat = []
    impr_lat = []
    for cid in case_ids:
        o = next((r["latency_ms"] for r in data if r["case_id"] == cid and r["system"] == "original_multi_agent"), 0)
        i = next((r["latency_ms"] for r in data if r["case_id"] == cid and r["system"] == "improved_multi_agent"), 0)
        orig_lat.append(o)
        impr_lat.append(i)

    x = np.arange(len(cases_short))
    width = 0.32

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(C_BG)

    b1 = ax.bar(x - width/2, orig_lat, width, color=C_ORIG, label="Original", zorder=3, alpha=0.9)
    b2 = ax.bar(x + width/2, impr_lat, width, color=C_IMPR, label="Improved", zorder=3, alpha=0.9)

    for bar, val in zip(b1, orig_lat):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.3, f"{val:.1f}",
                ha="center", va="bottom", fontsize=8, color="#333")
    for bar, val in zip(b2, impr_lat):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.3, f"{val:.1f}",
                ha="center", va="bottom", fontsize=8, color="#1a6e3c")

    # Mean lines
    ax.axhline(15.02, color=C_ORIG, linestyle="--", linewidth=1.2, alpha=0.6, label=f"Orig mean: 15.0 ms")
    ax.axhline(10.42, color=C_IMPR, linestyle="--", linewidth=1.2, alpha=0.6, label=f"Impr mean: 10.4 ms")

    styled_ax(ax, title="Figure 3 — Latency per Test Case (ms)", ylabel="Latency (ms)")
    ax.set_xticks(x)
    ax.set_xticklabels(cases_short, fontsize=10)
    ax.legend(fontsize=9, framealpha=0.9)
    fig.tight_layout(pad=1.5)
    path = os.path.join(OUT_DIR, "fig3_latency.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# 4. REQUIREMENT SCORE FOCUS CHART
# ═══════════════════════════════════════════════════════════════════
def chart_requirement_score():
    cases  = ["T1\nPilates", "T2\nAmbiguous", "T3\nOutdoor", "T4\nJewelry", "T5\nCaption", "T6\nTurkish", "T7\nText-only"]
    orig   = [1.0, 1.0, 1.0, 0.67, 1.0, 1.0, 1.0]
    impr   = [1.0, 1.0, 1.0, 1.00, 1.0, 1.0, 1.0]

    x = np.arange(len(cases))
    width = 0.32

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(C_BG)

    b1 = ax.bar(x - width/2, orig, width, color=C_ORIG, label="Original", zorder=3, alpha=0.9)
    b2 = ax.bar(x + width/2, impr, width, color=C_IMPR, label="Improved", zorder=3, alpha=0.9)

    for bar, val in zip(b1, orig):
        col = "#c0392b" if val < 1.0 else "#333"
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8.5, color=col, fontweight="bold")
    for bar, val in zip(b2, impr):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.2f}",
                ha="center", va="bottom", fontsize=8.5, color="#1a6e3c", fontweight="bold")

    # Arrow annotation for T4 gap
    ax.annotate("", xy=(3 + width/2, 1.00), xytext=(3 - width/2, 0.67),
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.5))
    ax.text(3.35, 0.82, "+0.33\nimprovement", fontsize=8, color="#c0392b", style="italic")

    styled_ax(ax, title="Figure 4 — Requirement Score per Test Case",
              ylabel="Requirement Score (0–1)")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, fontsize=9)
    ax.set_ylim(0, 1.25)
    ax.legend(fontsize=10, framealpha=0.9)
    fig.tight_layout(pad=1.5)
    path = os.path.join(OUT_DIR, "fig4_requirement_score.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# 5. PIPELINE FLOW DIAGRAM — Baseline vs Improved
# ═══════════════════════════════════════════════════════════════════
def draw_box(ax, cx, cy, text, color, text_color="white", width=2.2, height=0.55, fontsize=8.5):
    rect = mpatches.FancyBboxPatch(
        (cx - width/2, cy - height/2), width, height,
        boxstyle="round,pad=0.06", linewidth=1,
        edgecolor="#aaa", facecolor=color, zorder=3
    )
    ax.add_patch(rect)
    ax.text(cx, cy, text, ha="center", va="center",
            fontsize=fontsize, color=text_color, fontweight="bold", zorder=4)


def draw_arrow(ax, x1, y1, x2, y2, color="#666", label="", dashed=False):
    ls = "--" if dashed else "-"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, linestyle=ls),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.08, my, label, fontsize=7, color=color, style="italic")


def chart_pipeline_diagram():
    fig, axes = plt.subplots(1, 2, figsize=(14, 9))
    fig.patch.set_facecolor("#FAFAFA")

    # ── Colors ────────────────────────────────
    C_USER   = "#2C3E50"
    C_TM     = "#2980B9"
    C_AGENT  = "#16A085"
    C_QA     = "#8E44AD"
    C_BROW   = "#E67E22"
    C_NEW    = "#27AE60"
    C_GATE   = "#C0392B"

    # ── LEFT: Baseline ────────────────────────
    ax = axes[0]
    ax.set_facecolor("#FAFAFA")
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.3, 10.2)
    ax.axis("off")
    ax.set_title("Baseline Pipeline", fontsize=13, fontweight="bold", color="#1A1A2E", pad=10)

    cx = 2.5
    nodes_l = [
        (cx, 9.7,  "User Prompt",      C_USER),
        (cx, 8.7,  "Task Manager",     C_TM),
        (cx, 7.6,  "Researcher (cond.)",C_AGENT),
        (cx, 6.5,  "Writer",           C_AGENT),
        (cx, 5.4,  "Visual Prompt Eng.", C_AGENT),
        (cx, 4.3,  "Media Creator",    C_AGENT),
        (cx, 3.2,  "QA Agent",         C_QA),
        (cx, 2.1,  "Browser Operator", C_BROW),
        (cx, 1.0,  "✓ Published",      "#2ECC71"),
    ]
    for (x, y, txt, col) in nodes_l:
        draw_box(ax, x, y, txt, col)
    for i in range(len(nodes_l)-1):
        draw_arrow(ax, nodes_l[i][0], nodes_l[i][1]-0.28, nodes_l[i+1][0], nodes_l[i+1][1]+0.28)

    # Weakness annotation
    ax.text(4.0, 7.6, "⚠ No confidence\ncheck", fontsize=7.5, color="#E74C3C",
            ha="left", va="center", style="italic",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFF3F3", ec="#E74C3C", alpha=0.85))
    ax.text(4.0, 4.3, "⚠ Visual constraints\nnot verified", fontsize=7.5, color="#E74C3C",
            ha="left", va="center", style="italic",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFF3F3", ec="#E74C3C", alpha=0.85))

    # ── RIGHT: Improved ───────────────────────
    ax = axes[1]
    ax.set_facecolor("#FAFAFA")
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.3, 10.2)
    ax.axis("off")
    ax.set_title("Improved Pipeline", fontsize=13, fontweight="bold", color="#1A1A2E", pad=10)

    cx = 2.5
    nodes_r = [
        (cx, 9.7, "User Prompt",               C_USER),
        (cx, 8.7, "Request Brief Verifier",     C_NEW),   # NEW
        (cx, 7.7, "Confidence Gate",            C_GATE),  # NEW
        (cx, 6.7, "Improved Task Manager",      C_TM),
        (cx, 5.7, "Researcher / Writer",        C_AGENT),
        (cx, 4.7, "Visual Prompt Eng. + Inject",C_AGENT),
        (cx, 3.7, "Media Creator",              C_AGENT),
        (cx, 2.7, "QA + Requirement QA",        C_QA),    # NEW
        (cx, 1.7, "Browser Operator",           C_BROW),
        (cx, 0.7, "✓ Published",                "#2ECC71"),
    ]
    for (x, y, txt, col) in nodes_r:
        draw_box(ax, x, y, txt, col)
    for i in range(len(nodes_r)-1):
        draw_arrow(ax, nodes_r[i][0], nodes_r[i][1]-0.28, nodes_r[i+1][0], nodes_r[i+1][1]+0.28)

    # Clarification branch
    ax.text(4.3, 7.7, "Low confidence?\n→ Ask user", fontsize=7.5, color=C_GATE,
            ha="left", va="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFF0F0", ec=C_GATE, alpha=0.9))
    # QA repair loop
    ax.annotate("", xy=(1.1, 4.7), xytext=(1.1, 2.7),
                arrowprops=dict(arrowstyle="-|>", color=C_QA, lw=1.2, linestyle="--"))
    ax.text(0.05, 3.7, "Repair\nloop", fontsize=7.5, color=C_QA, ha="center", style="italic")

    # NEW label badges
    for badge_y in [8.7, 7.7, 2.7]:
        ax.text(4.5, badge_y, "NEW", fontsize=7, color="white", ha="center", va="center",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc=C_NEW, ec="none"))

    # Legend
    legend_items = [
        mpatches.Patch(color=C_NEW, label="New agents / improvements"),
        mpatches.Patch(color=C_GATE, label="Confidence gate"),
        mpatches.Patch(color=C_QA, label="QA layer"),
    ]
    fig.legend(handles=legend_items, loc="lower center", ncol=3, fontsize=9,
               framealpha=0.9, bbox_to_anchor=(0.5, 0.01))

    fig.suptitle("Figure 5 — System Architecture: Baseline vs Improved Pipeline",
                 fontsize=14, fontweight="bold", color="#1A1A2E", y=0.99)
    fig.tight_layout(rect=[0, 0.06, 1, 0.98])
    path = os.path.join(OUT_DIR, "fig5_pipeline_diagram.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# 6. SUMMARY RADAR / SPIDER CHART
# ═══════════════════════════════════════════════════════════════════
def chart_radar():
    categories = ["Overall\nScore", "Correctness", "Requirement\nScore",
                  "Completeness", "Reliability\n(1-FailRate)"]
    orig = [0.85, 0.85, 0.95, 0.86, 0.86]
    impr = [1.00, 1.00, 1.00, 1.00, 1.00]

    N = len(categories)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    orig_vals = orig + orig[:1]
    impr_vals = impr + impr[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    ax.plot(angles, orig_vals, "o-", linewidth=2, color=C_ORIG, label="Original")
    ax.fill(angles, orig_vals, alpha=0.18, color=C_ORIG)
    ax.plot(angles, impr_vals, "o-", linewidth=2, color=C_IMPR, label="Improved")
    ax.fill(angles, impr_vals, alpha=0.18, color=C_IMPR)

    ax.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=7.5, color="#666")
    ax.grid(color=C_GRID, linewidth=0.8)
    ax.set_title("Figure 6 — Performance Radar: Original vs Improved",
                 **FONT_TITLE, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=10)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig6_radar.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nGenerating Assignment 4 visuals → {OUT_DIR}\n")
    chart_aggregate()
    chart_per_test()
    chart_latency()
    chart_requirement_score()
    chart_pipeline_diagram()
    chart_radar()
    print(f"\n✅ All 6 visuals generated successfully!")
    print(f"   Location: {OUT_DIR}")
