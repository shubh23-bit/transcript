
import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)

from config import BASE_DIR


PDF_DIR = BASE_DIR / "storage" / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)


def safe_text(value) -> str:
    """Escape text before inserting it into a ReportLab paragraph."""
    return escape(str(value or "")).replace("\n", "<br/>")


def create_interview_pdf(data: dict, original_filename: str) -> Path:
    """Create and save an interview Q&A PDF."""

    title = str(data.get("title") or "Interview Study Notes")

    # Create a safe, predictable filename.
    stem = Path(original_filename).stem
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    safe_stem = safe_stem or "interview"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = PDF_DIR / f"{safe_stem}_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
        author="AI Interview Assistant",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=18,
    ))

    styles.add(ParagraphStyle(
        name="QuestionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#174A7E"),
        spaceBefore=12,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="SmallNote",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#555555"),
        fontSize=9,
        leading=13,
    ))

    story = []

    story.append(Paragraph(escape(title), styles["CoverTitle"]))
    story.append(Paragraph(
        f"Source video: {safe_text(original_filename)}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Interview Summary", styles["Heading1"]))
    story.append(Paragraph(
        safe_text(data.get("summary", "No summary available.")),
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Topics Covered", styles["Heading1"]))

    topics = data.get("topics", [])
    if topics:
        for topic in topics:
            story.append(Paragraph(
                f"&bull; {safe_text(topic)}",
                styles["BodyText"],
            ))
    else:
        story.append(Paragraph(
            "No topics identified.",
            styles["BodyText"],
        ))

    story.append(PageBreak())
    story.append(Paragraph(
        "Interview Questions & Answers",
        styles["Heading1"],
    ))

    questions = data.get("questions", [])

    if not questions:
        story.append(Paragraph(
            "No identifiable interview questions were found.",
            styles["BodyText"],
        ))

    for index, item in enumerate(questions, start=1):
        question = safe_text(item.get("question", "Question unavailable"))
        answer = safe_text(item.get("answer", "Answer unavailable"))
        answer_type = item.get("answer_type", "unknown")
        timestamp = safe_text(
            item.get("timestamp", "Not available")
        )

        if answer_type == "transcript_based":
            answer_label = "Answer based on transcript"
        elif answer_type == "ai_explanation":
            answer_label = "AI-generated explanation"
        else:
            answer_label = "Answer"

        section = [
            Paragraph(
                f"Q{index}. {question}",
                styles["QuestionHeading"],
            ),
            Paragraph(
                f"<b>{answer_label}:</b> {answer}",
                styles["BodyText"],
            ),
            Spacer(1, 4),
            Paragraph(
                f"<b>Video timestamp:</b> {timestamp}",
                styles["SmallNote"],
            ),
        ]

        key_points = item.get("key_points", [])
        if key_points:
            section.append(Spacer(1, 4))
            section.append(Paragraph(
                "<b>Key points</b>",
                styles["BodyText"],
            ))
            for point in key_points:
                section.append(Paragraph(
                    f"&bull; {safe_text(point)}",
                    styles["BodyText"],
                ))

        section.append(Spacer(1, 10))
        story.append(KeepTogether(section))

    story.append(PageBreak())
    story.append(Paragraph("Quick Revision Notes", styles["Heading1"]))

    revision_notes = data.get("revision_notes", [])
    if revision_notes:
        for note in revision_notes:
            story.append(Paragraph(
                f"&bull; {safe_text(note)}",
                styles["BodyText"],
            ))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph(
            "No revision notes available.",
            styles["BodyText"],
        ))

    doc.build(story)
    return output_path
