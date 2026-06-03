from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer


def markdown_to_story(md_text: str):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        "H3Custom",
        parent=styles["Heading3"],
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
    )
    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=normal_style,
        leftIndent=12,
    )
    code_style = ParagraphStyle(
        "CodeCustom",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=9,
        leading=11,
        backColor=colors.whitesmoke,
        borderColor=colors.lightgrey,
        borderWidth=0.5,
        borderPadding=6,
        borderRadius=2,
    )

    story = []
    in_code_block = False
    code_lines = []

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                story.append(Preformatted("\n".join(code_lines), code_style))
                story.append(Spacer(1, 6))
                in_code_block = False
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped == "---":
            story.append(Spacer(1, 8))
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:].strip(), title_style))
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(stripped[3:].strip(), h2_style))
            continue

        if stripped.startswith("### "):
            story.append(Paragraph(stripped[4:].strip(), h3_style))
            continue

        if stripped.startswith("- "):
            story.append(Paragraph(f"• {stripped[2:].strip()}", bullet_style))
            continue

        story.append(Paragraph(stripped, normal_style))

    return story


def main():
    source = Path("docs/assignment_report_tr.md")
    target = Path("docs/assignment_report_tr.pdf")
    md_text = source.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title="Agent-Based Systems Assignment",
    )
    story = markdown_to_story(md_text)
    doc.build(story)
    print(f"PDF generated: {target}")


if __name__ == "__main__":
    main()
