"""
YouTube DataOps & Analytics Platform (2026 Edition)
Architektur-Handbuch, Technisches Repertorium & Enterprise Dokumentation
Autor: Bernd Weltler
Erzeugt ein umfassendes, publikationsreifes PDF (25+ Seiten) mit ReportLab.
"""

import re
import io
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Flowable
)
from reportlab.pdfgen import canvas


def clean_rl_markup(text: str) -> str:
    """
    Konvertiert Markdown-Artefakte (**, `, [], <code>) zuverlässig in valides
    ReportLab-XML-Markup und stellt sicher, dass alle Zeichen in WinAnsi (cp1252)
    darstellbar sind (verhindert schwarze Kästchen bei Sonderzeichen wie ➔).
    """
    if not text:
        return ""

    # 1. Nicht-cp1252 Pfeile durch saubere cp1252-Äquivalente ersetzen
    text = text.replace("\u2794", "->").replace("\u2192", "->").replace("►", "->")
    text = text.replace("🟢", "[Aktiv]").replace("🟡", "[Legacy]").replace("🔴", "[Obsolet]").replace("⭐", "*")

    # 2. Markdown-Links [label](url) -> <font name="Courier">label</font>
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r'<font name="Courier">\1</font>', text)

    # 3. <code>...</code> -> <font name="Courier">...</font>
    text = re.sub(r"<code>(.*?)</code>", r'<font name="Courier">\1</font>', text, flags=re.DOTALL)

    # 4. **bold** -> <b>bold</b>
    text = re.sub(r"\*\*([^\*]+)\*\*", r"<b>\1</b>", text)

    # 5. `code` -> <font name="Courier">code</font> (mit Escaping von < und > innerhalb von Backticks)
    def repl_code(match):
        inner = match.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<font name="Courier">{inner}</font>'

    text = re.sub(r"`([^`]+)`", repl_code, text)

    # 6. Alleinstehende '&' (wie in 'Q&As' oder 'R&D') sauber als '&amp;' escapen
    text = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)

    # 7. Sicherheitsprüfung auf cp1252-Kompatibilität
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    return text


def P(text: str, style: ParagraphStyle) -> Paragraph:
    """Erzeugt einen typografisch bereinigten ReportLab Paragraph."""
    return Paragraph(clean_rl_markup(text), style)


def make_code_block(code_str: str, s: dict) -> Paragraph:
    """
    Formatiert mehrzeilige Code-Blöcke mit exakter Einrückung (&nbsp;)
    und Zeilenumbrüchen (<br/>) für ReportLab.
    """
    code_str = code_str.replace("\u2794", "->").replace("\u2192", "->")
    code_str = code_str.encode("cp1252", errors="replace").decode("cp1252")
    lines = []
    for line in code_str.strip("\n").split("\n"):
        escaped = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # Alle Leerzeichen durch geschützte Leerzeichen ersetzen, damit Einrückung exakt bleibt
        escaped = escaped.replace(" ", "&nbsp;")
        lines.append(escaped)
    formatted = "<br/>".join(lines)
    return Paragraph(formatted, s['code'])


class PageTracker(Flowable):
    """Zeichnet die exakte physische Seitenzahl eines Kapitels in Pass 1 auf."""
    def __init__(self, chapter_id, storage_dict):
        super().__init__()
        self.chapter_id = chapter_id
        self.storage_dict = storage_dict

    def draw(self):
        self.storage_dict[self.chapter_id] = self.canv._pageNumber


class NumberedCanvas(canvas.Canvas):
    """
    Zweiphasiger Canvas zur Berechnung der Gesamtseitenzahl und
    Erzeugung professioneller Kopf- und Fußzeilen ab Seite 2.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Deckblatt hat keine Kopf-/Fußzeile

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Laufende Kopfzeile
        header_text = "YouTube DataOps Platform (2026 Edition) — Enterprise Architektur-Handbuch"
        self.drawString(50, 842 - 36, header_text)
        self.setFont("Helvetica", 8)
        self.drawRightString(595 - 50, 842 - 36, "Release v2.1.0 (Serverless Cloud)")

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(50, 842 - 42, 595 - 50, 842 - 42)

        # Laufende Fußzeile
        self.line(50, 45, 595 - 50, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(50, 32, "CONFIDENTIAL & PROPRIETARY — DATAOPS REPERTORIUM — AUTOR: BERND WELTLER")
        page_str = f"Seite {self._pageNumber} von {page_count}"
        self.drawRightString(595 - 50, 32, page_str)

        self.restoreState()


def get_document_styles():
    """Definiert ein typografisch abgestimmtes, elegantes Farbschema und Schriftbild."""
    styles = getSampleStyleSheet()

    # Farbpalette
    c_primary = colors.HexColor("#0F172A")    # Deep Navy
    c_secondary = colors.HexColor("#0284C7")  # Bright Sky Blue
    c_accent = colors.HexColor("#0D9488")     # Dark Teal
    c_dark = colors.HexColor("#1E293B")       # Slate 800

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=c_primary,
        alignment=0,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=c_secondary,
        alignment=0,
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17.5,
        leading=22,
        textColor=c_primary,
        spaceBefore=16,
        spaceAfter=9,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16.5,
        textColor=c_secondary,
        spaceBefore=13,
        spaceAfter=5,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=c_dark,
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_dark,
        spaceAfter=6
    )

    body_bold = ParagraphStyle(
        'BodyBold_Custom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5,
        borderPadding=(6, 8, 6, 8),
        spaceBefore=5,
        spaceAfter=8,
        keepWithNext=False
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=body_style,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E3A8A"),
        backColor=colors.HexColor("#EFF6FF"),
        borderColor=colors.HexColor("#3B82F6"),
        borderWidth=1,
        borderPadding=(8, 10, 8, 10),
        spaceBefore=8,
        spaceAfter=10
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark,
        alignment=0
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'h1': h1_style,
        'h2': h2_style,
        'h3': h3_style,
        'body': body_style,
        'body_bold': body_bold,
        'bullet': bullet_style,
        'code': code_style,
        'callout': callout_style,
        'th': table_header,
        'td': table_cell,
        'td_bold': table_cell_bold,
        'primary': c_primary,
        'secondary': c_secondary,
        'accent': c_accent
    }


def make_callout(text, s, title="Architektur-Hinweis & Best Practice"):
    content = f"<b>{title}:</b><br/>{text}"
    return KeepTogether([P(content, s['callout'])])


def generate_story(s, chapter_pages=None, tracker_dict=None):
    if chapter_pages is None:
        chapter_pages = {}

    def track(ch_id):
        if tracker_dict is not None:
            return [PageTracker(ch_id, tracker_dict)]
        return []

    story = []

    # =========================================================================
    # DECKBLATT (COVER PAGE)
    # =========================================================================
    story.append(Spacer(1, 35))
    story.append(P("YouTube DataOps & Analytics Platform (2026 Edition)", s['title']))
    story.append(P(
        "Enterprise Architektur-Handbuch, Technisches Repertorium & Deep-Dive Dokumentation<br/>"
        "<i>Von Bare-Metal-Hadoop zu Serverless Cloud Lakehouse, Apache Iceberg V2 & DataOps</i>",
        s['subtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=3, color=s['secondary'], spaceAfter=25))

    meta_table_data = [
        [P("<b>Dokumenten-Typ:</b>", s['td_bold']), P("Enterprise Architecture Reference, Technical Repertorium & Operations Manual", s['td'])],
        [P("<b>Autor & Lead Architect:</b>", s['td_bold']), P("Bernd Weltler", s['td'])],
        [P("<b>Aktuelle Version:</b>", s['td_bold']), P("Release `v2.1.0` (Serverless Cloud & Observability) — inkl. `v1.0.0` & `v2.0.0` Historie", s['td'])],
        [P("<b>Status:</b>", s['td_bold']), P("Produktionsreif (100% Deployed, Getestet & Verifiziert)", s['td'])],
        [P("<b>GCP Projekt-ID:</b>", s['td_bold']), P("`cloudanalytics-514018` (Region: `europe-west3` Frankfurt / Location: `EU`)", s['td'])],
        [P("<b>Service Account:</b>", s['td_bold']), P("`cloudanalytics-514018@cloudanalytics-514018.iam.gserviceaccount.com`", s['td'])],
        [P("<b>GitHub Repository:</b>", s['td_bold']), P("`https://github.com/BHW80/DE_Capstone_2026.git`", s['td'])],
        [P("<b>Technologie-Stack:</b>", s['td_bold']), P("Google Cloud Pub/Sub (v2.1 Serverless Streaming), Apache Kafka KRaft (v1.0/v2.0), Apache Spark 3.5, Apache Iceberg V2, dbt Core 1.13, Google BigQuery, Terraform 1.17 (7 GCP Ressourcen), Google Cloud Workflows, Grafana Cloud, GitHub Actions", s['td'])],
    ]
    t_meta = Table(meta_table_data, colWidths=[145, 350])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 25))

    exec_summary_cover = (
        "<b>Executive Scope:</b> Dieses Handbuch dient als lückenloses Referenzwerk, Betriebshandbuch und Repertorium "
        "für die vollständige Modernisierung der YouTube Trending Video Data Pipeline. Es dokumentiert "
        "jede Architekturentscheidung (ADRs), die Migration von fragilen On-Premises-Altsystemen auf serverloses Cloud-Streaming "
        "(Google Cloud Pub/Sub in `v2.1.0` als Ablösung von lokalem Kafka) und Open Table Formats "
        "(Apache Iceberg V2), den Aufbau eines dimensionalen Data Warehouse nach Ralph Kimball (SCD-2 via dbt Core), "
        "das Infrastructure-as-Code-Design mit Terraform 1.17 (7 GCP-Ressourcen), den 0-€ Kostenvorteil serverloser Cloud Workflows, "
        "das cloud-native Observability-Konzept via Grafana Cloud sowie die GitHub Actions CI/CD-Automatisierung. "
        "Darüber hinaus stellt es die Prozesse für alle drei Releases (`v1.0.0`, `v2.0.0`, `v2.1.0`) in drei dedizierten Abschnitten "
        "gegenüber, beleuchtet kritisch 8 reale Risiken und Schwachstellen im Enterprise-Umfeld (inkl. TB/PB-Mitigationen) "
        "und bereitet mit 25 technischen Deep-Dive Interview-Fragen (Q&As) auf Senior/Lead-Architektur-Reviews vor."
    )
    story.append(P(exec_summary_cover, s['body']))
    story.append(PageBreak())

    # =========================================================================
    # INHALTSVERZEICHNIS (DYNAMISCH AUS PASS 1 BERECHNET)
    # =========================================================================
    story.append(P("Inhaltsverzeichnis", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=15))

    toc_data = [
        [P("<b>1. Management Summary & Strategisches Leitbild</b>", s['td_bold']), P(f"Seite {chapter_pages.get(1, '-')}", s['td'])],
        [P("<b>2. Die 3 Release-Prozesse im Detail (v1.0.0, v2.0.0, v2.1.0) & Notwendigkeits-Matrix</b>", s['td_bold']), P(f"Seite {chapter_pages.get(2, '-')}", s['td'])],
        [P("<b>3. End-to-End Systemarchitektur, Medallion Lakehouse & Repository-Struktur</b>", s['td_bold']), P(f"Seite {chapter_pages.get(3, '-')}", s['td'])],
        [P("<b>4. Streaming Ingestion & Resilienz (Cloud Pub/Sub v2.1 vs. Kafka KRaft, DLQ & SCD-2)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(4, '-')}", s['td'])],
        [P("<b>5. Ephemerer Compute & Open Table Format (Apache Iceberg V2)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(5, '-')}", s['td'])],
        [P("<b>6. Cloud Data Warehouse & Kimball Star-Schema (dbt Core & SCD-2)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(6, '-')}", s['td'])],
        [P("<b>7. DataOps Quality Gates: 15 dbt Tests & In-Workflow Validierung</b>", s['td_bold']), P(f"Seite {chapter_pages.get(7, '-')}", s['td'])],
        [P("<b>8. Infrastructure as Code (Terraform 1.17 Cloud Provisioning — 7 GCP Ressourcen)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(8, '-')}", s['td'])],
        [P("<b>9. Serverlose Orchestrierung (Google Cloud Workflows State-Machine)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(9, '-')}", s['td'])],
        [P("<b>10. Cloud-Native Observability (Grafana Cloud & GCP Monitoring - Weg 1)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(10, '-')}", s['td'])],
        [P("<b>11. DataOps CI/CD Pipelines, GitOps & Release-Management</b>", s['td_bold']), P(f"Seite {chapter_pages.get(11, '-')}", s['td'])],
        [P("<b>12. Architectural Decision Records (ADRs 001–007) & Kritische Enterprise-Risikoanalyse</b>", s['td_bold']), P(f"Seite {chapter_pages.get(12, '-')}", s['td'])],
        [P("<b>13. Deppensicheres Betriebshandbuch (9-Schritte-Anleitung & Playbooks)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(13, '-')}", s['td'])],
        [P("<b>14. Data Engineering Interview Masterclass & Technical Defense (25 Deep-Dive Q&As)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(14, '-')}", s['td'])],
        [P("<b>15. FinOps, Kosten-Engineering & Always-Free-Tier Kapazitätsplanung</b>", s['td_bold']), P(f"Seite {chapter_pages.get(15, '-')}", s['td'])],
    ]
    t_toc = Table(toc_data, colWidths=[430, 65])
    t_toc.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 1: MANAGEMENT SUMMARY & STRATEGISCHES LEITBILD
    # =========================================================================
    story.extend(track(1))
    story.append(P("1. Management Summary & Strategisches Leitbild", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Die moderne Datenlandschaft verlangt von Analytics-Plattformen heute weit mehr als das bloße "
        "Ausführen statischer SQL-Skripte oder nächtlicher Batch-Jobs. Unternehmen stehen vor der Herausforderung, "
        "kontinuierlich eintreffende Datenströme fehlertolerant aufzunehmen, fehlerhafte Events ohne Datenverlust "
        "zu isolieren, Datenänderungen historisch lückenlos nachzuvollziehen (SCD-2) und strenge analytische "
        "Qualitätsgarantien durchzusetzen — und das bei minimalen Betriebskosten.",
        s['body']
    ))
    story.append(P(
        "Das vorliegende Projekt **YouTube DataOps & Analytics Platform (2026 Edition)** demonstriert die "
        "vollständige Transformation eines wartungsintensiven universitären Legacy-Systems "
        "(Post Graduate Program in Data Engineering, Purdue University / Simplilearn 2021) über drei sauber getrennte "
        "Evolutions-Releases (`v1.0.0`, `v2.0.0`, `v2.1.0`) in eine cloud-native, serverlose Enterprise-Lösung.",
        s['body']
    ))

    story.append(P("Kernmetriken & Business Impact im Vergleich:", s['h2']))

    kpi_table_data = [
        [P("<b>Dimension</b>", s['th']), P("<b>Legacy-System (2021)</b>", s['th']), P("<b>DataOps Platform (2026 v2.1)</b>", s['th']), P("<b>Business & Tech Impact</b>", s['th'])],
        [
            P("<b>Monatliche Infrastrukturkosten</b>", s['td_bold']),
            P("Hohe VM-Kosten oder unkalkulierbare Cloud-Cluster", s['td']),
            P("<b>0,00 € laufende Idle-Kosten</b> (Cloud Pub/Sub, Cloud Workflows & GCP Free Tier)", s['td']),
            P("100% Kostensicherheit; keine 24/7 Kafka-VMs oder Composer-Gebühren (~300 €/Monat gespart)", s['td'])
        ],
        [
            P("<b>Streaming & Fehlertoleranz (DLQ)</b>", s['td_bold']),
            P("Lokaler Kafka+ZooKeeper; Pipeline bricht bei Fehlern ab", s['td']),
            P("<b>Serverless Cloud Pub/Sub</b> (`topic-youtube-ingest` + `topic-youtube-dlq`)", s['td']),
            P("Zero Data Loss ohne lokalen Broker: 444 Gutdaten + 56 korrupte Records (~10%) sauber getrennt", s['td'])
        ],
        [
            P("<b>Transaktionssicherheit (ACID)</b>", s['td_bold']),
            P("Flache Parquet-/CSV-Dateien (Gefahr von Teilabbrüchen)", s['td']),
            P("<b>Apache Iceberg V2</b> Table Format (`local.silver.videos`)", s['td']),
            P("Garantiert atomare Commits, Snapshot-Isolation, Manifest-Pruning & Time-Travel", s['td'])
        ],
        [
            P("<b>Historisierung & Auditfähigkeit</b>", s['td_bold']),
            P("SCD-1 (Alte Werte werden blind überschrieben)", s['td']),
            P("<b>SCD-2 Historisierung</b> via dbt Snapshots & Point-in-Time Joins", s['td']),
            P("Lückenlose Nachvollziehbarkeit mutierter Videotitel (`2kyS6SvSYSE`) über 3 Versionen", s['td'])
        ],
        [
            P("<b>Quality Assurance & Governance</b>", s['td_bold']),
            P("Keine automatisierten Datenprüfungen", s['td']),
            P("<b>15 dbt Data Tests + In-Workflow Foreign-Key Gate</b>", s['td']),
            P("Orphan Records und Schema-Drifts werden vor der BI-Freigabe hart blockiert (`raise`)", s['td'])
        ],
        [
            P("<b>Deployment & Reproduzierbarkeit</b>", s['td_bold']),
            P("Manuelle Windows-Klick-Anleitungen & Batch-Dateien", s['td']),
            P("<b>Terraform 1.17 IaC + GitHub Actions CI/CD</b>", s['td']),
            P("7 GCP-Ressourcen (inkl. Pub/Sub Topics & Subscriptions) in 60s reproduzierbar bereitgestellt", s['td'])
        ]
    ]
    t_kpi = Table(kpi_table_data, colWidths=[100, 115, 135, 145])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    story.append(make_callout(
        "Die fundamentale Prämisse dieser Plattform lautet: <b>Zero Idle Cost bei maximaler Produktionshärte</b>. "
        "In Release `v2.1.0` wurden sowohl der lokale Kafka-Broker (durch Google Cloud Pub/Sub) als auch der lokale "
        "Airflow-Cluster (durch Google Cloud Workflows) und der lokale Prometheus-Stack (durch Grafana Cloud) "
        "vollständig serverlos in die Cloud verlagert.",
        s, "Architektur-Prämisse"
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 2: DIE 3 RELEASE-PROZESSE IM DETAIL & NOTWENDIGKEITS-MATRIX
    # =========================================================================
    story.extend(track(2))
    story.append(P("2. Die 3 Release-Prozesse im Detail (v1.0.0, v2.0.0, v2.1.0) & Notwendigkeits-Matrix", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Dieses Kapitel stellt die exakten End-to-End-Prozessabläufe und Architekturen der drei Projektreleases "
        "(`v1.0.0`, `v2.0.0` und `v2.1.0`) in **drei eigenständigen Abschnitten** gegenüber und arbeitet präzise heraus, "
        "wie jede Evolutionsstufe die Engpässe ihres Vorgängers auflöst.",
        s['body']
    ))

    story.append(P("2.1 Ausgangslage: Die 2021 Legacy-Architektur (Historische Schmerzpunkte)", s['h2']))
    story.append(P("• <b>Windows OS-Inkompatibilität:</b> Lokale Hadoop/HDFS-Aufrufe scheiterten an Windows-Pfaden und erforderten inoffizielle `winutils.exe`-Binaries.", s['bullet']))
    story.append(P("• <b>ZooKeeper als Single Point of Failure:</b> Separate ZooKeeper-Prozesse führten unter Windows zu Verbindungsabbrüchen, Session-Timeouts und blockierten Kafka-Brokern.", s['bullet']))
    story.append(P("• <b>Fehlende Dead Letter Queue (DLQ):</b> Ein einziger korrupter Datensatz mit nicht-numerischen `views` brachte die gesamte Pipeline zum Absturz.", s['bullet']))
    story.append(P("• <b>SCD-1 Blindüberschreibung:</b> Änderungen an Videotiteln wurden ohne Historie überschrieben. Punktgenaue Analysen vor/nach Titeländerungen waren unmöglich.", s['bullet']))

    # -------------------------------------------------------------------------
    # ABSCHNITT 1: RELEASE v1.0.0
    # -------------------------------------------------------------------------
    story.append(P("2.2 Abschnitt 1: Prozess & Architektur in Release v1.0.0 (Core Foundation — Lokale Container-Pipeline)", s['h2']))
    story.append(P(
        "<b>Architektur-Ziel von `v1.0.0`:</b> Vollständige Eliminierung der Windows-Hadoop-Abhängigkeiten (`winutils.exe`) "
        "und des fehleranfälligen ZooKeeper-Dienstes durch eine rein lokale, containerisierte Medallion-Pipeline auf Basis "
        "von Docker Compose, Apache Kafka (KRaft) und PySpark.",
        s['body']
    ))
    story.append(P("<b>Der End-to-End-Prozess in Release `v1.0.0` (4 Prozessschritte):</b>", s['h3']))
    story.append(P("• <b>Prozessschritt 1 (Lokales Kafka KRaft Streaming & DLQ):</b> Start des lokalen Docker-Containers `de_kafka` (`start_kafka.ps1`) im ZooKeeper-losen KRaft-Modus auf `127.0.0.1:9092`. Der Producer (`run_producer.ps1` -> `src/producer.py`) liest `us_videos_mini_500.csv`, injiziert 10% korrupte Records (`views = 'CORRUPT_INVALID_NUMBER'`) und routet valide Daten in das lokale Kafka-Topic `topic_ingest` sowie fehlerhafte Daten in `topic_err`. Anschließend schreiben `run_bronze.ps1` (`src/consumer_bronze.py`) und `run_dlq.ps1` (`src/consumer_dlq.py`) lokale Parquet-Dateien nach `data/bronze/` bzw. `data/quarantine/`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 2 (Lokale PySpark Silver & Gold Transformation auf Parquet):</b> Der ephemere Spark-Container (`run_silver.ps1` -> `src/transform_silver.py`) führt die Typkonvertierung und den Broadcast-Join mit `US_category_id.json` aus und speichert flache Parquet-Dateien unter `data/silver/`. Danach berechnet `run_gold.ps1` (`src/transform_gold.py`) einfache Aggregationen (`channel_stats`, `category_stats`) als flache Parquet-Dateien unter `data/gold/`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 3 (Lokale Orchestrierung via Airflow 2.9):</b> Ein lokaler Airflow- und PostgreSQL-Container-Stack (`start_airflow.ps1` -> `docker/docker-compose-airflow.yml`) führt den DAG `dags/youtube_medallion_dag.py` auf Port `8085` aus.", s['bullet']))
    story.append(P("• <b>Prozessschritt 4 (Lokales Container-Monitoring):</b> Lokale Prometheus- und Grafana-Container (`start_monitoring.ps1` -> `docker/docker-compose-monitoring.yml`) überwachen die Container auf den Ports `9090` und `3000`.", s['bullet']))
    story.append(P(
        "<b>Architektonische Grenzen von `v1.0.0` (Warum `v2.0.0` nötig wurde):</b> Reine Parquet-Ordner bieten keine ACID-Transaktionen "
        "und kein Time-Travel; das flache Spark-Gold-Skript überschreibt Dimensionen blind nach **SCD-1** (keine Titel-Historie); "
        "und der gleichzeitige Betrieb von Kafka, Spark, Airflow, Postgres, Prometheus und Grafana belastet den lokalen Host mit 6+ Container-Daemons.",
        s['body']
    ))

    # -------------------------------------------------------------------------
    # ABSCHNITT 2: RELEASE v2.0.0
    # -------------------------------------------------------------------------
    story.append(P("2.3 Abschnitt 2: Prozess & Architektur in Release v2.0.0 (Lakehouse & Kimball Cloud DWH — Hybrid-Cloud)", s['h2']))
    story.append(P(
        "<b>Architektur-Ziel von `v2.0.0`:</b> Einführung eines echten Open Table Formats (**Apache Iceberg V2**) im Silver-Layer "
        "sowie Ablösung der starren Spark-Gold-Skripte durch ein cloud-basiertes **Kimball Star-Schema mit SCD-2 Historisierung** "
        "in **Google BigQuery** und **dbt Core**.",
        s['body']
    ))
    story.append(P("<b>Der End-to-End-Prozess in Release `v2.0.0` (4 Prozessschritte):</b>", s['h3']))
    story.append(P("• <b>Prozessschritt 1 (Lokales Kafka KRaft Streaming mit deterministischer SCD-2 Mutation):</b> Weiterhin über lokalen Docker-Kafka (`start_kafka.ps1`, `run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`), jedoch erweitert um die deterministische 3-stufige Titel- und Tag-Mutation für das Ziel-Video `2kyS6SvSYSE`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 2 (Silver Transformation in Apache Iceberg V2):</b> `run_silver.ps1` (`src/transform_silver.py`) bindet die `iceberg-spark-runtime-3.5` ein und schreibt die bereinigten Daten mit ACID-Garantie und Snapshot-Isolation in die Iceberg-Tabelle `local.silver.videos` (`data/iceberg_warehouse/silver/videos/`) sowie als Staging-Parquet nach `data/silver/`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 3 (Cloud-Brücke nach Google BigQuery):</b> `load_to_bigquery.ps1` (`src/cloud_loader_bigquery.py`) lädt die Silver-Parquet-Daten idempotent (`WRITE_TRUNCATE`) in die Tabelle `silver_videos` im BigQuery-Dataset `youtube_analytics` (Location `EU`).", s['bullet']))
    story.append(P("• <b>Prozessschritt 4 (dbt Core Kimball Star-Schema, SCD-2 Snapshot & 15 Tests):</b> `run_dbt.ps1 snapshot` führt `dim_video_snapshot` (`strategy='check'`) aus und historisiert alle 3 Titelversionen von `2kyS6SvSYSE` mit `valid_from`/`valid_to`. `run_dbt.ps1 run` baut das dimensionale Star-Schema (`dim_video`, `dim_category`, `dim_date` und `fact_video_metrics` mit Point-in-Time Join). `run_dbt.ps1 test` validiert 15 Schema- und Foreign-Key-Tests (`PASS=15`). Damit wird `run_gold.ps1` (`src/transform_gold.py`) in `v2.0.0` obsolet.", s['bullet']))
    story.append(P(
        "<b>Architektonische Grenzen von `v2.0.0` (Warum `v2.1.0` nötig wurde):</b> Das Streaming erforderte weiterhin einen lokal "
        "laufenden Docker-Kafka-Broker; Cloud-Ressourcen mussten noch manuell angelegt werden (kein Terraform IaC); und es fehlte "
        "eine serverlose Cloud-Orchestrierung sowie ein cloud-natives Monitoring ohne lokale Container.",
        s['body']
    ))

    # -------------------------------------------------------------------------
    # ABSCHNITT 3: RELEASE v2.1.0
    # -------------------------------------------------------------------------
    story.append(P("2.4 Abschnitt 3: Prozess & Architektur in Release v2.1.0 (Serverless Cloud & Observability — Aktuelle Produktion)", s['h2']))
    story.append(P(
        "<b>Architektur-Ziel von `v2.1.0`:</b> Vollständige Eliminierung aller dauerhaft laufenden Infrastruktur-Container durch "
        "**Terraform IaC (7 GCP-Ressourcen)**, **Serverless Google Cloud Pub/Sub** (löst lokales Docker-Kafka ab), "
        "**Serverless Google Cloud Workflows** (löst lokalen Airflow ab), **Grafana Cloud Weg 1** (löst lokalen Prometheus/Grafana ab) "
        "und **GitHub Actions CI/CD**.",
        s['body']
    ))
    story.append(P("<b>Der End-to-End-Prozess in Release `v2.1.0` (5 Prozessschritte):</b>", s['h3']))
    story.append(P("• <b>Prozessschritt 1 (Deklaratives Cloud-Provisioning via Terraform 1.17):</b> `run_infra.ps1 apply` rollt vollautomatisch **7 GCP-Ressourcen** in `cloudanalytics-514018` aus: GCS Lakehouse Bucket, BigQuery Dataset `youtube_analytics`, die beiden Pub/Sub Topics `topic-youtube-ingest` und `topic-youtube-dlq`, die zugehörigen Pull-Subscriptions `sub-youtube-ingest` und `sub-youtube-dlq` sowie den Cloud Workflow `youtube-dataops-pipeline`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 2 (Serverless Streaming & DLQ via Google Cloud Pub/Sub — Kein lokales Kafka mehr nötig!):</b> `run_pubsub_producer.ps1` (`src/cloud_pubsub_producer.py`) streamt die 500 Events aus `us_videos_mini_500.csv` per HTTPS/REST direkt in die Google Cloud: **444 valide Events** (inkl. der 3 SCD-2 Mutationen von `2kyS6SvSYSE`) gehen an `topic-youtube-ingest`, während **56 korrupte Events (~10%)** sofort in das Cloud-DLQ-Topic `topic-youtube-dlq` isoliert werden. `run_pubsub_bronze.ps1` (`src/cloud_pubsub_consumer_bronze.py`) und `run_pubsub_dlq.ps1` (`src/cloud_pubsub_consumer_dlq.py`) ziehen die Nachrichten per Pull-API aus `sub-youtube-ingest` bzw. `sub-youtube-dlq`, bestätigen sie per `acknowledge` und persistieren sie als Parquet unter `data/bronze/` und `data/quarantine/`.", s['bullet']))
    story.append(P("• <b>Prozessschritt 3 (Silver Iceberg V2, BigQuery Upload & dbt SCD-2 Star-Schema):</b> Wie in `v2.0.0` transformiert `run_silver.ps1` die Bronze-Daten in Apache Iceberg V2 (`local.silver.videos`), `load_to_bigquery.ps1` lädt sie nach BigQuery (`silver_videos`), und `run_dbt.ps1` (`snapshot`, `run`, `test`) baut und prüft das Kimball Star-Schema (15 Tests `PASS=15`).", s['bullet']))
    story.append(P("• <b>Prozessschritt 4 (Serverless Orchestrierung & In-Workflow Quality Gate via Cloud Workflows):</b> `run_workflow.ps1` (`src/cloud_workflow_runner.py`) triggert den Cloud Workflow `youtube-dataops-pipeline` in `europe-west3`. Dieser aktualisiert `fact_video_metrics` in BigQuery und führt direkt in der Cloud einen Foreign-Key-Orphan-Check (`LEFT JOIN` gegen `dim_video`) aus (`0 quality errors detected`).", s['bullet']))
    story.append(P("• <b>Prozessschritt 5 (Zero-Footprint Observability in Grafana Cloud & CI/CD):</b> Grafana Cloud liest über das native Google Cloud Monitoring Plugin (`stackdriver`) live die Metriken von Cloud Workflows, BigQuery und Cloud Pub/Sub (`topic-youtube-ingest` vs. `topic-youtube-dlq`) aus (`dashboards/youtube_dataops_monitoring.json`). Jede Codeänderung wird durch GitHub Actions (`.github/workflows/ci.yml` & `release.yml`) validiert.", s['bullet']))
    story.append(PageBreak())

    story.append(P("2.5 Evolutions- und Notwendigkeits-Matrix über alle Releases", s['h2']))

    matrix_data = [
        [P("<b>Kriterium</b>", s['th']), P("<b>2021 Legacy</b>", s['th']), P("<b>v1.0.0 (Foundation)</b>", s['th']), P("<b>v2.0.0 (Lakehouse)</b>", s['th']), P("<b>v2.1.0 (Aktuell)</b>", s['th'])],
        [
            P("<b>Bereitstellung</b>", s['td_bold']),
            P("Bare Metal Windows", s['td']),
            P("Docker Compose", s['td']),
            P("Docker + Python `.venv`", s['td']),
            P("<b>Terraform 1.17 (7 Res.)</b>", s['td'])
        ],
        [
            P("<b>Streaming Engine</b>", s['td_bold']),
            P("Kafka + ZooKeeper", s['td']),
            P("Lokales Kafka KRaft", s['td']),
            P("Lokales Kafka KRaft", s['td']),
            P("<b>Serverless Cloud Pub/Sub</b>", s['td'])
        ],
        [
            P("<b>Resilienz & DLQ</b>", s['td_bold']),
            P("Keine (Jobabbruch)", s['td']),
            P("Kafka `topic_err`", s['td']),
            P("Kafka `topic_err`", s['td']),
            P("<b>Pub/Sub `topic-youtube-dlq`</b>", s['td'])
        ],
        [
            P("<b>Storage Format</b>", s['td_bold']),
            P("Flache CSV-Dateien", s['td']),
            P("Snappy Parquet", s['td']),
            P("<b>Apache Iceberg V2</b>", s['td']),
            P("<b>Iceberg V2 + GCS Bucket</b>", s['td'])
        ],
        [
            P("<b>Datenmodellierung</b>", s['td_bold']),
            P("Unstrukturiert", s['td']),
            P("Flache Spark Gold Marts", s['td']),
            P("<b>Kimball Star-Schema</b>", s['td']),
            P("<b>Kimball + SCD-2 Marts</b>", s['td'])
        ],
        [
            P("<b>Historisierung</b>", s['td_bold']),
            P("Keine (SCD-1)", s['td']),
            P("Keine (SCD-1)", s['td']),
            P("<b>SCD-2 dbt Snapshots</b>", s['td']),
            P("<b>Point-in-Time Join DWH</b>", s['td'])
        ],
        [
            P("<b>Quality Gates</b>", s['td_bold']),
            P("Keine", s['td']),
            P("Basis Row-Count", s['td']),
            P("<b>15 dbt Data Tests</b>", s['td']),
            P("<b>15 Tests + Workflow Gate</b>", s['td'])
        ],
        [
            P("<b>Orchestrierung</b>", s['td_bold']),
            P("Manuelle Batch-Skripte", s['td']),
            P("Airflow 2.9 (Docker)", s['td']),
            P("PowerShell CLI Runner", s['td']),
            P("<b>Serverless Cloud Workflows</b>", s['td'])
        ],
        [
            P("<b>Observability</b>", s['td_bold']),
            P("Keine", s['td']),
            P("Lokaler Prometheus/Grafana", s['td']),
            P("Lokaler Container-Stack", s['td']),
            P("<b>Grafana Cloud (Weg 1)</b>", s['td'])
        ],
        [
            P("<b>CI/CD & Releases</b>", s['td_bold']),
            P("Keine", s['td']),
            P("Git Tag `v1.0.0`", s['td']),
            P("Git Tag `v2.0.0`", s['td']),
            P("<b>GitHub Actions (`v2.1.0`)</b>", s['td'])
        ]
    ]
    t_matrix = Table(matrix_data, colWidths=[90, 95, 100, 105, 105])
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 8))

    req_table_data = [
        [P("<b>Release</b>", s['th']), P("<b>Zwingend notwendig (Must-Have)</b>", s['th']), P("<b>Optional / Durch Cloud abgelöst (Nicht notwendig)</b>", s['th'])],
        [
            P("<b>Release v1.0.0</b><br/><i>(Core Foundation)</i>", s['td_bold']),
            P(
                "• Docker Desktop & Docker Compose<br/>"
                "• Lokaler Apache Kafka KRaft (`start_kafka.ps1`)<br/>"
                "• Lokaler Kafka Producer & Consumer (`run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`)<br/>"
                "• Ephemerer Docker PySpark (`run_silver.ps1`, `run_gold.ps1`)<br/>"
                "• Lokaler Airflow 2.9 Stack (`start_airflow.ps1`)<br/>"
                "• Lokaler Prometheus & Grafana Stack (`start_monitoring.ps1`)",
                s['td']
            ),
            P(
                "• <b>Kein GCP Cloud Account nötig</b> (100% lokal)<br/>"
                "• <b>Kein Cloud Pub/Sub, kein BigQuery, kein dbt Core</b><br/>"
                "• <b>Kein Apache Iceberg V2</b> (nur lose Parquet-Dateien)<br/>"
                "• <b>Kein Terraform, keine Cloud Workflows, keine Grafana Cloud</b>",
                s['td']
            )
        ],
        [
            P("<b>Release v2.0.0</b><br/><i>(Lakehouse & Kimball Marts)</i>", s['td_bold']),
            P(
                "• Python `.venv` + GCP Projekt & Service Account Key<br/>"
                "• Lokaler Apache Kafka KRaft (`start_kafka.ps1`, `run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`)<br/>"
                "• Apache Iceberg V2 im Spark-Container (`run_silver.ps1`)<br/>"
                "• BigQuery Loader (`load_to_bigquery.ps1`)<br/>"
                "• dbt Core Kimball Star-Schema, SCD-2 Snapshot & 15 Tests (`run_dbt.ps1`)",
                s['td']
            ),
            P(
                "• <b>Altes Spark Gold Script (`src/transform_gold.py`, `run_gold.ps1`):</b> Obsolet! Durch dbt Kimball Marts in BigQuery abgelöst.<br/>"
                "• <b>Noch nicht vorhanden:</b> Terraform, Cloud Pub/Sub, Cloud Workflows, Grafana Cloud, GitHub Actions CI/CD.",
                s['td']
            )
        ],
        [
            P("<b>Release v2.1.0</b><br/><i>(Serverless Cloud & Observability)</i><br/><b>[AKTUELLE PRODUKTION]</b>", s['td_bold']),
            P(
                "• Terraform 1.17 (`run_infra.ps1`: 7 GCP-Ressourcen)<br/>"
                "• <b>Serverless Google Cloud Pub/Sub</b> (`run_pubsub_producer.ps1`, `run_pubsub_bronze.ps1`, `run_pubsub_dlq.ps1`)<br/>"
                "• Ephemerer PySpark + Apache Iceberg V2 (`run_silver.ps1`)<br/>"
                "• BigQuery Loader (`load_to_bigquery.ps1`) & dbt Core (`run_dbt.ps1`)<br/>"
                "• <b>Serverless Cloud Workflow</b> (`run_workflow.ps1`)<br/>"
                "• <b>Grafana Cloud (Weg 1)</b> (`youtube_dataops_monitoring.json`)<br/>"
                "• GitHub Actions CI/CD (`ci.yml`, `release.yml`)",
                s['td']
            ),
            P(
                "• <b>Lokaler Docker-Kafka-Stack (`start_kafka.ps1`, `run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`):</b> "
                "<b>OPTIONAL / DURCH CLOUD PUB/SUB ABGELÖST!</b> Kein lokaler Kafka-Broker mehr nötig!<br/>"
                "• <b>Lokaler Airflow Stack (`start_airflow.ps1`, `dags/`):</b> <b>VOLLSTÄNDIG ÜBERFLÜSSIG!</b> Durch Cloud Workflows abgelöst.<br/>"
                "• <b>Lokaler Monitoring-Stack (`start_monitoring.ps1`):</b> <b>NICHT MEHR NÖTIG!</b> Durch Grafana Cloud abgelöst.<br/>"
                "• <b>Altes Spark Gold Script (`run_gold.ps1`):</b> Obsolet.",
                s['td']
            )
        ]
    ]
    t_req = Table(req_table_data, colWidths=[100, 195, 200])
    t_req.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_req)
    story.append(Spacer(1, 5))

    story.append(make_callout(
        "<b>Wichtige Betriebs-Leitlinie für Release v2.1.0 (Aktuell):</b> Für den regulären Betrieb in `v2.1.0` müssen "
        "<b>weder lokales Kafka (`start_kafka.ps1`), noch lokaler Airflow (`start_airflow.ps1`), noch lokales Monitoring (`start_monitoring.ps1`) gestartet werden!</b> "
        "Das Streaming läuft serverlos über **Google Cloud Pub/Sub** (`run_pubsub_producer.ps1` -> `run_pubsub_bronze.ps1` / `run_pubsub_dlq.ps1`), "
        "die Orchestrierung über **Cloud Workflows** (`run_workflow.ps1`) und das Monitoring über **Grafana Cloud**.",
        s, "Produktions-Leitlinie v2.1.0"
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 3: END-TO-END SYSTEMARCHITEKTUR & REPOSITORY-STRUKTUR
    # =========================================================================
    story.extend(track(3))
    story.append(P("3. End-to-End Systemarchitektur, Medallion Lakehouse & Repository-Struktur", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Die Plattform folgt dem **Medallion Lakehouse Architektur-Muster** (Bronze -> Silver -> Gold), "
        "kombiniert dieses jedoch mit modernem In-Warehouse ELT (Extract-Load-Transform) und dimensionaler "
        "Star-Schema-Modellierung nach Ralph Kimball.",
        s['body']
    ))

    story.append(P("3.1 Die 6 Datenfluss-Schichten im Detail (Stand Release v2.1.0)", s['h2']))

    story.append(P("<b>1. Raw Landing & Serverless Streaming Ingestion (Google Cloud Pub/Sub in v2.1 / Kafka KRaft in v1.0–v2.0):</b>", s['h3']))
    story.append(P(
        "In Release `v2.1.0` liest der serverlose Producer (`src/cloud_pubsub_producer.py` via `run_pubsub_producer.ps1`) "
        "das Sample `data/sample/us_videos_mini_500.csv` (500 Events) und publiziert diese per HTTPS/REST direkt an "
        "**Google Cloud Pub/Sub**: **444 valide Datensätze** fließen in `topic-youtube-ingest`, während **56 synthetisch "
        "korrumpierte Datensätze (~10% Fehlerrate)** direkt in das Dead-Letter-Queue-Topic `topic-youtube-dlq` geroutet werden. "
        "Für das Ziel-Video `2kyS6SvSYSE` mutiert der Producer deterministisch Titel und Tags über drei Trending-Tage. "
        "(Alternativ steht für Offline-Tests aus `v1.0`/`v2.0` weiterhin der lokale Kafka-KRaft-Producer `src/producer.py` bereit).",
        s['body']
    ))

    story.append(P("<b>2. Bronze & Quarantäne Persistenz (Cloud Pull-Subscriptions -> Micro-Batch Parquet):</b>", s['h3']))
    story.append(P(
        "Der Cloud-Bronze-Consumer (`src/cloud_pubsub_consumer_bronze.py` via `run_pubsub_bronze.ps1`) zieht die Nachrichten "
        "per Pull-API aus `sub-youtube-ingest`, bestätigt sie (`acknowledge`), ergänzt UTC-Audit-Metadaten (`_ingested_at`, "
        "`_kafka_offset`, `_kafka_partition`) und speichert Snappy-komprimierte Parquet-Dateien unter `data/bronze/`. "
        "Parallel isoliert `src/cloud_pubsub_consumer_dlq.py` (`run_pubsub_dlq.ps1`) alle fehlerhaften Nachrichten aus "
        "`sub-youtube-dlq` inklusive `_quarantine_at` und `_error_reason` unter `data/quarantine/`.",
        s['body']
    ))

    story.append(P("<b>3. Silver Layer: Apache Iceberg V2 & Broadcast-Transformation:</b>", s['h3']))
    story.append(P(
        "Ein ephemerer PySpark-Container (`de_spark`, `src/transform_silver.py`) liest die Bronze-Parquet-Dateien, "
        "konvertiert Datentypen (`views`, `likes`, `dislikes`, `comment_count` nach `long`; `trending_date` von `yy.dd.MM` "
        "nach `DATE`; `publish_time` nach `TIMESTAMP`) und führt einen Zero-Shuffle Broadcast-Join mit `data/raw/US_category_id.json` "
        "durch. Das Ergebnis wird im Dual-Write-Verfahren atomar in die **Apache Iceberg V2 Tabelle** `local.silver.videos` "
        "(`data/iceberg_warehouse/silver/videos/`) sowie als Parquet-Snapshot nach `data/silver/` geschrieben.",
        s['body']
    ))

    story.append(P("<b>4. Cloud Ingestion & Google BigQuery Staging:</b>", s['h3']))
    story.append(P(
        "Das Skript `src/cloud_loader_bigquery.py` (`load_to_bigquery.ps1`) lädt die bereinigten Silver-Parquet-Daten "
        "idempotent (`WRITE_TRUNCATE`) in die Quelltabelle `silver_videos` im BigQuery-Dataset `youtube_analytics` (Location `EU`).",
        s['body']
    ))

    story.append(P("<b>5. Gold Layer & Kimball Star-Schema (dbt Core):</b>", s['h3']))
    story.append(P(
        "**dbt Core** (`run_dbt.ps1`) übernimmt die In-Warehouse-Transformation in BigQuery: Über den idempotenten Staging-View "
        "`stg_videos` und den SCD-2 Snapshot `dim_video_snapshot` entstehen die Dimensionstabellen `dim_video`, `dim_category` "
        "und `dim_date` sowie die Faktentabelle `fact_video_metrics` (mit Point-in-Time Join). Anschließend sichern "
        "15 automatisierte dbt-Tests die Datenqualität ab.",
        s['body']
    ))

    story.append(P("<b>6. Serverless Orchestrierung & Cloud Observability:</b>", s['h3']))
    story.append(P(
        "Der per Terraform bereitgestellte Google Cloud Workflow `youtube-dataops-pipeline` (`run_workflow.ps1`) "
        "aktualisiert `fact_video_metrics` serverlos in BigQuery und prüft über ein In-Workflow Quality Gate, dass "
        "exakt 0 verwaiste Fremdschlüssel (Orphan Records) existieren. Sämtliche Laufzeit-, Kosten- und Streaming-Metriken "
        "werden ohne lokale Daemons direkt in **Grafana Cloud** (`dashboards/youtube_dataops_monitoring.json`) visualisiert.",
        s['body']
    ))

    story.append(P("3.2 Vollständige Repository-Struktur mit Versions-Zuordnung", s['h2']))
    repo_tree_code = (
        "DE_Capstone_2026/\n"
        "|-- .github/workflows/                    # [v2.1 Active] CI/CD Automation (GitHub Actions)\n"
        "|   |-- ci.yml                            # [v2.1 Active] Syntax-, Flake8-, YAML- & JSON-Validierung\n"
        "|   +-- release.yml                       # [v2.1 Active] Automatische GitHub Releases bei Tag-Push (v*)\n"
        "|-- dashboards/                           # [v2.1 Active] Observability-as-Code\n"
        "|   +-- youtube_dataops_monitoring.json   # [v2.1 Active] Grafana Cloud Dashboard (Plugin: stackdriver)\n"
        "|-- docs/                                 # [v2.1 Active] Enterprise Dokumentation & Handbuch\n"
        "|   +-- YouTube_DataOps_Platform_2026_Architektur_Repertorium.pdf\n"
        "|-- dags/                                 # [v1.0 Legacy] Lokale Airflow DAGs (abgeloest durch Workflows)\n"
        "|-- dbt/                                  # [v2.0 Active] Cloud DWH Transformationen (Kimball & SCD-2)\n"
        "|   |-- dbt_project.yml & profiles.yml    # [v2.0 Active] dbt Konfiguration & BigQuery EU-Profil\n"
        "|   |-- snapshots/dim_video_snapshot.sql  # [v2.0 Active] SCD-2 Snapshot (check_cols: title, tags, ...)\n"
        "|   +-- models/\n"
        "|       |-- staging/stg_videos.sql        # [v2.0 Active] Idempotente Deduplizierung & Typisierung View\n"
        "|       +-- marts/core/                   # [v2.0 Active] Kimball Star-Schema Marts & 15 Tests\n"
        "|           |-- dim_video.sql             # [v2.0 Active] SCD-2 Dimension mit valid_from/to & is_current\n"
        "|           |-- dim_category.sql          # [v2.0 Active] Conformed Kategorie-Dimension\n"
        "|           |-- dim_date.sql              # [v2.0 Active] Kalender-Dimension (is_weekend, day_name)\n"
        "|           |-- fact_video_metrics.sql    # [v2.0 Active] Fakten mit Point-in-Time SCD-2 Join\n"
        "|           +-- schema.yml                # [v2.0 Active] 15 automatisierte dbt Quality Gate Tests\n"
        "|-- infra/                                # [v2.1 Active] Infrastructure as Code (Terraform 1.17)\n"
        "|   |-- versions.tf, variables.tf, main.tf# [v2.1 Active] 7 GCP Ressourcen (GCS, BQ, 2x Topic, 2x Sub, Workflow)\n"
        "|   +-- workflows/pipeline.yaml           # [v2.1 Active] Serverless Cloud Workflow State-Machine\n"
        "|-- docker/                               # Modulare Docker Compose Definitionen\n"
        "|   |-- docker-compose-spark.yml          # [v2.0 Active] Ephemerer PySpark + Iceberg V2 Container\n"
        "|   |-- docker-compose-kafka.yml          # [v1.0/v2.0 Legacy] Lokaler Kafka KRaft (in v2.1 durch Pub/Sub ersetzt)\n"
        "|   |-- docker-compose-airflow.yml        # [v1.0 Legacy] Alter Airflow 2.9 & Postgres Stack\n"
        "|   +-- docker-compose-monitoring.yml     # [v1.0 Legacy] Alter lokaler Prometheus/Grafana Stack\n"
        "|-- src/                                  # Python Quellcode\n"
        "|   |-- cloud_pubsub_producer.py          # [v2.1 Active] Serverless GCP Pub/Sub Producer (10% DLQ + SCD-2)\n"
        "|   |-- cloud_pubsub_consumer_bronze.py   # [v2.1 Active] Serverless Pull-Consumer (sub-youtube-ingest -> Bronze)\n"
        "|   |-- cloud_pubsub_consumer_dlq.py      # [v2.1 Active] Serverless Pull-Consumer (sub-youtube-dlq -> Quarantine)\n"
        "|   |-- producer.py                       # [v1.0/v2.0 Legacy] Lokaler Kafka Producer (optional fuer Offline-Tests)\n"
        "|   |-- consumer_bronze.py & consumer_dlq.py # [v1.0/v2.0 Legacy] Lokale Kafka Consumer\n"
        "|   |-- transform_silver.py               # [v2.0 Active] PySpark Broadcast-Join & Apache Iceberg V2\n"
        "|   |-- transform_gold.py                 # [v1.0 Legacy] Altes Spark-Gold (abgeloest durch dbt)\n"
        "|   |-- cloud_loader_bigquery.py          # [v2.0 Active] Idempotenter BigQuery Parquet Uploader\n"
        "|   |-- cloud_workflow_runner.py          # [v2.1 Active] REST-Trigger & Live-Poller fuer Cloud Workflows\n"
        "|   +-- generate_repertorium_pdf.py       # [v2.1 Active] ReportLab Generator fuer das PDF-Repertorium\n"
        "+-- *.ps1 Runner-Skripte                  # [v2.1 Active] Kapselung aller CLI-Aufrufe fuer PowerShell"
    )
    story.append(make_code_block(repo_tree_code, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 4: STREAMING INGESTION & RESILIENZ (CLOUD PUB/SUB VS. KAFKA KRAFT)
    # =========================================================================
    story.extend(track(4))
    story.append(P("4. Streaming Ingestion & Resilienz (Cloud Pub/Sub v2.1 vs. Kafka KRaft, DLQ & SCD-2)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "In produktiven DataOps-Architekturen ist unkontrollierter Datenverlust inakzeptabel. "
        "Gleichzeitig darf ein korrupter Datensatz niemals die gesamte Ingestion-Pipeline blockieren ('Poison Pill Problem'). "
        "Dieses Kapitel erläutert den Evolutionssprung vom lokalen **Apache Kafka KRaft Broker** (`v1.0.0` / `v2.0.0`) "
        "hin zum vollständig serverlosen **Google Cloud Pub/Sub Streaming-Layer** in Release `v2.1.0`.",
        s['body']
    ))

    story.append(P("4.1 Warum ist Kafka in Release v2.1.0 optional? (Ablösung durch Google Cloud Pub/Sub)", s['h2']))
    story.append(P(
        "In den Releases `v1.0.0` und `v2.0.0` lief lokal ein Docker-Container mit Apache Kafka im ZooKeeper-losen "
        "**KRaft-Modus** (`docker/docker-compose-kafka.yml`, `127.0.0.1:9092`). Obwohl KRaft gegenüber dem alten "
        "ZooKeeper-Setup aus 2021 bereits eine massive Verbesserung darstellte, blieb ein entscheidender Nachteil bestehen: "
        "Ein Kafka-Broker belegt dauerhaft lokalen Arbeitsspeicher und ist für Cloud-Dienste (wie Grafana Cloud) nicht nativ sichtbar.",
        s['body']
    ))
    story.append(P(
        "In **Release `v2.1.0`** übernimmt deshalb **Google Cloud Pub/Sub** das gesamte Event-Streaming serverlos in der Cloud:",
        s['body']
    ))
    story.append(P("• <b>Keine lokale Broker-Infrastruktur nötig:</b> `start_kafka.ps1` muss in `v2.1.0` nicht mehr gestartet werden. Alle Nachrichten fließen verschlüsselt per HTTPS/REST direkt an `pubsub.googleapis.com`.", s['bullet']))
    story.append(P("• <b>Deklarative Bereitstellung per Terraform:</b> `infra/main.tf` provisioniert automatisch die beiden Topics `topic-youtube-ingest` und `topic-youtube-dlq` sowie die beiden Pull-Subscriptions `sub-youtube-ingest` und `sub-youtube-dlq` (7 Tage Retention, 60s Ack-Deadline).", s['bullet']))
    story.append(P("• <b>Native Cloud-Observability in Grafana Cloud:</b> Jeder Publish-Aufruf erzeugt automatisch die GCP-Systemmetrik `pubsub.googleapis.com/topic/send_message_operation_count`, die in Panel 3 und Panel 7 des Grafana-Cloud-Dashboards live nach `topic-youtube-ingest` vs. `topic-youtube-dlq` aufgeschlüsselt wird.", s['bullet']))

    story.append(P("4.2 Die Resilienz-Architektur: 10% Fault-Injection, DLQ & Deterministische SCD-2 Mutation", s['h2']))
    story.append(P(
        "Der serverlose Producer (`src/cloud_pubsub_producer.py` via `run_pubsub_producer.ps1`) liest alle **500 Datensätze** "
        "aus `data/sample/us_videos_mini_500.csv`, kodiert jedes JSON-Payload in Base64 und sendet es in gebündelten "
        "REST-Batches an Google Cloud Pub/Sub:",
        s['body']
    ))
    story.append(P("• <b>Sauberer Hauptstrom (`topic-youtube-ingest` -> `sub-youtube-ingest`):</b> Im verifizierten Live-Lauf wurden **444 valide Events** publiziert, von `src/cloud_pubsub_consumer_bronze.py` (`run_pubsub_bronze.ps1`) per Pull-API abgerufen, per `acknowledge` bestätigt und als `data/bronze/bronze_videos_*.parquet` (90,0 KB) gespeichert.", s['bullet']))
    story.append(P("• <b>10% Fault-Injection & Dead Letter Queue (`topic-youtube-dlq` -> `sub-youtube-dlq`):</b> Mit `ERROR_RATE = 0.10` wurden **56 korrupte Events** (`views = 'CORRUPT_INVALID_NUMBER'`) in das Cloud-DLQ-Topic isoliert und von `src/cloud_pubsub_consumer_dlq.py` (`run_pubsub_dlq.ps1`) nach `data/quarantine/quarantine_videos_*.parquet` (26,3 KB) geschrieben.", s['bullet']))
    story.append(P("• <b>Deterministische SCD-2 Mutation (`2kyS6SvSYSE`):</b> Das Zielvideo `2kyS6SvSYSE` ist von der Fault-Injection ausgenommen und durchläuft über drei Trending-Tage deterministisch drei Titel- und Tag-Mutationen (`Original` -> `(Official Update)` -> `[THE TRUTH]`).", s['bullet']))

    story.append(P("Original-Codeausschnitt aus `src/cloud_pubsub_producer.py` (v2.1 Serverless Streaming):", s['h3']))
    code_producer = (
        "# src/cloud_pubsub_producer.py (Original-Auszug: Serverless GCP Pub/Sub Producer)\n"
        "PROJECT_ID = \"cloudanalytics-514018\"\n"
        "TOPIC_INGEST = \"topic-youtube-ingest\"\n"
        "TOPIC_DLQ = \"topic-youtube-dlq\"\n"
        "SCD2_TARGET_VIDEO_ID = \"2kyS6SvSYSE\"\n\n"
        "for row in reader:\n"
        "    vid = row.get(\"video_id\", \"\")\n"
        "    if vid == SCD2_TARGET_VIDEO_ID:\n"
        "        scd2_occurrence_count += 1\n"
        "        if scd2_occurrence_count in SCD2_MUTATIONS:\n"
        "            row.update(SCD2_MUTATIONS[scd2_occurrence_count])\n\n"
        "    if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE:\n"
        "        corrupted_row = dict(row)\n"
        "        corrupted_row[\"views\"] = \"CORRUPT_INVALID_NUMBER\"\n"
        "        corrupted_row[\"_error_reason\"] = \"Simulated fault injection: non-numeric views\"\n"
        "        dlq_batch.append(corrupted_row)\n"
        "    else:\n"
        "        clean_batch.append(row)\n\n"
        "# Publiziert Base64-kodierte Nachrichten per HTTPS POST an pubsub.googleapis.com\n"
        "publish_batch(session, TOPIC_INGEST, clean_batch)\n"
        "publish_batch(session, TOPIC_DLQ, dlq_batch)"
    )
    story.append(make_code_block(code_producer, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 5: EPHEMERER COMPUTE & OPEN TABLE FORMAT (APACHE ICEBERG V2)
    # =========================================================================
    story.extend(track(5))
    story.append(P("5. Ephemerer Compute & Open Table Format (Apache Iceberg V2)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Im Zeitalter moderner Cloud Lakehouses reichen lose Parquet-Dateien im Object Store für produktive "
        "Workloads nicht mehr aus. Unternehmen benötigen ACID-Transaktionen, Snapshot-Isolation, Schema-Evolution "
        "und Time-Travel. Dieses Kapitel beschreibt die Implementierung des Silver-Layers mit PySpark 3.5 und "
        "**Apache Iceberg V2** (`src/transform_silver.py`).",
        s['body']
    ))

    story.append(P("5.1 Warum lose Parquet-Dateien in Produktion scheitern", s['h2']))
    story.append(P(
        "Parquet ist ein exzellentes spaltenorientiertes Dateiformat — aber ein Ordner voller Parquet-Dateien ist **keine Datenbanktabelle**:",
        s['body']
    ))
    story.append(P("• <b>Fehlende Atomarität (Dirty Reads):</b> Bricht ein Spark-Schreibjob nach 40 von 50 Parquet-Dateien ab, bleibt ein halb geschriebenes, korruptes Verzeichnis zurück.", s['bullet']))
    story.append(P("• <b>Teures Directory Listing `O(N)`:</b> Abfrage-Engines müssen bei losen Dateien langsame Dateisystem-Listings (`listStatus`) über alle Unterordner ausführen.", s['bullet']))
    story.append(P("• <b>Kein Time-Travel & kein sicheres Schema-Update:</b> Überschriebene Parquet-Dateien sind unwiderruflich verloren; Spaltenumbenennungen brechen bestehende Leser.", s['bullet']))

    story.append(P("5.2 Die Apache Iceberg V2 Metadaten-Hierarchie (`local.silver.videos`)", s['h2']))

    iceberg_arch_data = [
        [P("<b>Metadaten-Ebene</b>", s['th']), P("<b>Physischer Pfad im Projekt</b>", s['th']), P("<b>Funktion & ACID-Mechanismus</b>", s['th'])],
        [
            P("<b>Iceberg Catalog</b>", s['td_bold']),
            P("`spark.sql.catalog.local`<br/>(`type = hadoop`)", s['td']),
            P("Verwaltet den atomaren Zeiger auf die aktuelle `vN.metadata.json` im Warehouse `/app/data/iceberg_warehouse`.", s['td'])
        ],
        [
            P("<b>Table Metadata</b>", s['td_bold']),
            P("`silver/videos/metadata/`<br/>`v1.metadata.json`", s['td']),
            P("Speichert das Tabellen-Schema (Field-IDs), Partitionsspezifikationen und die vollständige Snapshot-Historie.", s['td'])
        ],
        [
            P("<b>Manifest List</b>", s['td_bold']),
            P("`silver/videos/metadata/`<br/>`snap-*.avro`", s['td']),
            P("Verzeichnet alle Manifest-Dateien eines einzelnen Commits inkl. Partitions-Statistiken für schnelles Pruning.", s['td'])
        ],
        [
            P("<b>Manifest Files</b>", s['td_bold']),
            P("`silver/videos/metadata/`<br/>`*-m0.avro`", s['td']),
            P("Trackt jede einzelne Parquet-Datendatei mit Zeilenanzahl und Spalten-Min/Max-Werten (Data Skipping).", s['td'])
        ],
        [
            P("<b>Data Files</b>", s['td_bold']),
            P("`silver/videos/data/`<br/>`*.parquet`", s['td']),
            P("Die Snappy-komprimierten, typisierten und per Broadcast-Join angereicherten YouTube-Events.", s['td'])
        ]
    ]
    t_iceberg = Table(iceberg_arch_data, colWidths=[105, 140, 250])
    t_iceberg.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_iceberg)
    story.append(Spacer(1, 8))

    story.append(P("5.3 Ephemerer Spark Compute, Broadcast-Join & Dual-Write", s['h2']))
    story.append(P(
        "Über `run_silver.ps1` wird der Container `de_spark` (`docker/docker-compose-spark.yml`) on-demand gestartet, "
        "führt `src/transform_silver.py` aus und beendet sich danach sofort wieder (0 € Idle-Ressourcen). "
        "Dabei liest Spark die Kategorie-Referenz `data/raw/US_category_id.json` und erzwingt über `broadcast(df_categories)` "
        "einen **Zero-Shuffle Broadcast-Join** im Arbeitsspeicher. Anschließend schreibt der Job sowohl atomar in die "
        "Iceberg-Tabelle `local.silver.videos` als auch nach `/app/data/silver`, damit `src/cloud_loader_bigquery.py` "
        "die Daten nahtlos nach BigQuery hochladen kann:",
        s['body']
    ))

    code_silver = (
        "# src/transform_silver.py (Original-Auszug: Iceberg Session, Broadcast Join & Commit)\n"
        "def create_spark_session():\n"
        "    return (\n"
        "        SparkSession.builder.appName(\"DE_Capstone_Silver_Iceberg\").master(\"local[*]\")\n"
        "        .config(\"spark.sql.extensions\", \"org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions\")\n"
        "        .config(\"spark.sql.catalog.local\", \"org.apache.iceberg.spark.SparkCatalog\")\n"
        "        .config(\"spark.sql.catalog.local.type\", \"hadoop\")\n"
        "        .config(\"spark.sql.catalog.local.warehouse\", \"/app/data/iceberg_warehouse\")\n"
        "        .getOrCreate()\n"
        "    )\n\n"
        "# Typisierung & Datums-Harmonisierung ('17.14.11' -> yy.dd.MM)\n"
        "df_cleaned = (\n"
        "    df_bronze.withColumn(\"category_id\", col(\"category_id\").cast(\"string\"))\n"
        "    .withColumn(\"views\", col(\"views\").cast(\"long\"))\n"
        "    .withColumn(\"likes\", col(\"likes\").cast(\"long\"))\n"
        "    .withColumn(\"dislikes\", col(\"dislikes\").cast(\"long\"))\n"
        "    .withColumn(\"comment_count\", col(\"comment_count\").cast(\"long\"))\n"
        "    .withColumn(\"publish_time\", to_timestamp(col(\"publish_time\")))\n"
        "    .withColumn(\"trending_date\", to_date(col(\"trending_date\"), \"yy.dd.MM\"))\n"
        ")\n\n"
        "# Zero-Shuffle Broadcast Join & atomarer Apache Iceberg V2 Commit\n"
        "df_silver = df_cleaned.join(broadcast(df_categories), on=\"category_id\", how=\"left\").na.fill({\"category_name\": \"Unknown\"})\n"
        "df_silver.writeTo(\"local.silver.videos\").createOrReplace()\n"
        "spark.read.table(\"local.silver.videos.history\").show(truncate=False)"
    )
    story.append(make_code_block(code_silver, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 6: CLOUD DWH & KIMBALL STAR-SCHEMA (DBT & SCD-2)
    # =========================================================================
    story.extend(track(6))
    story.append(P("6. Cloud Data Warehouse & Kimball Star-Schema (dbt Core & SCD-2)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Nachdem `src/cloud_loader_bigquery.py` (`load_to_bigquery.ps1`) die 295 bereinigten Silver-Events per "
        "`WRITE_TRUNCATE` als Quelltabelle `silver_videos` in das BigQuery-Dataset `youtube_analytics` (Location `EU`) "
        "geladen hat, übernimmt **dbt Core 1.13** (`run_dbt.ps1`) die In-Warehouse-Transformation (ELT) in ein "
        "dimensionales **Star-Schema nach Ralph Kimball**.",
        s['body']
    ))

    story.append(P("6.1 Die 6 dbt-Artefakte im BigQuery Dataset `youtube_analytics`", s['h2']))

    dwh_table_data = [
        [P("<b>Modell / Tabelle</b>", s['th']), P("<b>Materialisierung</b>", s['th']), P("<b>Primär-/Surrogate-Key</b>", s['th']), P("<b>Pfad & Transformations-Logik</b>", s['th'])],
        [
            P("<b>stg_videos</b>", s['td_bold']),
            P("View", s['td']),
            P("`video_id` + `trending_date`", s['td']),
            P("`models/staging/stg_videos.sql`: Trimming von Strings, Casting auf `INT64`, `DATE` und `TIMESTAMP`, Filter `video_id is not null`.", s['td'])
        ],
        [
            P("<b>dim_video_snapshot</b>", s['td_bold']),
            P("SCD-2 Snapshot Table", s['td']),
            P("`dbt_scd_id` (MD5)", s['td']),
            P("`snapshots/dim_video_snapshot.sql`: Überwacht `['title', 'channel_title', 'category_id', 'tags']` via `strategy='check'`.", s['td'])
        ],
        [
            P("<b>dim_video</b>", s['td_bold']),
            P("Table (Dimension)", s['td']),
            P("`video_key` (`dbt_scd_id`)", s['td']),
            P("`models/marts/core/dim_video.sql`: Exponiert `video_key`, `valid_from`, `valid_to` und berechnet das Flag `is_current`.", s['td'])
        ],
        [
            P("<b>dim_category</b>", s['td_bold']),
            P("Table (Conformed Dim)", s['td']),
            P("`category_key` (`INT64`)", s['td']),
            P("`models/marts/core/dim_category.sql`: Deduplizierte Kategorie-Dimension (`category_key`, `category_id`, `category_name`).", s['td'])
        ],
        [
            P("<b>dim_date</b>", s['td_bold']),
            P("Table (Date Spine)", s['td']),
            P("`date_key` (`YYYYMMDD`)", s['td']),
            P("`models/marts/core/dim_date.sql`: Berechnet `year`, `month`, `month_name`, `day`, `day_of_week`, `day_name` und `is_weekend`.", s['td'])
        ],
        [
            P("<b>fact_video_metrics</b>", s['td_bold']),
            P("Table (Fact Table)", s['td']),
            P("`metric_key` (MD5 Hex)", s['td']),
            P("`models/marts/core/fact_video_metrics.sql`: Tägliche Kennzahlen, `interaction_ratio` und Point-in-Time Join auf `dim_video`.", s['td'])
        ]
    ]
    t_dwh = Table(dwh_table_data, colWidths=[95, 85, 105, 210])
    t_dwh.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_dwh)
    story.append(Spacer(1, 8))

    story.append(P("6.2 Deep Dive: SCD-2 Snapshot (`dim_video_snapshot.sql`) & Deduplizierung", s['h2']))
    story.append(P(
        "Da ein Video im Streaming-Batch mehrfach vorkommen kann, dedupliziert der Snapshot die Quelle mittels "
        "`qualify row_number() over (partition by video_id order by trending_date desc, _ingested_at desc) = 1` "
        "und prüft auf Änderungen in den überwachten Attributen:",
        s['body']
    ))
    code_snapshot = (
        "-- dbt/snapshots/dim_video_snapshot.sql (Original-Code)\n"
        "{% snapshot dim_video_snapshot %}\n"
        "{{\n"
        "    config(\n"
        "      target_schema='youtube_analytics',\n"
        "      strategy='check',\n"
        "      unique_key='video_id',\n"
        "      check_cols=['title', 'channel_title', 'category_id', 'tags'],\n"
        "      invalidate_hard_deletes=True\n"
        "    )\n"
        "}}\n"
        "select video_id, title, channel_title, category_id, tags\n"
        "from {{ ref('stg_videos') }}\n"
        "qualify row_number() over (partition by video_id order by trending_date desc, _ingested_at desc) = 1\n"
        "{% endsnapshot %}"
    )
    story.append(make_code_block(code_snapshot, s))

    story.append(P("6.3 Point-in-Time Join in der Faktentabelle (`fact_video_metrics.sql`)", s['h2']))
    story.append(P(
        "Beim Aufbau der Faktentabelle wird jedes Trending-Event exakt mit derjenigen Version von `dim_video` "
        "verknüpft, die zum jeweiligen `trending_date` gültig war (`valid_from` bis `valid_to`). Zudem verhindert "
        "`safe_divide` Division-by-Zero-Fehler bei der Berechnung der `interaction_ratio`:",
        s['body']
    ))
    code_pit_join = (
        "-- dbt/models/marts/core/fact_video_metrics.sql (Original-Code)\n"
        "{{ config(materialized='table') }}\n\n"
        "with source_data as ( select * from {{ ref('stg_videos') }} ),\n"
        "dim_v as ( select * from {{ ref('dim_video') }} )\n\n"
        "select\n"
        "    to_hex(md5(concat(s.video_id, '_', cast(s.trending_date as string)))) as metric_key,\n"
        "    dim_v.video_key,\n"
        "    cast(s.category_id as int64) as category_key,\n"
        "    cast(format_date('%Y%m%d', s.trending_date) as int64) as date_key,\n"
        "    s.views, s.likes, s.dislikes, s.comment_count,\n"
        "    safe_divide(s.likes + s.dislikes + s.comment_count, s.views) as interaction_ratio,\n"
        "    s._ingested_at\n"
        "from source_data s\n"
        "inner join dim_v\n"
        "    on s.video_id = dim_v.video_id\n"
        "    and s.trending_date >= cast(dim_v.valid_from as date)\n"
        "    and (dim_v.valid_to is null or s.trending_date < cast(dim_v.valid_to as date))"
    )
    story.append(make_code_block(code_pit_join, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 7: DATAOPS QUALITY GATES & AUTOMATISIERTE TESTS
    # =========================================================================
    story.extend(track(7))
    story.append(P("7. DataOps Quality Gates: 15 dbt Tests & In-Workflow Validierung", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Gemäß dem DataOps-Prinzip **'Shift Left'** verlagert die Plattform Qualitätsprüfungen direkt in den "
        "Transformations- und Orchestrierungszyklus. Da Cloud Data Warehouses wie BigQuery standardmäßig keine "
        "Primary-Key- oder Foreign-Key-Constraints beim Schreiben erzwingen, implementiert das Projekt ein "
        "zweistufiges Schutzschild aus **15 deklarativen dbt Data Tests** (`dbt/models/marts/core/schema.yml`) "
        "und einem **serverlosen In-Workflow Quality Gate** (`infra/workflows/pipeline.yaml`).",
        s['body']
    ))

    story.append(P("7.1 Exakte Aufschlüsselung aller 15 dbt Data Tests (`schema.yml`)", s['h2']))

    test_table_data = [
        [P("<b>Mart-Tabelle</b>", s['th']), P("<b>Spalte</b>", s['th']), P("<b>Definierte dbt-Tests</b>", s['th']), P("<b>Anzahl</b>", s['th']), P("<b>Abgesicherte Invariante</b>", s['th'])],
        [
            P("<b>dim_video</b>", s['td_bold']),
            P("`video_key`<br/>`video_id`", s['td']),
            P("`unique`, `not_null`<br/>`not_null`", s['td']),
            P("<b>3 Tests</b>", s['td_bold']),
            P("Jede SCD-2-Versionszeile hat einen eindeutigen Surrogate-Hash (`dbt_scd_id`) und einen Natural Key.", s['td'])
        ],
        [
            P("<b>dim_category</b>", s['td_bold']),
            P("`category_key`", s['td']),
            P("`unique`, `not_null`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("Keine doppelten oder leeren Kategorienschlüssel in der Conformed Dimension.", s['td'])
        ],
        [
            P("<b>dim_date</b>", s['td_bold']),
            P("`date_key`", s['td']),
            P("`unique`, `not_null`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("Jeder Kalendertag im Format `YYYYMMDD` existiert exakt einmal.", s['td'])
        ],
        [
            P("<b>fact_video_metrics</b>", s['td_bold']),
            P("`metric_key`", s['td']),
            P("`unique`, `not_null`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("Verhindert doppelte Faktenzeilen für dasselbe Video am selben Trending-Tag.", s['td'])
        ],
        [
            P("<b>fact_video_metrics</b>", s['td_bold']),
            P("`video_key`", s['td']),
            P("`not_null` +<br/>`relationships` -> `dim_video`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("<b>Referenzielle Integrität (SCD-2):</b> Jeder Fakt zeigt auf eine existierende `dim_video`-Version.", s['td'])
        ],
        [
            P("<b>fact_video_metrics</b>", s['td_bold']),
            P("`category_key`", s['td']),
            P("`not_null` +<br/>`relationships` -> `dim_category`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("<b>Referenzielle Integrität:</b> Jede Faktenzeile besitzt eine valide Kategorie.", s['td'])
        ],
        [
            P("<b>fact_video_metrics</b>", s['td_bold']),
            P("`date_key`", s['td']),
            P("`not_null` +<br/>`relationships` -> `dim_date`", s['td']),
            P("<b>2 Tests</b>", s['td_bold']),
            P("<b>Referenzielle Integrität:</b> Jede Faktenzeile besitzt einen gültigen Kalendertag.", s['td'])
        ],
        [
            P("<b>SUMME</b>", s['td_bold']),
            P("<b>Alle 4 Core Marts</b>", s['td_bold']),
            P("<b>4x unique, 8x not_null, 3x FK</b>", s['td_bold']),
            P("<b>15 Tests</b>", s['td_bold']),
            P("<b>Ergebnis im Produktivlauf: `PASS=15 WARN=0 ERROR=0 SKIP=0`</b>", s['td_bold'])
        ]
    ]
    t_test = Table(test_table_data, colWidths=[90, 75, 110, 50, 170])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E0F2FE")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_test)
    story.append(Spacer(1, 8))

    story.append(P("7.2 Das serverlose In-Workflow Quality Gate (`pipeline.yaml`)", s['h2']))
    story.append(P(
        "Zusätzlich zu `run_dbt.ps1 test` führt der Google Cloud Workflow bei jedem Lauf in der Cloud "
        "automatisch eine Foreign-Key-Orphan-Prüfung in BigQuery aus. Werden verwaiste Schlüssel (`invalid_count > 0`) "
        "entdeckt, wirft der Workflow im Schritt `evaluate_quality_gate` sofort eine Exception (`raise`) und "
        "verhindert eine Freigabe fehlerhafter Daten.",
        s['body']
    ))
    story.append(make_callout(
        "<b>Verifiziertes Testergebnis (`run_dbt.ps1 test` & `run_workflow.ps1`):</b><br/>"
        "• dbt Core: `Done. PASS=15 WARN=0 ERROR=0 SKIP=0 TOTAL=15`<br/>"
        "• Cloud Workflow: `{\"message\":\"DataOps Pipeline completed successfully. 0 quality errors detected.\",\"status\":\"SUCCESS\"}`",
        s, "Formeller Qualitätsnachweis"
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 8: INFRASTRUCTURE AS CODE (TERRAFORM 1.17)
    # =========================================================================
    story.extend(track(8))
    story.append(P("8. Infrastructure as Code (Terraform 1.17 Cloud Provisioning — 7 GCP Ressourcen)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Manuelles Zusammenklicken von Cloud-Ressourcen ('ClickOps') führt unweigerlich zu Konfigurations-Drift "
        "und nicht reproduzierbaren Umgebungen. In Release `v2.1.0` wird die gesamte Google Cloud Infrastruktur "
        "über **Terraform 1.17** (`infra/main.tf`, `infra/variables.tf`, `infra/versions.tf`) deklarativ verwaltet "
        "und über den PowerShell-Wrapper `run_infra.ps1` gesteuert.",
        s['body']
    ))

    story.append(P("8.1 Die 7 bereitgestellten Google Cloud Ressourcen im Detail", s['h2']))

    tf_res_data = [
        [P("<b>Terraform Ressource</b>", s['th']), P("<b>Live GCP Name / ID</b>", s['th']), P("<b>Konfiguration & FinOps-Schutz</b>", s['th'])],
        [
            P("`google_storage_bucket`<br/>`.lakehouse_storage`", s['td_bold']),
            P("`lakehouse-youtube-`<br/>`cloudanalytics-514018`", s['td']),
            P("Location `EU`, `uniform_bucket_level_access = true`, `versioning { enabled = true }`, `force_destroy = true`.", s['td'])
        ],
        [
            P("`google_bigquery_dataset`<br/>`.youtube_analytics`", s['td_bold']),
            P("`youtube_analytics`", s['td']),
            P("Location `EU`, `delete_contents_on_destroy = true` (garantiert rückstandsloses Löschen bei `destroy`).", s['td'])
        ],
        [
            P("`google_pubsub_topic`<br/>`.youtube_ingest`", s['td_bold']),
            P("`topic-youtube-ingest`", s['td']),
            P("Serverloses Cloud-Pub/Sub-Topic für den regulären Event-Ingest-Strom (444 Clean Events).", s['td'])
        ],
        [
            P("`google_pubsub_subscription`<br/>`.youtube_ingest_sub`", s['td_bold']),
            P("`sub-youtube-ingest`", s['td']),
            P("Pull-Subscription für `run_pubsub_bronze.ps1` (`ack_deadline_seconds = 60`, Retention 7 Tage).", s['td'])
        ],
        [
            P("`google_pubsub_topic`<br/>`.youtube_dlq`", s['td_bold']),
            P("`topic-youtube-dlq`", s['td']),
            P("Serverloses Cloud-Pub/Sub-Topic für isolierte Dead-Letter-Queue-Nachrichten (56 DLQ Events).", s['td'])
        ],
        [
            P("`google_pubsub_subscription`<br/>`.youtube_dlq_sub`", s['td_bold']),
            P("`sub-youtube-dlq`", s['td']),
            P("Pull-Subscription für `run_pubsub_dlq.ps1` (`ack_deadline_seconds = 60`, Retention 7 Tage).", s['td'])
        ],
        [
            P("`google_workflows_workflow`<br/>`.youtube_dataops_pipeline`", s['td_bold']),
            P("`youtube-dataops-pipeline`", s['td']),
            P("Region `europe-west3` (Frankfurt), nutzt `var.service_account_email` und injiziert `workflows/pipeline.yaml`.", s['td'])
        ]
    ]
    t_tf = Table(tf_res_data, colWidths=[130, 145, 220])
    t_tf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_tf)
    story.append(Spacer(1, 6))

    story.append(P("8.2 Vollständiger Code von `infra/main.tf` (7 GCP Ressourcen)", s['h2']))
    code_tf = (
        "# infra/main.tf (Vollstaendiger Original-Code: 7 GCP Ressourcen)\n"
        "provider \"google\" {\n"
        "  project     = var.project_id\n"
        "  region      = var.region\n"
        "  credentials = file(var.credentials_file)\n"
        "}\n\n"
        "resource \"google_storage_bucket\" \"lakehouse_storage\" {\n"
        "  name                        = \"lakehouse-youtube-${var.project_id}\"\n"
        "  location                    = var.location\n"
        "  force_destroy               = true\n"
        "  uniform_bucket_level_access = true\n"
        "  versioning { enabled = true }\n"
        "}\n\n"
        "resource \"google_bigquery_dataset\" \"youtube_analytics\" {\n"
        "  dataset_id                 = \"youtube_analytics\"\n"
        "  friendly_name              = \"YouTube Video Analytics DWH\"\n"
        "  location                   = var.location\n"
        "  delete_contents_on_destroy = true\n"
        "}\n\n"
        "resource \"google_pubsub_topic\" \"youtube_ingest\" {\n"
        "  name = \"topic-youtube-ingest\"\n"
        "}\n\n"
        "resource \"google_pubsub_subscription\" \"youtube_ingest_sub\" {\n"
        "  name                       = \"sub-youtube-ingest\"\n"
        "  topic                      = google_pubsub_topic.youtube_ingest.name\n"
        "  ack_deadline_seconds       = 60\n"
        "  message_retention_duration = \"604800s\"\n"
        "}\n\n"
        "resource \"google_pubsub_topic\" \"youtube_dlq\" {\n"
        "  name = \"topic-youtube-dlq\"\n"
        "}\n\n"
        "resource \"google_pubsub_subscription\" \"youtube_dlq_sub\" {\n"
        "  name                       = \"sub-youtube-dlq\"\n"
        "  topic                      = google_pubsub_topic.youtube_dlq.name\n"
        "  ack_deadline_seconds       = 60\n"
        "  message_retention_duration = \"604800s\"\n"
        "}\n\n"
        "resource \"google_workflows_workflow\" \"youtube_dataops_pipeline\" {\n"
        "  name            = \"youtube-dataops-pipeline\"\n"
        "  region          = var.region\n"
        "  description     = \"Serverlose Orchestrierung fuer YouTube DWH Star-Schema & Quality Gates\"\n"
        "  service_account = var.service_account_email\n"
        "  source_contents = file(\"${path.module}/workflows/pipeline.yaml\")\n"
        "}"
    )
    story.append(make_code_block(code_tf, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 9: SERVERLOSE ORCHESTRIERUNG (GOOGLE CLOUD WORKFLOWS)
    # =========================================================================
    story.extend(track(9))
    story.append(P("9. Serverlose Orchestrierung (Google Cloud Workflows State-Machine)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "In Release `v2.1.0` löst **Google Cloud Workflows** den lokalen Airflow-Container-Stack aus `v1.0.0` "
        "vollständig ab. Während ein gemanagter Airflow-Cluster (Cloud Composer) durch dauerhaft laufende "
        "GKE-Knoten rund 300 € bis 450 € pro Monat kostet, arbeitet Cloud Workflows zu 100% serverlos mit "
        "**0,00 € Idle-Kosten** (5.000 Schritte/Monat im Always Free Tier inklusive).",
        s['body']
    ))

    story.append(P("9.1 Architektur & Parser-Härtung von `infra/workflows/pipeline.yaml`", s['h2']))
    story.append(P(
        "Die State-Machine nutzt den offiziellen Google Cloud BigQuery Connector (`googleapis.bigquery.v2.jobs.query`) "
        "und berücksichtigt zwei wichtige Produktions-Restriktionen der Cloud Workflows Engine:",
        s['body']
    ))
    story.append(P("• <b>400-Zeichen-Limit für Ausdrücke (`${...}`):</b> Da Cloud Workflows dynamische Ausdrücke auf maximal 400 Zeichen begrenzt, ist das SQL-Statement in `prepare_fact_query` sauber in vier Teilvariablen (`q_target`, `q_select`, `q_from`, `q_join`) modularisiert und wird über `${q_target + q_select + q_from + q_join}` konkateniert.", s['bullet']))
    story.append(P("• <b>Strikte Trennung von `assign` und `switch`:</b> In Cloud Workflows darf ein Schritt nicht gleichzeitig `assign` und `switch` enthalten. Deshalb liest `get_quality_result` zunächst `invalid_count` aus, bevor `evaluate_quality_gate` die Bedingung `${invalid_count > 0}` prüft.", s['bullet']))

    story.append(P("9.2 Vollständiger Code von `infra/workflows/pipeline.yaml`", s['h2']))
    code_workflow = (
        "# infra/workflows/pipeline.yaml (Vollstaendiger Original-Code)\n"
        "main:\n"
        "  params: [args]\n"
        "  steps:\n"
        "    - init_constants:\n"
        "        assign:\n"
        "          - project_id: \"cloudanalytics-514018\"\n"
        "          - dataset_id: \"youtube_analytics\"\n"
        "    - check_silver_data:\n"
        "        call: googleapis.bigquery.v2.jobs.query\n"
        "        args:\n"
        "          projectId: ${project_id}\n"
        "          body:\n"
        "            query: ${\"SELECT count(*) as total_records FROM `\" + project_id + \".\" + dataset_id + \".silver_videos`\"}\n"
        "            useLegacySql: false\n"
        "        result: silver_check_result\n"
        "    - prepare_fact_query:\n"
        "        assign:\n"
        "          - q_target: ${\"CREATE OR REPLACE TABLE `\" + project_id + \".\" + dataset_id + \".fact_video_metrics` AS \"}\n"
        "          - q_select: \"SELECT TO_HEX(MD5(CONCAT(s.video_id, '_', CAST(s.trending_date AS STRING)))) AS metric_key, dim_v.video_key, CAST(s.category_id AS INT64) AS category_key, CAST(FORMAT_DATE('%Y%m%d', s.trending_date) AS INT64) AS date_key, s.views, s.likes, s.dislikes, s.comment_count, SAFE_DIVIDE(s.likes + s.dislikes + s.comment_count, s.views) AS interaction_ratio, s._ingested_at \"\n"
        "          - q_from: ${\"FROM `\" + project_id + \".\" + dataset_id + \".stg_videos` s INNER JOIN `\" + project_id + \".\" + dataset_id + \".dim_video` dim_v \"}\n"
        "          - q_join: \"ON s.video_id = dim_v.video_id AND s.trending_date >= CAST(dim_v.valid_from AS DATE) AND (dim_v.valid_to IS NULL OR s.trending_date < CAST(dim_v.valid_to AS DATE))\"\n"
        "          - fact_query: ${q_target + q_select + q_from + q_join}\n"
        "    - refresh_fact_table:\n"
        "        call: googleapis.bigquery.v2.jobs.query\n"
        "        args:\n"
        "          projectId: ${project_id}\n"
        "          body:\n"
        "            query: ${fact_query}\n"
        "            useLegacySql: false\n"
        "        result: fact_refresh_result\n"
        "    - quality_gate_validation:\n"
        "        call: googleapis.bigquery.v2.jobs.query\n"
        "        args:\n"
        "          projectId: ${project_id}\n"
        "          body:\n"
        "            query: ${\"SELECT count(*) as invalid_keys FROM `\" + project_id + \".\" + dataset_id + \".fact_video_metrics` f LEFT JOIN `\" + project_id + \".\" + dataset_id + \".dim_video` v ON f.video_key = v.video_key WHERE v.video_key IS NULL\"}\n"
        "            useLegacySql: false\n"
        "        result: quality_result\n"
        "    - get_quality_result:\n"
        "        assign:\n"
        "          - invalid_count: ${int(quality_result.rows[0].f[0].v)}\n"
        "    - evaluate_quality_gate:\n"
        "        switch:\n"
        "          - condition: ${invalid_count > 0}\n"
        "            raise: ${\"Quality Gate FAILED! Found \" + string(invalid_count) + \" orphan records in fact_video_metrics.\"}\n"
        "    - finish_success:\n"
        "        return:\n"
        "          status: \"SUCCESS\"\n"
        "          message: \"DataOps Pipeline completed successfully. 0 quality errors detected.\""
    )
    story.append(make_code_block(code_workflow, s))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 10: CLOUD-NATIVE OBSERVABILITY (GRAFANA CLOUD & GCP MONITORING)
    # =========================================================================
    story.extend(track(10))
    story.append(P("10. Cloud-Native Observability (Grafana Cloud & GCP Monitoring - Weg 1)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "In Release `v2.1.0` wurde das Monitoring auf **'Weg 1: Cloud-Native Observability'** umgestellt. "
        "Anstatt lokale Prometheus- und Grafana-Container auf dem Entwickler-PC laufen zu lassen, verbindet sich "
        "**Grafana Cloud** über das offizielle **Google Cloud Monitoring** Plugin (`pluginId: stackdriver`) direkt "
        "mit den Telemetrie-APIs der Google Cloud Platform — mit **0 lokalen Daemons und 0 CPU/RAM-Belastung**.",
        s['body']
    ))

    story.append(P("10.1 Die 8 Panels des Grafana Dashboards (`youtube_dataops_monitoring.json`)", s['h2']))

    obs_table_data = [
        [P("<b>Row / Panel-Titel</b>", s['th']), P("<b>Visualisierung</b>", s['th']), P("<b>GCP Metric Type (`stackdriver`)</b>", s['th']), P("<b>Operativer & FinOps Nutzen</b>", s['th'])],
        [
            P("<b>1. Workflow Executions</b><br/><i>(Row: High-Level KPIs)</i>", s['td_bold']),
            P("Stat Panel (Grün)", s['td']),
            P("`workflows.googleapis.com/`<br/>`finished_execution_count`", s['td']),
            P("Gesamtzahl abgeschlossener Cloud-Workflow-Läufe (`REDUCE_SUM`, `ALIGN_DELTA`).", s['td'])
        ],
        [
            P("<b>2. BigQuery Queries</b><br/><i>(Row: High-Level KPIs)</i>", s['td_bold']),
            P("Stat Panel (Blau)", s['td']),
            P("`bigquery.googleapis.com/`<br/>`query/count`", s['td']),
            P("Überwacht die DWH-Abfragefrequenz durch dbt und Cloud Workflows.", s['td'])
        ],
        [
            P("<b>3. Pub/Sub Activity</b><br/><i>(Row: High-Level KPIs)</i>", s['td_bold']),
            P("Stat Panel (Violett)", s['td']),
            P("`pubsub.googleapis.com/topic/`<br/>`send_message_operation_count`", s['td']),
            P("Gesamtes Streaming-Nachrichtenvolumen über alle Cloud-Topics.", s['td'])
        ],
        [
            P("<b>4. BigQuery Bytes Billed</b><br/><i>(Row: High-Level KPIs)</i>", s['td_bold']),
            P("Stat Panel (Ampel)", s['td']),
            P("`bigquery.googleapis.com/`<br/>`query/scanned_bytes_billed`", s['td']),
            P("<b>FinOps-Wächter:</b> Grün < 100 MB, Orange ab 100 MB, Rot ab 1 GB gescannten Daten.", s['td'])
        ],
        [
            P("<b>5. Workflow Executions by Status</b><br/><i>(Row: Orchestration)</i>", s['td_bold']),
            P("Stacked Bar Chart", s['td']),
            P("`workflows.googleapis.com/`<br/>`finished_execution_count`", s['td']),
            P("Gruppiert nach `metric.label.status` (`SUCCEEDED` vs. `FAILED`) über die Zeit.", s['td'])
        ],
        [
            P("<b>6. Workflow Execution Duration (p99)</b><br/><i>(Row: Orchestration)</i>", s['td_bold']),
            P("Time Series Line (s)", s['td']),
            P("`workflows.googleapis.com/`<br/>`execution_durations`", s['td']),
            P("Misst die 99.-Perzentil-Latenz (`ALIGN_PERCENTILE_99`) der Pipeline-Durchläufe.", s['td'])
        ],
        [
            P("<b>7. Pub/Sub Topics (Ingest vs DLQ)</b><br/><i>(Row: DWH & DLQ Health)</i>", s['td_bold']),
            P("Stacked Bar Chart", s['td']),
            P("`pubsub.googleapis.com/topic/`<br/>`send_message_operation_count`", s['td']),
            P("Gruppiert nach `resource.label.topic_id` (`topic-youtube-ingest` vs. `topic-youtube-dlq`).", s['td'])
        ],
        [
            P("<b>8. BigQuery Data Scanned Volume</b><br/><i>(Row: DWH & DLQ Health)</i>", s['td_bold']),
            P("Time Series Area", s['td']),
            P("`bigquery.googleapis.com/`<br/>`query/scanned_bytes_billed`", s['td']),
            P("Historischer Verlauf des Abfrage-Scanvolumens zur Erkennung teurer Full-Table-Scans.", s['td'])
        ]
    ]
    t_obs = Table(obs_table_data, colWidths=[125, 80, 140, 150])
    t_obs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_obs)
    story.append(Spacer(1, 8))

    story.append(make_callout(
        "<b>Technischer Hinweis zum Grafana-Import (`pluginId: stackdriver`):</b> Intern identifiziert Grafana 10+ "
        "die Datenquelle 'Google Cloud Monitoring' unter der historischen Plugin-ID `stackdriver`. "
        "In `dashboards/youtube_dataops_monitoring.json` ist diese ID exakt hinterlegt, sodass beim JSON-Import "
        "sofort das Dropdown zur Auswahl der verbundenen GCP-Datenquelle erscheint.",
        s, "Grafana Schema-Kompatibilität"
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 11: DATAOPS CI/CD & RELEASE-MANAGEMENT
    # =========================================================================
    story.extend(track(11))
    story.append(P("11. DataOps CI/CD Pipelines, GitOps & Release-Management", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Im Data Engineering trifft deklarativer Code auf persistenten Daten-State. Dieses Kapitel zeigt sowohl "
        "die im Repository aktiven **GitHub Actions Workflows** (`.github/workflows/ci.yml` und `release.yml`) "
        "als auch das **Enterprise-Zielbild für Multi-Environment Promotion (Dev -> Staging -> Prod)**.",
        s['body']
    ))

    story.append(P("11.1 Die aktiven GitHub Actions Workflows im Repository", s['h2']))
    code_ci = (
        "# .github/workflows/ci.yml (Original-Code)\n"
        "name: DataOps CI & Validation\n"
        "on:\n"
        "  push:\n"
        "    branches: [ main ]\n"
        "  pull_request:\n"
        "    branches: [ main ]\n\n"
        "jobs:\n"
        "  validate-pipeline:\n"
        "    name: Code Quality & Schema Verification\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Checkout Code\n"
        "        uses: actions/checkout@v4\n"
        "      - name: Set up Python 3.10\n"
        "        uses: actions/setup-python@v5\n"
        "        with:\n"
        "          python-version: \"3.10\"\n"
        "          cache: \"pip\"\n"
        "      - name: Install Python Dependencies\n"
        "        run: |\n"
        "          python -m pip install --upgrade pip\n"
        "          pip install flake8 pyyaml\n"
        "      - name: Python Syntax & Lint Check\n"
        "        run: |\n"
        "          python -m compileall src/\n"
        "          flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics\n"
        "      - name: Validate Cloud Workflows YAML\n"
        "        run: |\n"
        "          python -c \"import yaml; yaml.safe_load(open('infra/workflows/pipeline.yaml'))\"\n"
        "      - name: Validate Grafana Dashboard JSON\n"
        "        run: |\n"
        "          python -c \"import json; json.load(open('dashboards/youtube_dataops_monitoring.json'))\""
    )
    story.append(make_code_block(code_ci, s))

    story.append(P(
        "Ergänzend triggert `.github/workflows/release.yml` bei jedem Push eines Versions-Tags (`v*`, wie `v1.0.0`, "
        "`v2.0.0`, `v2.1.0`) die Action `softprops/action-gh-release@v2` und publiziert automatisch ein GitHub Release "
        "inklusive generierter Release Notes.",
        s['body']
    ))

    story.append(P("11.2 Enterprise-Praxis: Drei-Zonen-Modell, Slim CI & Keyless OIDC", s['h2']))
    story.append(P("• <b>Umgebungs-Isolation (Dev / Staging / Prod):</b> Entwickler arbeiten lokal gegen ein isoliertes Dataset (`youtube_analytics_dev`). Pull Requests bauen in einer ephemeren Staging-Umgebung (`youtube_analytics_ci_<PR_ID>`). Auf `youtube_analytics_prod` hat kein Mensch Schreibrechte — ausschließlich der CI/CD-Service-Account.", s['bullet']))
    story.append(P("• <b>dbt Slim CI (`state:modified+`):</b> In großen DWHs baut die CI-Pipeline bei einem Pull Request nicht alle 500 Modelle neu, sondern führt via `dbt build --select state:modified+ --defer --state ./prod-manifest` nur geänderte Modelle und deren direkte Kinder aus.", s['bullet']))
    story.append(P("• <b>Keyless Authentication via Workload Identity Federation (OIDC):</b> Statt statischer JSON-Keys in GitHub Secrets tauscht GitHub Actions zur Laufzeit ein kurzlebiges OIDC-JWT-Token gegen ein 1 Stunde gültiges GCP OAuth2-Token (`google-github-actions/auth@v2`).", s['bullet']))
    story.append(P("• <b>Remote Terraform State Locking:</b> Der Terraform-State (`terraform.tfstate`) liegt im Enterprise-Betrieb in einem versionierten GCS-Bucket mit automatischem State-Locking, damit niemals zwei Pipelines gleichzeitig `terraform apply` ausführen.", s['bullet']))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 12: ARCHITECTURAL DECISION RECORDS (ADRS) & ENTERPRISE RISIKOANALYSE
    # =========================================================================
    story.extend(track(12))
    story.append(P("12. Architectural Decision Records (ADRs 001–007) & Kritische Enterprise-Risikoanalyse", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P("12.1 Die 7 zentralen Architekturentscheidungen (ADRs 001 bis 007)", s['h2']))

    adrs = [
        (
            "ADR-001: Apache Kafka KRaft vs. ZooKeeper (v1.0/v2.0)",
            "<b>Entscheidung:</b> Einsatz von Apache Kafka im ZooKeeper-losen KRaft-Modus (`docker-compose-kafka.yml`).<br/>"
            "<b>Kontext & Begründung:</b> Das 2021er Setup litt unter ZooKeeper-Timeouts und Split-Brain-Problemen. KRaft halbiert die Container-Anzahl und verwaltet den Cluster-State in einem internen Raft-Quorum-Log."
        ),
        (
            "ADR-002: Apache Iceberg V2 Table Format vs. Pure Parquet (ab v2.0)",
            "<b>Entscheidung:</b> Nutzung von Apache Iceberg V2 (`local.silver.videos`) für den Silver Lakehouse Layer.<br/>"
            "<b>Kontext & Begründung:</b> Reine Parquet-Ordner bieten keine ACID-Garantien und keine Snapshot-Isolation. Iceberg V2 trennt physische Parquet-Daten strikt von logischen Metadaten (`v1.metadata.json`, `snap-*.avro`), erlaubt atomare Commits, Time-Travel und Engine-Neutralität."
        ),
        (
            "ADR-003: Ephemerer Docker PySpark vs. Permanenter Spark-Cluster",
            "<b>Entscheidung:</b> Ausführung von PySpark-Jobs in einem ephemeren On-Demand-Container (`de_spark`).<br/>"
            "<b>Kontext & Begründung:</b> Ein dauerhaft laufender Spark-Cluster verbraucht rund um die Uhr RAM/CPU. Ephemerer Compute erzeugt 0 € Leerlaufkosten und nutzt über `broadcast()` einen Zero-Shuffle Join."
        ),
        (
            "ADR-004: Kimball Star-Schema & SCD-2 via dbt Core vs. One Big Table (ab v2.0)",
            "<b>Entscheidung:</b> Modellierung als relationales Kimball Star-Schema mit SCD-2 Snapshot (`dim_video_snapshot`) in BigQuery.<br/>"
            "<b>Kontext & Begründung:</b> Flache Tabellen (OBT) überschreiben bei Titeländerungen die Historie (SCD-1). Das Star-Schema trennt Fakten (`fact_video_metrics`) von Dimensionen (`dim_video`, `dim_category`, `dim_date`), ermöglicht Point-in-Time Joins und wird durch 15 dbt-Tests abgesichert."
        ),
        (
            "ADR-005: Google Cloud Workflows vs. Apache Airflow / Cloud Composer (v2.1)",
            "<b>Entscheidung:</b> Ablösung von Apache Airflow (v1.0) durch serverlose Google Cloud Workflows (v2.1).<br/>"
            "<b>Kontext & Begründung:</b> Cloud Composer kostet mindestens ~300 €/Monat im Leerlauf. Cloud Workflows startet in unter 200 ms via REST, orchestriert BigQuery nativ, prüft das Foreign-Key Quality Gate in der Cloud und kostet im Always Free Tier 0,00 €."
        ),
        (
            "ADR-006: Grafana Cloud Direct Monitoring (Weg 1) vs. Lokale Prometheus-Container (v2.1)",
            "<b>Entscheidung:</b> Direkte Anbindung von Grafana Cloud an Google Cloud Monitoring (`pluginId: stackdriver`).<br/>"
            "<b>Kontext & Begründung:</b> 0 lokale Daemons, direkte Abfrage von `workflows`, `bigquery` und `pubsub` Metriken über den Service Account (`roles/monitoring.viewer`) und versioniertes Dashboard-as-Code."
        ),
        (
            "ADR-007: Serverless Google Cloud Pub/Sub (v2.1) vs. Lokaler Docker-Kafka-Broker (v1.0/v2.0)",
            "<b>Entscheidung:</b> Ablösung des lokalen Kafka-Containers durch Google Cloud Pub/Sub (`topic-youtube-ingest`/`sub-youtube-ingest` & `topic-youtube-dlq`/`sub-youtube-dlq`) in Release `v2.1.0`.<br/>"
            "<b>Kontext & Begründung:</b> Ein lokaler Kafka-Broker belegt dauerhaft RAM und ist für Cloud-Dienste nicht nativ sichtbar. Cloud Pub/Sub skaliert serverlos, benötigt 0 lokale Container, kostet bis 10 GB/Monat 0,00 € und liefert Echtzeit-Telemetrie an Grafana Cloud."
        )
    ]

    for title, content in adrs:
        story.append(P(f"<b>{title}</b>", s['h3']))
        story.append(P(content, s['body']))
        story.append(Spacer(1, 2))

    story.append(PageBreak())

    story.append(P("12.2 Kritische Analyse: 8 Reale Risiken & Architektonische Schwachstellen im Enterprise-Umfeld", s['h2']))
    story.append(P(
        "Eine belastbare Senior/Lead-Architekturdokumentation verschweigt nicht die Grenzen des eigenen Designs. "
        "Während diese Plattform für ein 0-€-Kostenprofil (Always Free Tier) und deterministische Reproduzierbarkeit "
        "optimiert wurde, birgt sie beim Skalieren auf **Terabyte- bis Petabyte-Volumina im Enterprise-Betrieb** "
        "acht konkrete strukturelle Risiken und Schwachstellen, die wie folgt mitigiert werden müssen:",
        s['body']
    ))

    risks = [
        (
            "1. Hybride Storage-Brücke (Lokales Dateisystem statt Native Cloud Object Storage)",
            "<b>Ist-Zustand (Schwachstelle):</b> In `v2.1.0` ziehen die Pub/Sub-Consumer Daten auf die lokale Festplatte (`data/bronze/`), der Docker-PySpark-Container schreibt das Iceberg-Warehouse lokal (`data/iceberg_warehouse/`), und `load_to_bigquery.py` lädt Parquet von lokal nach BigQuery. Fällt die lokale Workstation aus, steht die Datenbrücke.<br/>"
            "<b>Enterprise-Mitigation:</b> Vollständige Verlagerung in den bereits per Terraform provisionierten GCS-Bucket `gs://lakehouse-youtube-cloudanalytics-514018/`. Pub/Sub nutzt eine **Cloud Storage Subscription** (oder Cloud Run Jobs), PySpark läuft als **Serverless Dataproc Batch** direkt auf GCS, und BigQuery liest die Iceberg-Metadaten ohne Kopiervorgang über **BigQuery BigLake**."
        ),
        (
            "2. Lokaler Terraform-State & Statischer Service-Account-JSON-Schlüssel",
            "<b>Ist-Zustand (Schwachstelle):</b> Die Datei `infra/terraform.tfstate` liegt lokal und unverschlüsselt auf dem Host; die Authentifizierung nutzt `gcp_service_account.json` (langlebiger privater Schlüssel mit Exfiltrationsrisiko).<br/>"
            "<b>Enterprise-Mitigation:</b> Auslagerung des Terraform-States in einen versionierten **GCS Remote Backend Bucket** mit nativem State-Locking sowie Umstellung von statischen JSON-Keys auf **Workload Identity Federation (OIDC)** (kurzlebige 1h-OAuth2-Tokens)."
        ),
        (
            "3. Intra-Batch-Mutationsverlust bei `dbt snapshot` (Micro-Batch vs. Continuous CDC)",
            "<b>Ist-Zustand (Schwachstelle):</b> `dim_video_snapshot.sql` dedupliziert die Staging-View via `QUALIFY row_number() OVER (PARTITION BY video_id ORDER BY trending_date DESC, _ingested_at DESC) = 1`. Ändert ein Video seinen Titel dreimal innerhalb desselben Micro-Batches, sieht ein einzelner `dbt snapshot`-Lauf nur den letzten Zustand des Batches.<br/>"
            "<b>Enterprise-Mitigation:</b> Entweder hochfrequente Ausführung von `dbt snapshot` (z. B. alle 5–15 Minuten) oder Berechnung der Versionsgrenzen (`LEAD(trending_date) OVER (PARTITION BY video_id ORDER BY trending_date)`) direkt per Window-Function über den gesamten Event-Stream."
        ),
        (
            "4. Full-Refresh (`CREATE OR REPLACE TABLE`) statt Inkrementeller Partitionierung",
            "<b>Ist-Zustand (Schwachstelle):</b> Sowohl `load_to_bigquery.py` (`WRITE_TRUNCATE`) als auch die dbt-Marts und der Cloud Workflow bauen `fact_video_metrics` bei jedem Lauf komplett neu auf. Bei 500 Zeilen dauert dies 2 Sekunden — bei **50 Terabyte** führt ein Full-Table-Scan zu enormen BigQuery-Kosten (~300 $ pro Lauf).<br/>"
            "<b>Enterprise-Mitigation:</b> Umstellung von `fact_video_metrics` in dbt auf `materialized='incremental'`, `incremental_strategy='merge'`, `partition_by={'field': 'trending_date', 'data_type': 'date'}` und `cluster_by=['category_key', 'video_key']`."
        ),
        (
            "5. Überprivilegierter Service Account (`*.admin` statt Least-Privilege Principle)",
            "<b>Ist-Zustand (Schwachstelle):</b> Ein einziger Service Account vereint `bigquery.admin`, `storage.admin`, `pubsub.admin` und `workflows.admin` sowohl für das Terraform-Deployment als auch für die Laufzeit des Cloud Workflows.<br/>"
            "<b>Enterprise-Mitigation:</b> Strikte Trennung (Segregation of Duties) in mindestens drei Service Accounts: 1. `sa-terraform-deployer` (nur in CI/CD), 2. `sa-pubsub-ingest` (nur `pubsub.publisher`/`subscriber`), 3. `sa-workflow-runtime` (nur `bigquery.dataEditor` und `bigquery.jobUser`)."
        ),
        (
            "6. Fehlende Schema-Durchsetzung am Ingest-Rand (Schemaless JSON vs. Schema Registry)",
            "<b>Ist-Zustand (Schwachstelle):</b> Die Producer prüfen fehlerhafte `views` im Python-Code der Quelle und senden freies JSON. Wenn ein Drittsystem direkt fehlerhaftes JSON in `topic-youtube-ingest` publiziert, wird dies erst beim nachgelagerten Pull/Cast bemerkt.<br/>"
            "<b>Enterprise-Mitigation:</b> Kopplung von `topic-youtube-ingest` an eine **Google Cloud Pub/Sub Schema Registry** (Avro oder Protocol Buffers) sowie Einsatz einer nativen Pub/Sub `dead_letter_policy` mit `max_delivery_attempts = 5` direkt auf der Subscription."
        ),
        (
            "7. Post-Write Quality Gate in `pipeline.yaml` (Gefahr kurzzeitiger Dirty Reads)",
            "<b>Ist-Zustand (Schwachstelle):</b> In `infra/workflows/pipeline.yaml` überschreibt Schritt 4 (`refresh_fact_table`) zuerst die produktive Tabelle `fact_video_metrics`, und erst Schritt 5 (`quality_gate_validation`) prüft auf verwaiste Fremdschlüssel. Schlägt das Gate fehl, stehen die fehlerhaften Daten bereits in der Tabelle.<br/>"
            "<b>Enterprise-Mitigation:</b> Umsetzung des **Write-Audit-Publish (WAP)** Patterns: Der Workflow schreibt zuerst in eine isolierte Staging-Tabelle `fact_video_metrics_wap`, führt darauf das Quality Gate aus und kopiert sie erst bei `invalid_count == 0` atomar per `CREATE OR REPLACE TABLE ... CLONE` in die Produktion."
        ),
        (
            "8. Rein statische CI-Pipeline ohne Live-Datenbank-Integrationstests (Slim CI)",
            "<b>Ist-Zustand (Schwachstelle):</b> `.github/workflows/ci.yml` prüft Python-Syntax, Flake8-Regeln sowie YAML/JSON-Strukturen, führt aber kein `dbt build` gegen BigQuery aus, da keine Cloud-Credentials in GitHub hinterlegt sind. Ein subtiler SQL-Tippfehler würde erst beim Deployment auffallen.<br/>"
            "<b>Enterprise-Mitigation:</b> Anbindung von GitHub Actions per OIDC an ein dediziertes GCP-Testprojekt und Ausführung von `dbt build --select state:modified+ --defer --state ./prod-manifest` (Slim CI) in einem ephemeren Pull-Request-Dataset `youtube_analytics_ci_<PR_ID>`."
        )
    ]

    for r_title, r_body in risks:
        story.append(P(f"<b>{r_title}</b>", s['h3']))
        story.append(P(r_body, s['body']))
        story.append(Spacer(1, 2))

    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 13: DEPPENSICHERES BETRIEBSHANDBUCH (9 SCHRITTE & PLAYBOOKS)
    # =========================================================================
    story.extend(track(13))
    story.append(P("13. Deppensicheres Betriebshandbuch (9-Schritte-Anleitung & Playbooks)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Dieses Kapitel enthält die vollständige, **deppensichere Schritt-für-Schritt-Anleitung (End-to-End)** "
        "für das aktuelle Produktions-Release `v2.1.0` inklusive aller Voraussetzungen, IAM-Rollen, GCP-APIs, "
        "PowerShell-Runner und Fehlerbehebungs-Playbooks.",
        s['body']
    ))

    story.append(P("13.1 Checkliste der Voraussetzungen (IAM-Rollen & GCP APIs)", s['h2']))
    story.append(P("• <b>Lokale Systemumgebung:</b> Windows 10/11 mit PowerShell, Docker Desktop (gestartet, WSL2-Backend für den ephemeren Silver-PySpark-Job), Python 3.10+ sowie Terraform 1.17.", s['bullet']))
    story.append(P("• <b>GCP Projekt & Service Account Key:</b> Projekt-ID `cloudanalytics-514018` (Region `europe-west3` / Location `EU`). Der JSON-Key des Service Accounts `cloudanalytics-514018@cloudanalytics-514018.iam.gserviceaccount.com` liegt als `gcp_service_account.json` im Projekt-Root (via `.gitignore` geschützt).", s['bullet']))
    story.append(P("• <b>Die 6 zwingend erforderlichen GCP IAM-Rollen auf dem Service Account:</b><br/>"
                   "  1. `roles/bigquery.admin` (BigQuery Administrator)<br/>"
                   "  2. `roles/storage.admin` (Storage Administrator)<br/>"
                   "  3. `roles/pubsub.admin` (Pub/Sub Administrator — für Topics & Pull-Subscriptions)<br/>"
                   "  4. `roles/workflows.admin` (Workflows Administrator)<br/>"
                   "  5. `roles/iam.serviceAccountUser` (Dienstkonto-Nutzer — zwingend für Workflow-Deployment!)<br/>"
                   "  6. `roles/monitoring.viewer` (Monitoring-Betrachter — zwingend für Grafana Cloud!)", s['bullet']))
    story.append(P("• <b>Die 5 zwingend aktivierten Google Cloud APIs:</b><br/>"
                   "  `workflows.googleapis.com`, `monitoring.googleapis.com`, `pubsub.googleapis.com`, `bigquery.googleapis.com`, `storage.googleapis.com`.", s['bullet']))

    story.append(P("13.2 Die 9-Schritte End-to-End Ausführungssequenz für Release v2.1.0 (PowerShell)", s['h2']))
    code_9steps = (
        "# SCHRITT 1: Python Virtual Environment aktivieren & Abhaengigkeiten installieren\n"
        "cd D:\\Projekte\\CloudEng\\DE_Capstone_2026\n"
        "python -m venv .venv\n"
        "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n\n"
        "# SCHRITT 2: Cloud-Infrastruktur (7 GCP Ressourcen inkl. Pub/Sub Subs) per Terraform ausrollen\n"
        ".\\run_infra.ps1 init\n"
        ".\\run_infra.ps1 plan\n"
        ".\\run_infra.ps1 apply     # -> Apply complete! Resources: 7 added, 0 changed, 0 destroyed.\n\n"
        "# SCHRITT 3: Serverless Streaming Ingestion via Google Cloud Pub/Sub (Kein lokales Kafka noetig!)\n"
        ".\\run_pubsub_producer.ps1 # Sendet 444 Clean Events (topic-youtube-ingest) + 56 DLQ Events (topic-youtube-dlq)\n"
        ".\\run_pubsub_bronze.ps1   # Zieht 444 Events aus sub-youtube-ingest -> data/bronze/*.parquet\n"
        ".\\run_pubsub_dlq.ps1      # Isoliert 56 korrupte Events aus sub-youtube-dlq -> data/quarantine/*.parquet\n\n"
        "# SCHRITT 4: Silver Lakehouse Transformation (Ephemerer PySpark & Apache Iceberg V2)\n"
        ".\\run_silver.ps1          # Broadcast-Join + Commit in Iceberg (local.silver.videos) & data/silver/\n\n"
        "# SCHRITT 5: Bereinigte Silver-Daten idempotent nach Google BigQuery laden\n"
        ".\\load_to_bigquery.ps1    # Laedt 444 Zeilen in cloudanalytics-514018.youtube_analytics.silver_videos\n\n"
        "# SCHRITT 6: dbt Kimball Star-Schema, SCD-2 Snapshot & 15 Quality-Gate-Tests ausfuehren\n"
        ".\\run_dbt.ps1 debug       # Prueft BigQuery-Verbindung\n"
        ".\\run_dbt.ps1 snapshot    # Historisiert Titel-Mutationen (2kyS6SvSYSE) in dim_video_snapshot\n"
        ".\\run_dbt.ps1 run         # Baut stg_videos, dim_video, dim_category, dim_date, fact_video_metrics\n"
        ".\\run_dbt.ps1 test        # -> PASS=15 WARN=0 ERROR=0 SKIP=0 TOTAL=15\n\n"
        "# SCHRITT 7: Serverless Google Cloud Workflow in Frankfurt (europe-west3) ausfuehren\n"
        ".\\run_workflow.ps1        # -> Status: SUCCEEDED (0 orphan records in fact_video_metrics)\n\n"
        "# SCHRITT 8: Grafana Cloud verbinden (Google Cloud Monitoring -> gcp_service_account.json)\n"
        "#            & Dashboard importieren: dashboards/youtube_dataops_monitoring.json\n\n"
        "# SCHRITT 9: Aufraeumen & 0-EUR-Kostengarantie nach Testende\n"
        ".\\run_infra.ps1 destroy   # Loescht alle 7 GCP-Ressourcen rueckstandslos (0,00 EUR Kosten)"
    )
    story.append(make_code_block(code_9steps, s))
    story.append(PageBreak())

    story.append(P("13.3 Vollständige Referenz aller PowerShell-Runner (`.ps1`)", s['h2']))

    runner_table = [
        [P("<b>Runner-Skript</b>", s['th']), P("<b>Parameter</b>", s['th']), P("<b>Release-Status & Funktion</b>", s['th'])],
        [P("`run_infra.ps1`", s['td_bold']), P("`init`, `plan`, `apply`, `destroy`", s['td']), P("<b>[v2.1 Active]</b> Steuert Terraform 1.17 in `infra/` (7 GCP-Ressourcen).", s['td'])],
        [P("`run_pubsub_producer.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.1 Active]</b> Serverless GCP Pub/Sub Producer (444 Clean, 56 DLQ, SCD-2 Mutationen).", s['td'])],
        [P("`run_pubsub_bronze.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.1 Active]</b> Serverless Pull-Consumer (`sub-youtube-ingest` -> `data/bronze/*.parquet`).", s['td'])],
        [P("`run_pubsub_dlq.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.1 Active]</b> Serverless Pull-Consumer (`sub-youtube-dlq` -> `data/quarantine/*.parquet`).", s['td'])],
        [P("`run_silver.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0/v2.1 Active]</b> Startet Docker PySpark (`transform_silver.py`) & committet Iceberg V2.", s['td'])],
        [P("`load_to_bigquery.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0/v2.1 Active]</b> Lädt Silver-Parquet idempotent nach BigQuery (`silver_videos`).", s['td'])],
        [P("`run_dbt.ps1`", s['td_bold']), P("`debug`, `snapshot`, `run`, `test`", s['td']), P("<b>[v2.0/v2.1 Active]</b> Steuert dbt Core CLI (SCD-2 Snapshots, Star-Schema, 15 Tests).", s['td'])],
        [P("`run_workflow.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.1 Active]</b> Triggert den Serverless Cloud Workflow via REST und pollt bis `SUCCEEDED`.", s['td'])],
        [P("`start_kafka.ps1` / `stop_kafka.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0/v2.0 Legacy / Optional]</i> Lokaler Docker-Kafka-Stack (in v2.1 durch Pub/Sub ersetzt).", s['td'])],
        [P("`run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0/v2.0 Legacy / Optional]</i> Lokale Kafka Producer/Consumer (in v2.1 durch `run_pubsub_*.ps1` ersetzt).", s['td'])],
        [P("`run_gold.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0 Legacy]</i> Altes Spark-Gold-Skript (ab v2.0 durch `run_dbt.ps1` abgelöst).", s['td'])],
        [P("`start_monitoring.ps1` / `stop_monitoring.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0 Legacy]</i> Lokaler Prometheus/Grafana Stack (in v2.1 durch Grafana Cloud abgelöst).", s['td'])],
        [P("`start_airflow.ps1` / `stop_airflow.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0 Legacy]</i> Lokaler Airflow 2.9 Stack (in v2.1 durch Cloud Workflows abgelöst).", s['td'])]
    ]
    t_run = Table(runner_table, colWidths=[135, 115, 245])
    t_run.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_run)
    story.append(Spacer(1, 10))

    story.append(P("13.4 Produktions-Troubleshooting Playbooks (Aus echten Fehlern gelernt)", s['h2']))

    story.append(P("<b>Playbook 1: GCP IAM `Error 403: Permission denied` beim Terraform Workflow-Deployment</b>", s['h3']))
    story.append(P(
        "• <i>Symptom:</i> `terraform apply` schlägt beim Erstellen von `google_workflows_workflow` mit `403 Permission 'workflows.workflows.create' or 'iam.serviceAccounts.actAs' denied` fehl.<br/>"
        "• <i>Ursache:</i> Zum Binden eines Service Accounts an einen Cloud Workflow benötigt der ausführende Account neben `roles/workflows.admin` zwingend auch `roles/iam.serviceAccountUser`.<br/>"
        "• <i>Lösung:</i> Den existierenden Service Account (`var.service_account_email`) in `infra/main.tf` referenzieren und ihm in der GCP Console `roles/workflows.admin` sowie `roles/iam.serviceAccountUser` zuweisen.",
        s['body']
    ))

    story.append(P("<b>Playbook 2: Cloud Workflows Parser-Fehler (`400 characters limit` & `multiple step types`)</b>", s['h3']))
    story.append(P(
        "• <i>Symptom 1:</i> `maximum length for an expression is 400 characters, the provided expression has a length of 743`.<br/>"
        "• <i>Symptom 2:</i> `step 'evaluate_quality_gate': step matches multiple types: 'switch', 'assign'`.<br/>"
        "• <i>Lösung:</i> In `infra/workflows/pipeline.yaml` lange SQL-Abfragen in mehrere Variablen (`q_target`, `q_select`, `q_from`, `q_join`) aufteilen und `assign` (`get_quality_result`) strikt vom nachfolgenden `switch`-Schritt (`evaluate_quality_gate`) trennen.",
        s['body']
    ))

    story.append(P("<b>Playbook 3: Grafana Cloud Import meldet `No data sources of type cloudmonitoring found`</b>", s['h3']))
    story.append(P(
        "• <i>Symptom:</i> Beim Import des Dashboard-JSONs lässt sich die konfigurierte Google Cloud Monitoring Datenquelle nicht auswählen.<br/>"
        "• <i>Ursache:</i> Grafana verwendet intern die Plugin-ID `stackdriver` (nicht `cloudmonitoring`).<br/>"
        "• <i>Lösung:</i> In `dashboards/youtube_dataops_monitoring.json` ist `\"pluginId\": \"stackdriver\"` und `\"type\": \"stackdriver\"` gesetzt. Zudem benötigt der Service Account die Rolle `roles/monitoring.viewer`.",
        s['body']
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 14: INTERVIEW MASTERCLASS & TECHNICAL DEFENSE (25 Q&AS)
    # =========================================================================
    story.extend(track(14))
    story.append(P("14. Data Engineering Interview Masterclass & Technical Defense (25 Deep-Dive Q&As)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Dieses Kapitel dient als umfassendes Repetitorium für technische Architektur-Reviews und Vorstellungsgespräche "
        "auf Senior- und Lead-Data-Engineer-Niveau. Es liefert präzise, praxiserprobte Antworten auf **25 tiefgehende Fachfragen** "
        "rund um dieses Projekt.",
        s['body']
    ))

    qa_list = [
        (
            "F1: Warum haben Sie sich für Apache Iceberg V2 anstelle von reinem Parquet entschieden?",
            "Parquet ist lediglich ein Dateiformat, keine Tabellen-Abstraktion. Lose Parquet-Dateien bieten keine ACID-Transaktionen "
            "(Gefahr von Dirty Reads bei Jobabbrüchen), kein Time-Travel und erfordern teure Directory-Listings. "
            "Apache Iceberg V2 verwaltet Metadaten hierarchisch (`v1.metadata.json` -> `snap-*.avro` -> `*-m0.avro`), "
            "garantiert atomare Commits per Compare-and-Swap und ermöglicht Data Skipping über Spaltenstatistiken."
        ),
        (
            "F2: Warum haben Sie Google Cloud Workflows statt Apache Airflow (Cloud Composer) gewählt?",
            "Eine bewusste FinOps- und Architekturentscheidung: Cloud Composer benötigt einen dauerhaft laufenden GKE-Cluster "
            "(~300 €/Monat), selbst wenn die Pipeline nur wenige Minuten am Tag läuft. Da unsere Transformationslogik "
            "vollständig in BigQuery liegt (ELT), benötigen wir lediglich eine leichtgewichtige State-Machine zur Orchestrierung. "
            "Cloud Workflows startet in Millisekunden, ist 100% serverlos und kostet im Always Free Tier exakt 0,00 €."
        ),
        (
            "F3: Wie handhaben Sie Slowly Changing Dimensions (SCD-2) und warum reicht SCD-1 nicht?",
            "Bei SCD-1 überschreibt eine Titeländerung (wie bei Video `2kyS6SvSYSE`) den alten Wert — historische Analysen "
            "über den Effekt von Titel-Mutationen auf Klickraten sind damit unmöglich. Unser dbt Snapshot (`dim_video_snapshot`) "
            "implementiert SCD-2 (`strategy='check'`), schließt alte Versionen mit `valid_to` ab und legt eine neue Zeile mit "
            "`is_current = true` an. In `fact_video_metrics` ordnet ein Point-in-Time Join jedes Event exakt der damals gültigen Version zu."
        ),
        (
            "F4: Was ist der Unterschied zwischen den 15 dbt-Tests und dem In-Workflow Quality Gate?",
            "Die 15 dbt-Tests (`schema.yml`) prüfen beim Build-Prozess alle 4 Core-Marts auf `unique`, `not_null` und "
            "`relationships`. Das In-Workflow Quality Gate (`pipeline.yaml`) ist dagegen ein Laufzeit-Wächter direkt in der "
            "Cloud-Orchestrierung: Nach jedem Refresh von `fact_video_metrics` zählt ein `LEFT JOIN`-Check verwaiste Fremdschlüssel "
            "und wirft bei `invalid_count > 0` sofort eine Exception (`raise`)."
        ),
        (
            "F5: Wie verhindern Sie, dass fehlerhafte Streaming-Nachrichten die Pipeline zum Absturz bringen?",
            "Durch das Dead-Letter-Queue-Muster (DLQ): `src/cloud_pubsub_producer.py` (bzw. `src/producer.py`) injiziert 10% korrupte Nachrichten "
            "(`views = 'CORRUPT_INVALID_NUMBER'`), leitet diese aber sofort in das Quarantäne-Topic `topic-youtube-dlq` um, während die 444 validen Events "
            "über `topic-youtube-ingest` ungestört verarbeitet werden. `src/cloud_pubsub_consumer_dlq.py` persistiert die 56 Fehler-Events samt `_error_reason` unter `data/quarantine/`."
        ),
        (
            "F6: Warum wird das Zielvideo `2kyS6SvSYSE` im Producer von der 10% Fault-Injection ausgenommen?",
            "Um 100% deterministische, reproduzierbare End-to-End-Tests für SCD-2 zu garantieren (`if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE`). "
            "Würde eine der drei Titel-Mutationen zufällig in der DLQ landen, wäre die SCD-2-Versionskette nicht deterministisch testbar."
        ),
        (
            "F7: Warum verbinden sich die lokalen Kafka-Skripte mit `127.0.0.1:9092` statt `localhost:9092`?",
            "Unter Windows 10/11 löst `localhost` bevorzugt auf IPv6 (`::1`) auf. Wenn der Docker-Port-Forwarder auf IPv4 bindet, "
            "verursacht jeder Verbindungsaufbau einen 2-sekündigen TCP-SYN-Timeout vor dem Fallback auf IPv4. `127.0.0.1:9092` "
            "erzwingt sofortiges IPv4 ohne Disconnect-Lag."
        ),
        (
            "F8: Warum führt `src/transform_silver.py` einen Dual-Write (Iceberg V2 + Parquet) durch?",
            "Die Iceberg-Tabelle `local.silver.videos` liefert das volle Open-Table-Format mit Snapshot-Historie und ACID-Garantien "
            "im Lakehouse. Der zusätzliche Parquet-Export nach `/app/data/silver` dient als schlanker Transfer-Staging-Puffer "
            "für den lokalen Upload-Client `src/cloud_loader_bigquery.py` nach BigQuery."
        ),
        (
            "F9: Warum ist der Broadcast-Join in PySpark so entscheidend für die Performance?",
            "Ein Standard-SortMergeJoin müsste sowohl die großen Video-Events als auch die Kategorien über das Netzwerk nach "
            "`category_id` shuffeln. Da `US_category_id.json` winzig ist (< 50 KB), sendet `broadcast(df_categories)` die "
            "Lookup-Tabelle einmalig in den RAM jedes Executors. Der Join erfolgt rein lokal im Speicher (Zero Shuffle)."
        ),
        (
            "F10: Wie garantieren Sie Idempotenz über alle Pipeline-Stufen hinweg?",
            "1. Silver Iceberg: `.writeTo('local.silver.videos').createOrReplace()` ersetzt den Snapshot atomar. "
            "2. BigQuery Loader: `WriteDisposition.WRITE_TRUNCATE` überschreibt `silver_videos` ohne Duplikate. "
            "3. dbt Staging (`stg_videos.sql`): Dedupliziert per `QUALIFY row_number() OVER (PARTITION BY video_id, trending_date ORDER BY _ingested_at DESC) = 1`. "
            "4. dbt Marts & Cloud Workflow: Aktualisieren Tabellen atomar per `CREATE OR REPLACE TABLE` mit deterministischen MD5-Schlüsseln (`metric_key`)."
        ),
        (
            "F11: Warum haben Sie in `pipeline.yaml` das SQL-Statement in vier Variablen aufgeteilt?",
            "Google Cloud Workflows besitzt ein hartes Parser-Limit von 400 Zeichen pro `${...}`-Ausdruck. "
            "Ein einzelner Ausdruck mit 743 Zeichen wird beim Deployment abgelehnt. Durch die Aufteilung in `q_target`, "
            "`q_select`, `q_from` und `q_join` bleibt jeder Teilstring unter 400 Zeichen und wird erst in `${q_target + q_select + q_from + q_join}` zusammengefügt."
        ),
        (
            "F12: Wie optimieren Sie BigQuery-Kosten bei wachsendem Datenvolumen (Terabyte-Scale)?",
            "Im On-Demand-Tarif berechnet BigQuery nach gescannten Bytes. Bei großen Datenmengen partitionieren wir `fact_video_metrics` "
            "nach `trending_date` (`PARTITION BY trending_date`) und clustern nach `category_key, video_key` (`CLUSTER BY`). "
            "Zusätzlich überwacht unser Grafana-Dashboard live die Metrik `bigquery.googleapis.com/query/scanned_bytes_billed`."
        ),
        (
            "F13: Warum verwendet man Surrogate Keys (`video_key`) statt Natural Keys (`video_id`) im Star-Schema?",
            "Weil `video_id` in einer SCD-2-Dimension (`dim_video`) nicht mehr eindeutig ist: Dasselbe Video hat bei 3 Titelversionen "
            "3 Zeilen mit derselben `video_id`. Erst der Surrogate Key (`video_key = dbt_scd_id`) identifiziert exakt die "
            "historische Version, auf die die Faktentabelle verweist."
        ),
        (
            "F14: Wie funktioniert CI/CD in einer echten Enterprise-Produktionsumgebung (GitOps)?",
            "Kein Entwickler führt in Produktion manuell `dbt run` oder `terraform apply` aus. Änderungen laufen über Pull Requests: "
            "GitHub Actions authentifiziert sich keyless per OIDC (Workload Identity) gegen GCP, führt `terraform plan` und "
            "einen dbt Slim-CI-Lauf (`state:modified+`) in einem isolierten CI-Dataset aus. Erst nach Code-Review und Merge auf "
            "`main` rollt die CD-Pipeline die Änderungen automatisch nach `prod` aus."
        ),
        (
            "F15: Welche Komponenten aus Release v1.0.0 und v2.0.0 sind in Release v2.1.0 obsolet und warum?",
            "1. Lokales Docker-Kafka (`start_kafka.ps1`, `run_producer.ps1`, `run_bronze.ps1`, `run_dlq.ps1`) wurde in `v2.1.0` durch serverloses Google Cloud Pub/Sub (`run_pubsub_*.ps1`) abgelöst. "
            "2. Lokaler Airflow (`start_airflow.ps1`, `dags/`) wurde durch Google Cloud Workflows ersetzt. "
            "3. Lokaler Prometheus/Grafana (`start_monitoring.ps1`) wurde durch Grafana Cloud ('Weg 1' direkt auf GCP Monitoring) ersetzt. "
            "4. Das alte Spark-Gold-Skript (`run_gold.ps1`) wurde bereits ab `v2.0.0` durch das dbt Kimball Star-Schema in BigQuery ersetzt."
        ),
        (
            "F16: Worin unterscheiden sich Google Cloud Pub/Sub (v2.1) und Apache Kafka KRaft (v1.0/v2.0) architektonisch?",
            "Kafka basiert auf einem partitionierten Commit-Log mit fortlaufenden Offsets pro Consumer-Group und erfordert laufende Broker-Instanzen; Ordering wird pro Partition garantiert. "
            "Cloud Pub/Sub ist dagegen ein global verteilter, serverloser Message-Bus mit Entkopplung von Topics und Subscriptions (`sub-youtube-ingest`), "
            "Message-Level Ack-Deadlines (60s) und 0,00 € Idle-Kosten ohne jegliche Cluster-Wartung."
        ),
        (
            "F17: Was ist das Write-Audit-Publish (WAP) Pattern und warum ist es sicherer als ein Post-Write Quality Gate?",
            "Bei unserem aktuellen Post-Write Gate in `pipeline.yaml` wird erst `fact_video_metrics` überschrieben und danach auf verwaiste Fremdschlüssel geprüft. "
            "Schlägt der Check fehl, sehen BI-Nutzer bereits korrupte Daten. Beim WAP-Pattern schreibt die Pipeline zuerst in eine isolierte "
            "Staging-Tabelle (`fact_video_metrics_wap`), führt alle Audits darauf aus und publiziert sie erst bei 0 Fehlern per Zero-Copy Table Clone (`CREATE OR REPLACE TABLE ... CLONE`) in die Produktion."
        ),
        (
            "F18: Wie eliminiert man im Enterprise-Ausbau den Kopierschritt `load_to_bigquery.py` mittels BigQuery BigLake?",
            "Indem PySpark die Apache Iceberg V2 Tabelle direkt in den GCS-Bucket (`gs://lakehouse-youtube-cloudanalytics-514018/iceberg/silver/videos`) schreibt. "
            "Über eine **BigQuery BigLake Iceberg Table** liest BigQuery die `vN.metadata.json` und Parquet-Dateien direkt auf GCS mit voller "
            "Spalten-Zugriffskontrolle und Snapshot-Isolation, ohne dass Daten physisch dupliziert oder hochgeladen werden müssen."
        ),
        (
            "F19: Welche Schwachstelle hat `dbt snapshot` bei mehreren Mutationen desselben Videos innerhalb eines einzigen Micro-Batches?",
            "`dbt snapshot` kann pro Aufruf für einen `unique_key` (`video_id`) nur genau einen neuen Zustand mit dem aktuellen Bestand vergleichen. "
            "Deshalb muss `dim_video_snapshot.sql` via `QUALIFY row_number() = 1` auf den jüngsten Satz pro Batch deduplizieren; Zwischenmutationen innerhalb desselben Batches gehen verloren. "
            "Um jede Einzelmutation eines Batches zu erfassen, berechnet man `valid_from` und `valid_to` (`LEAD(trending_date) OVER (...)`) direkt als deterministische Window-Function im dbt-Modell."
        ),
        (
            "F20: Warum ist eine lokale `terraform.tfstate`-Datei im Team-Betrieb gefährlich und wie löst man das?",
            "Liegt `terraform.tfstate` lokal auf einem Laptop, haben andere Teammitglieder und CI/CD-Runner keinen Zugriff auf den aktuellen Infrastruktur-State. "
            "Führen zwei Personen gleichzeitig `terraform apply` aus, kommt es zu Race-Conditions und Ressourcen-Korruption. "
            "Im Enterprise-Umfeld nutzt man ein `backend \"gcs\"` in einem versionierten GCS-Bucket, das über `.tflock`-Dateien automatisches State-Locking erzwingt."
        ),
        (
            "F21: Wie sieht ein striktes Least-Privilege IAM-Konzept für diese Plattform aus?",
            "Statt eines einzigen Sammel-Service-Accounts mit `*.admin`-Rollen trennt man nach dem Least-Privilege-Prinzip: "
            "1. `sa-cicd-terraform` (nur für Infrastruktur-Provisionierung in GitHub Actions), "
            "2. `sa-ingest-producer` (`roles/pubsub.publisher` nur auf den beiden Topics), "
            "3. `sa-workflow-runtime` (`roles/bigquery.dataEditor` auf Dataset-Ebene + `roles/bigquery.jobUser`), "
            "4. `sa-grafana-reader` (ausschließlich Read-Only `roles/monitoring.viewer`)."
        ),
        (
            "F22: Wie behandelt das Star-Schema Late-Arriving Facts oder Early-Arriving Facts (Late-Arriving Dimensions)?",
            "Trifft ein Fakt ein, dessen `trending_date` zeitlich vor dem ersten `valid_from`-Zeitstempel der zugehörigen `dim_video`-Version liegt, "
            "würde ein strikter Point-in-Time `INNER JOIN` den Fakt verwerfen. Im Enterprise-DWH setzt man bei der initialen Version eines Videos "
            "`valid_from` auf ein technisches Startdatum (`1970-01-01`) oder nutzt einen `LEFT JOIN` mit Fallback auf einen Dummy-Dimensionssatz (`video_key = '-1'`, 'Unknown Version')."
        ),
        (
            "F23: Was ist das 'Small File Problem' in Apache Iceberg V2 bei hochfrequentem Streaming und wie behebt man es?",
            "Schreibt ein Streaming-Consumer jede Minute eine kleine Parquet-Datei (z. B. 90 KB), entstehen tausende Kleinstdateien und Manifeste. "
            "Abfragen verlangsamen sich durch hohen Metadaten- und I/O-Overhead drastisch. Iceberg löst dies durch periodische Hintergrund-Compaction: "
            "`CALL local.system.rewrite_data_files(table => 'silver.videos', options => map('target-file-size-bytes', '134217728'))` bündelt kleine Dateien atomar zu 128-MB-Dateien, ohne laufende Leser zu blockieren."
        ),
        (
            "F24: Wie erzwingt man Schema-Validierung bereits beim Senden an Google Cloud Pub/Sub (Schema-on-Write at the Edge)?",
            "Anstatt fehlerhafte Datentypen erst im Consumer oder PySpark zu erkennen, definiert man in Terraform eine `google_pubsub_schema`-Ressource "
            "(im **Apache Avro** oder **Protocol Buffers** Format) und bindet diese an `topic-youtube-ingest`. "
            "Pub/Sub lehnt dann jede Nachricht, bei der `views` kein `long` ist, bereits am API-Gateway synchron mit `HTTP 400 InvalidArgument` ab."
        ),
        (
            "F25: Wie sieht das Disaster-Recovery-Konzept (RTO / RPO) für diese Plattform aus?",
            "• **Infrastruktur (RTO < 2 Minuten):** Durch Terraform IaC (`run_infra.ps1 apply`) lassen sich alle 7 GCP-Ressourcen in einer neuen Region sofort wiederherstellen. "
            "• **Streaming-Puffer (RPO = 0 bei Ausfall < 7 Tage):** Die Pub/Sub Subscriptions (`sub-youtube-ingest` / `sub-youtube-dlq`) speichern unbestätigte Nachrichten 7 Tage lang (`message_retention_duration = 604800s`). "
            "• **Data Warehouse & Lakehouse:** BigQuery bietet 7-Tage Time-Travel (`FOR SYSTEM_TIME AS OF`), der GCS-Bucket hat Object Versioning aktiviert, und Apache Iceberg V2 erlaubt Rollbacks auf jeden historischen Snapshot."
        )
    ]

    for q, a in qa_list:
        story.append(P(f"<b>{q}</b>", s['h2']))
        story.append(P(a, s['body']))
        story.append(Spacer(1, 2))

    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 15: FINOPS, KOSTEN-ENGINEERING & KAPAZITÄTSPLANUNG
    # =========================================================================
    story.extend(track(15))
    story.append(P("15. FinOps, Kosten-Engineering & Always-Free-Tier Kapazitätsplanung", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Kostenoptimierung (**FinOps**) ist eine Kernverantwortung moderner Data Architects. "
        "Die gesamte YouTube DataOps Plattform (`v2.1.0`) ist so konzipiert, dass sie dauerhaft innerhalb "
        "des **Google Cloud Always Free Tiers** und **Grafana Cloud Free Tiers** betrieben werden kann.",
        s['body']
    ))

    story.append(P("15.1 Nachweis der 0,00 € Betriebskosten (Free Tier Kontingente vs. Verbrauch)", s['h2']))

    finops_data = [
        [P("<b>Cloud-Dienst</b>", s['th']), P("<b>Monatliches Free-Tier-Kontingent</b>", s['th']), P("<b>Realer Projekt-Verbrauch</b>", s['th']), P("<b>Effektive Kosten</b>", s['th'])],
        [
            P("<b>Google BigQuery</b>", s['td_bold']),
            P("10 GB aktiver Speicher + 1 TB Abfragevolumen pro Monat frei.", s['td']),
            P("< 5 MB Speicher (444 Zeilen) / < 100 MB Queries pro Monat.", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ],
        [
            P("<b>Cloud Storage (GCS)</b>", s['td_bold']),
            P("5 GB Standard-Storage frei; minimale Gebühren in EU bei Kleinstmengen.", s['td']),
            P("Bucket `lakehouse-youtube-...` (< 10 MB; via `destroy` jederzeit löschbar).", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ],
        [
            P("<b>Cloud Pub/Sub</b>", s['td_bold']),
            P("10 GB Nachrichtenvolumen pro Monat kostenlos.", s['td']),
            P("< 5 MB für Topics (`topic-youtube-ingest`/`dlq`) & Subscriptions (`sub-youtube-*`).", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ],
        [
            P("<b>Cloud Workflows</b>", s['td_bold']),
            P("5.000 interne Workflow-Schritte pro Monat kostenlos.", s['td']),
            P("8 Schritte pro Workflow-Lauf (~240 Schritte bei täglichem Lauf).", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ],
        [
            P("<b>Cloud Monitoring</b>", s['td_bold']),
            P("Alle Standard-GCP-Dienstmetriken (`workflows`, `bigquery`, `pubsub`) kostenlos.", s['td']),
            P("Ausschließliche Nutzung kostenloser GCP-Systemmetriken.", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ],
        [
            P("<b>Grafana Cloud</b>", s['td_bold']),
            P("Free Forever Plan: 3 User, 10k Metriken, 50 GB Logs inklusive.", s['td']),
            P("1 User, 1 Dashboard (`youtube_dataops_monitoring.json`).", s['td']),
            P("<b>0,00 € / Monat</b>", s['td_bold'])
        ]
    ]
    t_finops = Table(finops_data, colWidths=[105, 145, 135, 110])
    t_finops.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s['primary']),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_finops)
    story.append(Spacer(1, 10))

    story.append(P("15.2 Implementierte Cost Guardrails (Schutz vor Kostenfallen)", s['h2']))
    story.append(P("• <b>Terraform Teardown-Garantie (`run_infra.ps1 destroy`):</b> Durch `force_destroy = true` am GCS-Bucket und `delete_contents_on_destroy = true` am BigQuery-Dataset lassen sich sämtliche 7 Cloud-Ressourcen jederzeit mit einem einzigen Befehl rückstandslos entfernen.", s['bullet']))
    story.append(P("• <b>Grafana FinOps-Schwellenwerte:</b> Panel 4 (`BigQuery Bytes Billed`) schlägt bei über 100 MB auf Orange und bei 1 GB auf Rot um, sodass teure Abfragen sofort sichtbar werden.", s['bullet']))
    story.append(P("• <b>Verzicht auf 24/7-Cluster:</b> Weder für Streaming (Serverless Cloud Pub/Sub) noch für Compute (ephemerer Docker-PySpark), Orchestrierung (Serverless Cloud Workflows) oder Monitoring (Grafana Cloud Weg 1) laufen dauerhafte VMs oder Kubernetes-Cluster.", s['bullet']))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=12))
    story.append(P(
        "<b>Schlusswort:</b> Dieses Repertorium dokumentiert den vollständigen, verifizierten Stand der "
        "**YouTube DataOps & Analytics Platform (2026 Edition)** über alle drei Releases (`v1.0.0`, `v2.0.0`, `v2.1.0`). "
        "Alle beschriebenen Skripte, Modelle, Tests, Terraform-Ressourcen, Cloud Workflows und Dashboards "
        "stimmen zu 100% mit dem produktiven Code im Repository überein.",
        s['body']
    ))

    return story


def build_pdf(filename="docs/YouTube_DataOps_Platform_2026_Architektur_Repertorium.pdf"):
    out_path = Path(filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    s = get_document_styles()

    # PASS 1: Dynamische Ermittlung der exakten Kapitel-Seitenzahlen im Speicher
    tracker_dict = {}
    pass1_story = generate_story(s, chapter_pages=None, tracker_dict=tracker_dict)
    mem_buffer = io.BytesIO()
    doc_pass1 = SimpleDocTemplate(
        mem_buffer,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=54,
        bottomMargin=54
    )
    doc_pass1.build(pass1_story, canvasmaker=NumberedCanvas)

    print("Pass 1 abgeschlossen. Exakt ermittelte Kapitel-Seitenzahlen:")
    for ch_id in sorted(tracker_dict.keys()):
        print(f"  Kapitel {ch_id:2d}: Seite {tracker_dict[ch_id]}")

    # PASS 2: Finales Dokument mit 100% abgestimmtem Inhaltsverzeichnis
    pass2_tracker = {}
    pass2_story = generate_story(s, chapter_pages=tracker_dict, tracker_dict=pass2_tracker)
    doc_pass2 = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=54,
        bottomMargin=54
    )
    doc_pass2.build(pass2_story, canvasmaker=NumberedCanvas)

    # Konsistenz-Assertion zwischen Pass 1 und Pass 2
    assert tracker_dict == pass2_tracker, f"TOC-Drift erkannt: {tracker_dict} != {pass2_tracker}"
    print(f"PDF erfolgreich und 100% konsistent generiert: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_pdf()
