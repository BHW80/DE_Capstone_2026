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
        [P("<b>Technologie-Stack:</b>", s['td_bold']), P("Apache Kafka KRaft, Apache Spark 3.5, Apache Iceberg V2, dbt Core 1.13, Google BigQuery, Terraform 1.17, Google Cloud Workflows, Grafana Cloud, GitHub Actions", s['td'])],
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
        "jede Architekturentscheidung (ADRs), die Migration von fragilen On-Premises-Altsystemen auf Open Table Formats "
        "(Apache Iceberg V2), den Aufbau eines dimensionalen Data Warehouse nach Ralph Kimball (SCD-2 via dbt Core), "
        "das Infrastructure-as-Code-Design mit Terraform 1.17, den 0-€ Kostenvorteil serverloser Cloud Workflows, "
        "das cloud-native Observability-Konzept via Grafana Cloud sowie die GitHub Actions CI/CD-Automatisierung. "
        "Zusätzlich grenzt es für alle drei Projekt-Releases (`v1.0.0`, `v2.0.0`, `v2.1.0`) präzise ab, welche "
        "Komponenten zwingend erforderlich sind und welche historisch abgelöst wurden."
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
        [P("<b>2. Die Evolutionsstufen & Release-Notwendigkeits-Matrix (v1.0 / v2.0 / v2.1)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(2, '-')}", s['td'])],
        [P("<b>3. End-to-End Systemarchitektur, Medallion Lakehouse & Repository-Struktur</b>", s['td_bold']), P(f"Seite {chapter_pages.get(3, '-')}", s['td'])],
        [P("<b>4. Streaming Ingestion & Resilienz (Kafka KRaft, DLQ & SCD-2 Mutation)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(4, '-')}", s['td'])],
        [P("<b>5. Ephemerer Compute & Open Table Format (Apache Iceberg V2)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(5, '-')}", s['td'])],
        [P("<b>6. Cloud Data Warehouse & Kimball Star-Schema (dbt Core & SCD-2)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(6, '-')}", s['td'])],
        [P("<b>7. DataOps Quality Gates: 15 dbt Tests & In-Workflow Validierung</b>", s['td_bold']), P(f"Seite {chapter_pages.get(7, '-')}", s['td'])],
        [P("<b>8. Infrastructure as Code (Terraform 1.17 Cloud Provisioning)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(8, '-')}", s['td'])],
        [P("<b>9. Serverlose Orchestrierung (Google Cloud Workflows State-Machine)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(9, '-')}", s['td'])],
        [P("<b>10. Cloud-Native Observability (Grafana Cloud & GCP Monitoring - Weg 1)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(10, '-')}", s['td'])],
        [P("<b>11. DataOps CI/CD Pipelines, GitOps & Release-Management</b>", s['td_bold']), P(f"Seite {chapter_pages.get(11, '-')}", s['td'])],
        [P("<b>12. Architectural Decision Records (ADRs 001 bis 006) im Detail</b>", s['td_bold']), P(f"Seite {chapter_pages.get(12, '-')}", s['td'])],
        [P("<b>13. Deppensicheres Betriebshandbuch (9-Schritte-Anleitung & Playbooks)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(13, '-')}", s['td'])],
        [P("<b>14. Data Engineering Interview Masterclass & Technical Defense (15 Q&As)</b>", s['td_bold']), P(f"Seite {chapter_pages.get(14, '-')}", s['td'])],
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
        "(Post Graduate Program in Data Engineering, Purdue University / Simplilearn 2021) in eine "
        "cloud-native Enterprise-Lösung nach modernsten Data-Engineering- und DevOps-Standards.",
        s['body']
    ))

    story.append(P("Kernmetriken & Business Impact im Vergleich:", s['h2']))

    kpi_table_data = [
        [P("<b>Dimension</b>", s['th']), P("<b>Legacy-System (2021)</b>", s['th']), P("<b>DataOps Platform (2026 v2.1)</b>", s['th']), P("<b>Business & Tech Impact</b>", s['th'])],
        [
            P("<b>Monatliche Infrastrukturkosten</b>", s['td_bold']),
            P("Hohe VM-Kosten oder unkalkulierbare Cloud-Cluster", s['td']),
            P("<b>0,00 € laufende Idle-Kosten</b> (Serverless Cloud Workflows & GCP Free Tier)", s['td']),
            P("100% Kostensicherheit; keine 24/7 GKE- oder Composer-Gebühren (~300 €/Monat gespart)", s['td'])
        ],
        [
            P("<b>Datenresilienz & Fehlertoleranz</b>", s['td_bold']),
            P("Pipeline bricht bei fehlerhaften Records komplett ab", s['td']),
            P("<b>Automatisierte Dead Letter Queue (DLQ)</b> Quarantäne (`topic_err`)", s['td']),
            P("Zero Data Loss: 295 Gutdaten fließen weiter, 31 korrupte Records (~10%) werden isoliert", s['td'])
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
            P("5 GCP-Ressourcen in 60 Sekunden reproduzierbar bereitgestellt und rückstandslos löschbar", s['td'])
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
        "Statt kostspielige Airflow-Cluster (Cloud Composer) 24/7 leerlaufen zu lassen, orchestriert ein "
        "serverloser Google Cloud Workflow BigQuery-Jobs und führt In-Database Quality Gates aus. "
        "Damit eignet sich dieses System als Blaupause für moderne Cloud Data Platforms in Startups wie im Enterprise-Umfeld.",
        s, "Architektur-Prämisse"
    ))
    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 2: DIE EVOLUTIONSSTUFEN & RELEASE-NOTWENDIGKEITS-MATRIX
    # =========================================================================
    story.extend(track(2))
    story.append(P("2. Die Evolutionsstufen & Release-Notwendigkeits-Matrix", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Um den technologischen Wert der aktuellen Architektur zu verstehen, muss man die vier Entwicklungsstufen "
        "des Projekts betrachten: vom fragilen 2021er On-Premises-Setup über das containerisierte Fundament (`v1.0.0`) "
        "und die Lakehouse/Kimball-Ausbaustufe (`v2.0.0`) bis hin zur serverlosen Cloud-Plattform (`v2.1.0`).",
        s['body']
    ))

    story.append(P("2.1 Die 2021 Legacy-Architektur (Historische Schmerzpunkte)", s['h2']))
    story.append(P("• <b>Windows OS-Inkompatibilität:</b> Lokale Hadoop/HDFS-Aufrufe scheiterten an Windows-Pfaden und erforderten inoffizielle `winutils.exe`-Binaries.", s['bullet']))
    story.append(P("• <b>ZooKeeper als Single Point of Failure:</b> Separate ZooKeeper-Prozesse führten unter Windows zu Verbindungsabbrüchen, Session-Timeouts und blockierten Kafka-Brokern.", s['bullet']))
    story.append(P("• <b>Fehlende Dead Letter Queue (DLQ):</b> Ein einziger korrupter Datensatz mit nicht-numerischen `views` brachte die gesamte Pipeline zum Absturz.", s['bullet']))
    story.append(P("• <b>SCD-1 Blindüberschreibung:</b> Änderungen an Videotiteln wurden ohne Historie überschrieben. Punktgenaue Analysen vor/nach Titeländerungen waren unmöglich.", s['bullet']))
    story.append(P("• <b>Manuelles ClickOps statt IaC/CI/CD:</b> Cloud-Ressourcen wurden per Mausklick angelegt; automatisierte Tests oder reproduzierbare Deployments existierten nicht.", s['bullet']))

    story.append(P("2.2 Die Evolutionsmatrix: Vergleich aller 4 Generationen", s['h2']))

    matrix_data = [
        [P("<b>Kriterium</b>", s['th']), P("<b>2021 Legacy</b>", s['th']), P("<b>v1.0.0 (Foundation)</b>", s['th']), P("<b>v2.0.0 (Lakehouse)</b>", s['th']), P("<b>v2.1.0 (Aktuell)</b>", s['th'])],
        [
            P("<b>Bereitstellung</b>", s['td_bold']),
            P("Bare Metal Windows", s['td']),
            P("Docker Compose", s['td']),
            P("Docker + Python `.venv`", s['td']),
            P("<b>Terraform 1.17 IaC</b>", s['td'])
        ],
        [
            P("<b>Streaming Engine</b>", s['td_bold']),
            P("Kafka + ZooKeeper", s['td']),
            P("Kafka KRaft (Zero-ZK)", s['td']),
            P("KRaft + SCD-2 Events", s['td']),
            P("<b>KRaft + GCP Pub/Sub</b>", s['td'])
        ],
        [
            P("<b>Resilienz & Fehler</b>", s['td_bold']),
            P("Keine (Jobabbruch)", s['td']),
            P("Parquet Quarantäne", s['td']),
            P("DLQ Consumer (`topic_err`)", s['td']),
            P("<b>DLQ + Pub/Sub Error Topic</b>", s['td'])
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
            P("Keine", s['td']),
            P("<b>SCD-2 dbt Snapshots</b>", s['td']),
            P("<b>Point-in-Time Join DWH</b>", s['td'])
        ],
        [
            P("<b>Quality Gates</b>", s['td_bold']),
            P("Keine", s['td']),
            P("Basis Row-Count", s['td']),
            P("<b>15 dbt Data Tests</b>", s['td']),
            P("<b>15 Tests + In-Workflow Gate</b>", s['td'])
        ],
        [
            P("<b>Orchestrierung</b>", s['td_bold']),
            P("Manuelle Batch-Skripte", s['td']),
            P("Airflow 2.9 (Docker)", s['td']),
            P("PowerShell Runner", s['td']),
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
    story.append(Spacer(1, 10))

    story.append(P("2.3 Notwendigkeits-Matrix über alle drei Releases (Was wird gebraucht – und was nicht?)", s['h2']))
    story.append(P(
        "Ein entscheidendes Qualitätsmerkmal professioneller DataOps-Dokumentation ist die glasklare Abgrenzung "
        "zwischen **zwingend notwendigen Produktivkomponenten** und **historisch abgelöstem Legacy-Code (Deprecations)** "
        "in jedem der drei Git-Releases (`v1.0.0`, `v2.0.0`, `v2.1.0`):",
        s['body']
    ))

    req_table_data = [
        [P("<b>Release</b>", s['th']), P("<b>Zwingend notwendig (Must-Have)</b>", s['th']), P("<b>Vollständig überflüssig / Nicht notwendig</b>", s['th'])],
        [
            P("<b>Release v1.0.0</b><br/><i>(Core Foundation)</i>", s['td_bold']),
            P(
                "• Docker Desktop & Docker Compose<br/>"
                "• Apache Kafka im KRaft-Modus (`127.0.0.1:9092`)<br/>"
                "• Streaming Producer mit DLQ (`src/producer.py`)<br/>"
                "• Bronze & DLQ Consumer (`src/consumer_bronze.py`, `src/consumer_dlq.py`)<br/>"
                "• Ephemerer Docker PySpark (`src/transform_silver.py`, `src/transform_gold.py`)<br/>"
                "• Lokaler Airflow 2.9 & PostgreSQL Stack (`dags/`, `docker-compose-airflow.yml`)<br/>"
                "• Lokaler Prometheus & Grafana Stack (`docker-compose-monitoring.yml`)",
                s['td']
            ),
            P(
                "• <b>Kein GCP Cloud Account zwingend nötig</b> (reines lokales Offline-Testing möglich)<br/>"
                "• <b>Kein BigQuery</b> (Speicherung rein lokal als Snappy Parquet)<br/>"
                "• <b>Kein dbt Core</b> (Transformationen rein in Spark Python)<br/>"
                "• <b>Kein Apache Iceberg</b> (nur lose Parquet-Dateien)<br/>"
                "• <b>Kein Terraform</b> (reine Docker Compose Verwaltung)<br/>"
                "• <b>Keine Cloud Workflows</b> (Scheduler ist lokaler Airflow)<br/>"
                "• <b>Keine Grafana Cloud</b> (lokaler Container auf Port 3000)<br/>"
                "• <b>Kein GitHub Actions CI/CD</b>",
                s['td']
            )
        ],
        [
            P("<b>Release v2.0.0</b><br/><i>(Lakehouse & Kimball Marts)</i>", s['td_bold']),
            P(
                "• Python Virtual Environment (`.venv`) mit `requirements.txt`<br/>"
                "• GCP Projekt (`cloudanalytics-514018`) & Key (`gcp_service_account.json`)<br/>"
                "• GCP IAM-Rollen: `roles/bigquery.admin`, `roles/storage.admin`<br/>"
                "• Apache Iceberg V2 Runtime im Spark-Container (`iceberg-spark-runtime-3.5`)<br/>"
                "• Iceberg Warehouse (`data/iceberg_warehouse/silver/videos/`)<br/>"
                "• dbt Core Projekt (`dbt/`) mit BigQuery-Profil (`profiles.yml`)<br/>"
                "• dbt SCD-2 Snapshots (`dim_video_snapshot.sql`)<br/>"
                "• 15 automatisierte dbt Tests (`schema.yml`)<br/>"
                "• Idempotenter BigQuery Uploader (`src/cloud_loader_bigquery.py`, `load_to_bigquery.ps1`)",
                s['td']
            ),
            P(
                "• <b>Altes Spark Gold Script (`src/transform_gold.py`, `run_gold.ps1`):</b> Nicht mehr nötig! Vollständig durch dbt Kimball Marts in BigQuery abgelöst.<br/>"
                "• <b>Lose Parquet-Dateien als alleiniger Silver-Layer:</b> Durch Apache Iceberg V2 mit ACID-Commits und Snapshot-Historie ersetzt.<br/>"
                "• <b>SCD-1 Überschreibung:</b> Abgelöst durch SCD-2 Snapshot Historisierung.<br/>"
                "• <b>Noch nicht vorhanden / nicht nötig:</b> Terraform, Cloud Workflows, Pub/Sub Topics, Grafana Cloud, GitHub Actions CI/CD.",
                s['td']
            )
        ],
        [
            P("<b>Release v2.1.0</b><br/><i>(Serverless Cloud & Observability)</i><br/><b>[AKTUELLE PRODUKTION]</b>", s['td_bold']),
            P(
                "• Terraform 1.17 (`run_infra.ps1`)<br/>"
                "• GCP Service Account mit 6 IAM-Rollen (`bigquery.admin`, `storage.admin`, `pubsub.admin`, `workflows.admin`, `iam.serviceAccountUser`, `monitoring.viewer`)<br/>"
                "• 5 aktivierte GCP APIs (`workflows`, `monitoring`, `pubsub`, `bigquery`, `storage`)<br/>"
                "• Deklarative Cloud-Infrastruktur (`infra/main.tf`, `variables.tf`, `versions.tf`)<br/>"
                "• Serverless Cloud Workflow State-Machine (`infra/workflows/pipeline.yaml`)<br/>"
                "• REST Workflow-Runner (`src/cloud_workflow_runner.py`, `run_workflow.ps1`)<br/>"
                "• In-Workflow Quality Gate (Foreign-Key-Orphan-Check in BigQuery)<br/>"
                "• Grafana Cloud mit nativer Google Cloud Monitoring Data Source (Weg 1)<br/>"
                "• Dashboard-as-Code (`dashboards/youtube_dataops_monitoring.json`)<br/>"
                "• GitHub Actions CI/CD (`.github/workflows/ci.yml`, `release.yml`)",
                s['td']
            ),
            P(
                "• <b>Lokaler Airflow Stack (`dags/`, `docker-compose-airflow.yml`, `start_airflow.ps1`, `stop_airflow.ps1`):</b> "
                "<b>VOLLSTÄNDIG ÜBERFLÜSSIG!</b> Zu 100% durch den serverlosen Google Cloud Workflow abgelöst. "
                "Spart 24/7 laufende Container und im Cloud-Betrieb ~300 €/Monat für Cloud Composer.<br/>"
                "• <b>Lokaler Prometheus & Grafana Container-Stack (`docker-compose-monitoring.yml`, `start_monitoring.ps1`, `stop_monitoring.ps1`):</b> "
                "<b>NICHT MEHR NÖTIG!</b> Grafana Cloud fragt GCP Monitoring direkt serverlos ab (0 lokale Daemons, 0 CPU-Last).<br/>"
                "• <b>Altes Spark Gold Script (`src/transform_gold.py`, `run_gold.ps1`):</b> Veraltet und redundant.<br/>"
                "• <b>Manuelle Klicks in der GCP Webkonsole ('ClickOps'):</b> Durch Terraform vollständig eliminiert.",
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
        "<b>Wichtige Betriebs-Leitlinie für Release v2.1.0 (Aktuell):</b> Für den regulären Betrieb und Tests müssen "
        "<b>weder Airflow (`start_airflow.ps1`) noch der lokale Monitoring-Stack (`start_monitoring.ps1`) gestartet werden!</b> "
        "Die gesamte Produktions-Pipeline läuft serverlos über Terraform (`run_infra.ps1`), BigQuery-Loader (`load_to_bigquery.ps1`), "
        "dbt Core (`run_dbt.ps1`), Cloud Workflows (`run_workflow.ps1`) und Grafana Cloud. Die alten v1.0-Dateien verbleiben "
        "ausschließlich zur Dokumentation des Migrationspfades im Repository.",
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

    story.append(P("3.1 Die 6 Datenfluss-Schichten im Detail", s['h2']))

    story.append(P("<b>1. Raw Landing & Streaming Ingestion (Kafka KRaft):</b>", s['h3']))
    story.append(P(
        "Der Streaming-Producer (`src/producer.py`) liest das kuratierte Sample `data/sample/us_videos_mini_500.csv` "
        "(326 Events) und simuliert das Echtzeit-Eintreffen von YouTube Trending Daten. "
        "295 valide Datensätze fließen in das Kafka-Topic `topic_ingest`, während 31 synthetisch korrumpierte "
        "Datensätze (~10% Fehlerrate) direkt in das Dead-Letter-Queue-Topic `topic_err` geroutet werden. "
        "Zudem mutiert der Producer für das Ziel-Video `2kyS6SvSYSE` deterministisch Titel und Tags über drei Trending-Tage.",
        s['body']
    ))

    story.append(P("<b>2. Bronze & Quarantäne Persistenz (Micro-Batch Consumers):</b>", s['h3']))
    story.append(P(
        "Der Bronze-Consumer (`src/consumer_bronze.py`) liest `topic_ingest`, reichert jeden Record mit UTC-Audit-Metadaten "
        "(`_ingested_at`, `_kafka_offset`, `_kafka_partition`) an und speichert Snappy-komprimierte Parquet-Dateien unter "
        "`data/bronze/`. Parallel isoliert `src/consumer_dlq.py` alle fehlerhaften Nachrichten aus `topic_err` inklusive "
        "`_quarantine_at` und `_error_reason` unter `data/quarantine/`.",
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
        "**dbt Core** (`run_dbt.ps1`) übernimmt die In-Warehouse-Transformation in BigQuery: Über den Staging-View "
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
        "|       |-- staging/stg_videos.sql        # [v2.0 Active] Typisierung & Trimming View auf silver_videos\n"
        "|       +-- marts/core/                   # [v2.0 Active] Kimball Star-Schema Marts & 15 Tests\n"
        "|           |-- dim_video.sql             # [v2.0 Active] SCD-2 Dimension mit valid_from/to & is_current\n"
        "|           |-- dim_category.sql          # [v2.0 Active] Conformed Kategorie-Dimension\n"
        "|           |-- dim_date.sql              # [v2.0 Active] Kalender-Dimension (is_weekend, day_name)\n"
        "|           |-- fact_video_metrics.sql    # [v2.0 Active] Fakten mit Point-in-Time SCD-2 Join\n"
        "|           +-- schema.yml                # [v2.0 Active] 15 automatisierte dbt Quality Gate Tests\n"
        "|-- infra/                                # [v2.1 Active] Infrastructure as Code (Terraform 1.17)\n"
        "|   |-- versions.tf, variables.tf, main.tf# [v2.1 Active] 5 GCP Ressourcen (GCS, BQ, Pub/Sub, Workflows)\n"
        "|   +-- workflows/pipeline.yaml           # [v2.1 Active] Serverless Cloud Workflow State-Machine\n"
        "|-- docker/                               # Modulare Docker Compose Definitionen\n"
        "|   |-- docker-compose-kafka.yml          # [v2.0 Active] Apache Kafka KRaft & Provectus Kafka-UI\n"
        "|   |-- docker-compose-spark.yml          # [v2.0 Active] Ephemerer PySpark + Iceberg V2 Container\n"
        "|   |-- docker-compose-airflow.yml        # [v1.0 Legacy] Alter Airflow 2.9 & Postgres Stack\n"
        "|   +-- docker-compose-monitoring.yml     # [v1.0 Legacy] Alter lokaler Prometheus/Grafana Stack\n"
        "|-- src/                                  # Python Quellcode\n"
        "|   |-- producer.py                       # [v2.0 Active] Streaming Producer (10% DLQ + SCD-2 Mutation)\n"
        "|   |-- consumer_bronze.py                # [v2.0 Active] Bronze Parquet Consumer (topic_ingest)\n"
        "|   |-- consumer_dlq.py                   # [v2.0 Active] DLQ Quarantaene Consumer (topic_err)\n"
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
    # KAPITEL 4: STREAMING INGESTION & RESILIENZ (KAFKA KRAFT & DLQ)
    # =========================================================================
    story.extend(track(4))
    story.append(P("4. Streaming Ingestion & Resilienz (Kafka KRaft, DLQ & SCD-2 Mutation)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "In produktiven DataOps-Architekturen ist unkontrollierter Datenverlust inakzeptabel. "
        "Gleichzeitig darf ein korrupter Datensatz niemals die gesamte Ingestion-Pipeline blockieren ('Poison Pill Problem'). "
        "Dieses Kapitel erläutert die Implementierung des Streaming-Layers mit Apache Kafka im KRaft-Modus, "
        "die 10%-Fault-Injection-Engine sowie die deterministische SCD-2-Titelmutation.",
        s['body']
    ))

    story.append(P("4.1 Warum Apache Kafka KRaft? (Eliminierung von ZooKeeper)", s['h2']))
    story.append(P(
        "Historisch benötigte Apache Kafka einen separaten Apache ZooKeeper-Cluster zur Partition-Leader-Election "
        "und Metadaten-Verwaltung. Dies führte zu doppeltem Konfigurationsaufwand, Metadaten-Synchronisationslags "
        "und Split-Brain-Zuständen. Mit **Kafka Raft Metadata Mode (KRaft)** (`docker/docker-compose-kafka.yml`) "
        "wurde ZooKeeper vollständig eliminiert: Der Kafka-Broker agiert gleichzeitig als `broker,controller` und "
        "verwaltet den Cluster-State in einem internen, ereignisgesteuerten Raft-Quorum-Log. "
        "Alle Python-Clients verbinden sich explizit über `127.0.0.1:9092` (reines IPv4), um den unter Windows "
        "bekannten 2-Sekunden-IPv6-DNS-Fallback-Lag von `localhost` zu vermeiden.",
        s['body']
    ))

    story.append(P("4.2 Die Resilienz-Architektur: 10% Fault-Injection & Dead Letter Queue", s['h2']))
    story.append(P(
        "Der Producer (`src/producer.py`) liest die 326 Datensätze aus `data/sample/us_videos_mini_500.csv` und "
        "implementiert eine präzise **Fault-Injection- und Quarantäne-Weiche**:",
        s['body']
    ))
    story.append(P("• <b>Stochastische 10% Fehlerrate (`ERROR_RATE = 0.10`):</b> Für alle Videos außer dem SCD-2-Zielvideo wird mit 10% Wahrscheinlichkeit (`random.random() < ERROR_RATE`) das numerische Feld `views` durch den ungültigen String `CORRUPT_INVALID_NUMBER` überschrieben und das Audit-Feld `_error_reason = 'Simulated fault injection: non-numeric views'` ergänzt.", s['bullet']))
    story.append(P("• <b>Sofortiges DLQ-Routing (`topic_err`):</b> Korrupte Events werden nicht in den Hauptstrom eingespeist, sondern sofort an das Dead-Letter-Queue-Topic `topic_err` gesendet (im Referenzlauf: 31 Events).", s['bullet']))
    story.append(P("• <b>Sauberer Hauptstrom (`topic_ingest`):</b> Alle validen Events fließen in `topic_ingest` (im Referenzlauf: 295 Events).", s['bullet']))
    story.append(P("• <b>Entkoppelte Consumer mit Audit-Metadaten:</b> `src/consumer_bronze.py` (Gruppe `bronze_consumer_group`) konsumiert `topic_ingest`, ergänzt `_ingested_at` (UTC ISO-8601), `_kafka_offset` sowie `_kafka_partition` und schreibt Parquet nach `data/bronze/`. Analog isoliert `src/consumer_dlq.py` (Gruppe `dlq_consumer_group`) alle `topic_err`-Nachrichten mit `_quarantine_at` nach `data/quarantine/`. Beide Consumer nutzen `consumer_timeout_ms=5000` für saubere Micro-Batch-Terminierung.", s['bullet']))

    story.append(P("4.3 Deterministische SCD-2 Titel- & Tag-Mutation im Producer", s['h2']))
    story.append(P(
        "Auf YouTube ändern Creator häufig nach der Veröffentlichung den Titel oder die Tags eines Videos (A/B-Testing), "
        "um die Click-Through-Rate (CTR) zu steigern. Um die nachgelagerte SCD-2-Historisierung in BigQuery deterministisch "
        "zu beweisen, überwacht `src/producer.py` das Video mit der ID **`2kyS6SvSYSE`** und mutiert dessen Attribute "
        "über drei aufeinanderfolgende Erscheinungen im Stream:",
        s['body']
    ))
    story.append(P("• <b>Erscheinung 1 (Original aus CSV):</b> Titel: `WE WANT TO TALK ABOUT OUR MARRIAGE`", s['bullet']))
    story.append(P("• <b>Erscheinung 2 (Mutation 1):</b> Titel: `WE WANT TO TALK ABOUT OUR MARRIAGE (Official Update)` | Tags: `marriage|relationship|update|vlog`", s['bullet']))
    story.append(P("• <b>Erscheinung 3 (Mutation 2):</b> Titel: `WE WANT TO TALK ABOUT OUR MARRIAGE [THE TRUTH]` | Tags: `marriage|relationship|update|vlog|truth`", s['bullet']))

    story.append(P("Original-Codeausschnitt aus `src/producer.py`:", s['h3']))
    code_producer = (
        "# src/producer.py (Original-Auszug: SCD-2 Mutation & 10% DLQ Fault-Injection)\n"
        "SCD2_TARGET_VIDEO_ID = \"2kyS6SvSYSE\"\n"
        "SCD2_MUTATIONS = {\n"
        "    2: {\n"
        "        \"title\": \"WE WANT TO TALK ABOUT OUR MARRIAGE (Official Update)\",\n"
        "        \"tags\": \"marriage|relationship|update|vlog\"\n"
        "    },\n"
        "    3: {\n"
        "        \"title\": \"WE WANT TO TALK ABOUT OUR MARRIAGE [THE TRUTH]\",\n"
        "        \"tags\": \"marriage|relationship|update|vlog|truth\"\n"
        "    }\n"
        "}\n\n"
        "# 1. Deterministische SCD-2 Mutation fuer unser Ziel-Video\n"
        "if vid == SCD2_TARGET_VIDEO_ID:\n"
        "    scd2_occurrence_count += 1\n"
        "    if scd2_occurrence_count in SCD2_MUTATIONS:\n"
        "        row.update(SCD2_MUTATIONS[scd2_occurrence_count])\n\n"
        "# 2. Fault Injection (10% korrupte Daten -> Dead Letter Queue)\n"
        "if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE:\n"
        "    corrupted_row = dict(row)\n"
        "    corrupted_row[\"views\"] = \"CORRUPT_INVALID_NUMBER\"\n"
        "    corrupted_row[\"_error_reason\"] = \"Simulated fault injection: non-numeric views\"\n"
        "    producer.send(TOPIC_ERR, key=vid, value=corrupted_row)\n"
        "    err_count += 1\n"
        "else:\n"
        "    producer.send(TOPIC_INGEST, key=vid, value=row)\n"
        "    valid_count += 1"
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
    story.append(P("8. Infrastructure as Code (Terraform 1.17 Cloud Provisioning)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Manuelles Zusammenklicken von Cloud-Ressourcen ('ClickOps') führt unweigerlich zu Konfigurations-Drift "
        "und nicht reproduzierbaren Umgebungen. In Release `v2.1.0` wird die gesamte Google Cloud Infrastruktur "
        "über **Terraform 1.17** (`infra/main.tf`, `infra/variables.tf`, `infra/versions.tf`) deklarativ verwaltet "
        "und über den PowerShell-Wrapper `run_infra.ps1` gesteuert.",
        s['body']
    ))

    story.append(P("8.1 Die 5 bereitgestellten Google Cloud Ressourcen im Detail", s['h2']))

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
            P("Serverloses Cloud-Pub/Sub-Topic für den regulären Event-Ingest-Strom.", s['td'])
        ],
        [
            P("`google_pubsub_topic`<br/>`.youtube_dlq`", s['td_bold']),
            P("`topic-youtube-dlq`", s['td']),
            P("Serverloses Cloud-Pub/Sub-Topic für isolierte Dead-Letter-Queue-Nachrichten.", s['td'])
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
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_tf)
    story.append(Spacer(1, 8))

    story.append(P("8.2 Vollständiger Code von `infra/main.tf`", s['h2']))
    code_tf = (
        "# infra/main.tf (Vollstaendiger Original-Code)\n"
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
        "resource \"google_pubsub_topic\" \"youtube_dlq\" {\n"
        "  name = \"topic-youtube-dlq\"\n"
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
    # KAPITEL 12: ARCHITECTURAL DECISION RECORDS (ADRS) IM DETAIL
    # =========================================================================
    story.extend(track(12))
    story.append(P("12. Architectural Decision Records (ADRs 001 bis 006) im Detail", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Architectural Decision Records (ADRs) dokumentieren fundamentale Architekturentscheidungen "
        "nachvollziehbar mit Kontext, verworfenen Alternativen, Trade-offs und Begründungen.",
        s['body']
    ))

    adrs = [
        (
            "ADR-001: Apache Kafka KRaft vs. ZooKeeper",
            "<b>Entscheidung:</b> Einsatz von Apache Kafka im ZooKeeper-losen KRaft-Modus (`docker-compose-kafka.yml`).<br/>"
            "<b>Kontext:</b> Das 2021er Setup litt unter ZooKeeper-Timeouts und Split-Brain-Problemen auf Windows-Hosts.<br/>"
            "<b>Alternativen:</b> Kafka mit ZooKeeper, RabbitMQ, AWS Kinesis.<br/>"
            "<b>Begründung & Trade-offs:</b> KRaft halbiert die Container-Anzahl, beschleunigt Metadaten-Operationen um den Faktor 10 und eliminiert ZooKeeper als Fehlerquelle."
        ),
        (
            "ADR-002: Apache Iceberg V2 Table Format vs. Pure Parquet",
            "<b>Entscheidung:</b> Nutzung von Apache Iceberg V2 (`local.silver.videos`) für den Silver Lakehouse Layer.<br/>"
            "<b>Kontext:</b> Reine Parquet-Ordner bieten keine ACID-Garantien, keine Snapshot-Isolation und erfordern teure `O(N)` Directory-Listings.<br/>"
            "<b>Alternativen:</b> Delta Lake, Apache Hudi, lose Parquet-Dateien.<br/>"
            "<b>Begründung & Trade-offs:</b> Iceberg V2 trennt physische Parquet-Daten strikt von logischen Metadaten (`v1.metadata.json`, `snap-*.avro`), erlaubt atomare Commits, Time-Travel und volle Engine-Neutralität (Spark, BigQuery BigLake, Trino)."
        ),
        (
            "ADR-003: Ephemerer Docker PySpark vs. Permanenter Spark-Cluster",
            "<b>Entscheidung:</b> Ausführung von PySpark-Jobs in einem ephemeren On-Demand-Container (`de_spark`).<br/>"
            "<b>Kontext:</b> Ein dauerhaft laufender Spark-Cluster (Standalone/Dataproc) verbraucht rund um die Uhr RAM/CPU.<br/>"
            "<b>Alternativen:</b> GCP Dataproc Cluster, Databricks All-Purpose Cluster, lokales PySpark auf Host.<br/>"
            "<b>Begründung & Trade-offs:</b> Ephemerer Compute erzeugt 0 € Leerlaufkosten, kapselt Java/Hadoop/Iceberg-JARs sauber vom Windows-Host ab und nutzt über `broadcast()` einen Zero-Shuffle Join."
        ),
        (
            "ADR-004: Kimball Star-Schema & SCD-2 via dbt Core vs. One Big Table (OBT)",
            "<b>Entscheidung:</b> Modellierung als relationales Kimball Star-Schema mit SCD-2 Snapshot (`dim_video_snapshot`) in BigQuery.<br/>"
            "<b>Kontext:</b> Flache Tabellen (OBT) überschreiben bei Titeländerungen die Historie (SCD-1) und duplizieren Dimensionsattribute.<br/>"
            "<b>Alternativen:</b> Flaches Spark-Gold-Skript (`transform_gold.py` aus v1.0), Data Vault 2.0.<br/>"
            "<b>Begründung & Trade-offs:</b> Das Star-Schema trennt Fakten (`fact_video_metrics`) von Dimensionen (`dim_video`, `dim_category`, `dim_date`), ermöglicht exakte Point-in-Time Joins und wird durch 15 dbt-Tests abgesichert."
        ),
        (
            "ADR-005: Google Cloud Workflows vs. Apache Airflow / Cloud Composer",
            "<b>Entscheidung:</b> Ablösung von Apache Airflow (v1.0) durch serverlose Google Cloud Workflows (v2.1).<br/>"
            "<b>Kontext:</b> Cloud Composer (Managed Airflow auf GCP) kostet mindestens ~300 €/Monat, selbst im Leerlauf.<br/>"
            "<b>Alternativen:</b> Lokaler Airflow Docker-Stack, Cloud Composer, Prefect.<br/>"
            "<b>Begründung & Trade-offs:</b> Cloud Workflows startet in unter 200 ms via REST, orchestriert BigQuery nativ, prüft das Foreign-Key Quality Gate in der Cloud und kostet im Always Free Tier exakt 0,00 €."
        ),
        (
            "ADR-006: Grafana Cloud Direct Monitoring (Weg 1) vs. Lokale Prometheus-Container",
            "<b>Entscheidung:</b> Direkte Anbindung von Grafana Cloud an Google Cloud Monitoring (`pluginId: stackdriver`).<br/>"
            "<b>Kontext:</b> Lokale Prometheus/Grafana-Container (`docker-compose-monitoring.yml`) belegen lokal RAM/Ports und kennen keine nativen GCP-Metriken.<br/>"
            "<b>Alternativen:</b> Lokaler Prometheus mit GCP-Exporter, Google Cloud Console Charts.<br/>"
            "<b>Begründung & Trade-offs:</b> 0 lokale Daemons, direkte Abfrage von `workflows`, `bigquery` und `pubsub` Metriken über den Service Account (`roles/monitoring.viewer`) und versioniertes Dashboard-as-Code."
        )
    ]

    for title, content in adrs:
        story.append(P(f"<b>{title}</b>", s['h2']))
        story.append(P(content, s['body']))
        story.append(Spacer(1, 3))

    story.append(PageBreak())

    # =========================================================================
    # KAPITEL 13: DEPPENSICHERES BETRIEBSHANDBUCH (9 SCHRITTE & PLAYBOOKS)
    # =========================================================================
    story.extend(track(13))
    story.append(P("13. Deppensicheres Betriebshandbuch (9-Schritte-Anleitung & Playbooks)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Dieses Kapitel enthält die vollständige, **deppensichere Schritt-für-Schritt-Anleitung (End-to-End)** "
        "inklusive aller Voraussetzungen, IAM-Rollen, GCP-APIs, PowerShell-Runner und Fehlerbehebungs-Playbooks.",
        s['body']
    ))

    story.append(P("13.1 Checkliste der Voraussetzungen (IAM-Rollen & GCP APIs)", s['h2']))
    story.append(P("• <b>Lokale Systemumgebung:</b> Windows 10/11 mit PowerShell, Docker Desktop (gestartet, WSL2-Backend), Python 3.10+ sowie Terraform 1.17.", s['bullet']))
    story.append(P("• <b>GCP Projekt & Service Account Key:</b> Projekt-ID `cloudanalytics-514018` (Region `europe-west3` / Location `EU`). Der JSON-Key des Service Accounts `cloudanalytics-514018@cloudanalytics-514018.iam.gserviceaccount.com` liegt als `gcp_service_account.json` im Projekt-Root (via `.gitignore` geschützt).", s['bullet']))
    story.append(P("• <b>Die 6 zwingend erforderlichen GCP IAM-Rollen auf dem Service Account:</b><br/>"
                   "  1. `roles/bigquery.admin` (BigQuery Administrator)<br/>"
                   "  2. `roles/storage.admin` (Storage Administrator)<br/>"
                   "  3. `roles/pubsub.admin` (Pub/Sub Administrator)<br/>"
                   "  4. `roles/workflows.admin` (Workflows Administrator)<br/>"
                   "  5. `roles/iam.serviceAccountUser` (Dienstkonto-Nutzer — zwingend für Workflow-Deployment!)<br/>"
                   "  6. `roles/monitoring.viewer` (Monitoring-Betrachter — zwingend für Grafana Cloud!)", s['bullet']))
    story.append(P("• <b>Die 5 zwingend aktivierten Google Cloud APIs:</b><br/>"
                   "  `workflows.googleapis.com`, `monitoring.googleapis.com`, `pubsub.googleapis.com`, `bigquery.googleapis.com`, `storage.googleapis.com`.", s['bullet']))

    story.append(P("13.2 Die 9-Schritte End-to-End Ausführungssequenz (PowerShell)", s['h2']))
    code_9steps = (
        "# SCHRITT 1: Python Virtual Environment aktivieren & Abhaengigkeiten installieren\n"
        "cd D:\\Projekte\\CloudEng\\DE_Capstone_2026\n"
        "python -m venv .venv\n"
        "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n\n"
        "# SCHRITT 2: Cloud-Infrastruktur (5 GCP Ressourcen) per Terraform ausrollen\n"
        ".\\run_infra.ps1 init\n"
        ".\\run_infra.ps1 plan\n"
        ".\\run_infra.ps1 apply     # -> Apply complete! Resources: 5 added, 0 changed, 0 destroyed.\n\n"
        "# SCHRITT 3: Streaming Ingestion (Kafka KRaft, 10% DLQ & SCD-2 Mutation)\n"
        ".\\start_kafka.ps1         # Startet Kafka Broker (:9092) & Kafka-UI (http://localhost:8080)\n"
        ".\\run_producer.ps1        # Sendet 295 Clean Events (topic_ingest) + 31 DLQ Events (topic_err)\n"
        ".\\run_bronze.ps1          # Schreibt 295 Events als Parquet nach data/bronze/\n"
        ".\\run_dlq.ps1             # Isoliert 31 korrupte Events als Parquet nach data/quarantine/\n\n"
        "# SCHRITT 4: Silver Lakehouse Transformation (Ephemerer PySpark & Apache Iceberg V2)\n"
        ".\\run_silver.ps1          # Broadcast-Join + Commit in Iceberg (local.silver.videos) & data/silver/\n\n"
        "# SCHRITT 5: Bereinigte Silver-Daten idempotent nach Google BigQuery laden\n"
        ".\\load_to_bigquery.ps1    # Laedt 295 Zeilen in cloudanalytics-514018.youtube_analytics.silver_videos\n\n"
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
        ".\\stop_kafka.ps1          # Stoppt lokale Kafka-Container\n"
        ".\\run_infra.ps1 destroy   # Loescht alle 5 GCP-Ressourcen rueckstandslos (0,00 EUR Kosten)"
    )
    story.append(make_code_block(code_9steps, s))
    story.append(PageBreak())

    story.append(P("13.3 Vollständige Referenz aller PowerShell-Runner (`.ps1`)", s['h2']))

    runner_table = [
        [P("<b>Runner-Skript</b>", s['th']), P("<b>Parameter</b>", s['th']), P("<b>Release-Status & Funktion</b>", s['th'])],
        [P("`run_infra.ps1`", s['td_bold']), P("`init`, `plan`, `apply`, `destroy`", s['td']), P("<b>[v2.1 Active]</b> Steuert Terraform 1.17 in `infra/` (5 GCP-Ressourcen).", s['td'])],
        [P("`start_kafka.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Startet Kafka Broker (KRaft) & Kafka-UI via Docker Compose.", s['td'])],
        [P("`stop_kafka.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Stoppt Kafka-Container und gibt Ports `9092` & `8080` frei.", s['td'])],
        [P("`run_producer.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Startet `src/producer.py` (295 Clean, 31 DLQ, SCD-2 Mutationen).", s['td'])],
        [P("`run_bronze.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Konsumiert `topic_ingest` -> `data/bronze/*.parquet`.", s['td'])],
        [P("`run_dlq.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Konsumiert `topic_err` -> `data/quarantine/*.parquet`.", s['td'])],
        [P("`run_silver.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Startet Docker PySpark (`transform_silver.py`) & committet Iceberg V2.", s['td'])],
        [P("`load_to_bigquery.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.0 Active]</b> Lädt Silver-Parquet idempotent nach BigQuery (`silver_videos`).", s['td'])],
        [P("`run_dbt.ps1`", s['td_bold']), P("`debug`, `snapshot`, `run`, `test`", s['td']), P("<b>[v2.0 Active]</b> Steuert dbt Core CLI (SCD-2 Snapshots, Star-Schema, 15 Tests).", s['td'])],
        [P("`run_workflow.ps1`", s['td_bold']), P("Keine", s['td']), P("<b>[v2.1 Active]</b> Triggert den Serverless Cloud Workflow via REST und pollt bis `SUCCEEDED`.", s['td'])],
        [P("`run_gold.ps1`", s['td_bold']), P("Keine", s['td']), P("<i>[v1.0 Legacy]</i> Altes Spark-Gold-Skript (in v2.0/v2.1 durch `run_dbt.ps1` abgelöst).", s['td'])],
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
        "• <i>Ursache:</i> Zum Binden eines Service Accounts an einen Cloud Workflow benötigt der ausführende Account neben `roles/workflows.admin` zwingend auch `roles/iam.serviceAccountUser`. Versucht Terraform zudem eigene Service Accounts oder APIs zu aktivieren, scheitert dies ohne `iam.serviceAccountAdmin`.<br/>"
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
    # KAPITEL 14: INTERVIEW MASTERCLASS & TECHNICAL DEFENSE
    # =========================================================================
    story.extend(track(14))
    story.append(P("14. Data Engineering Interview Masterclass & Technical Defense (15 Q&As)", s['h1']))
    story.append(HRFlowable(width="100%", thickness=1, color=s['primary'], spaceAfter=10))

    story.append(P(
        "Dieses Kapitel dient als Vorbereitungsleitfaden für technische Architektur-Reviews und Vorstellungsgespräche "
        "auf Senior- und Lead-Data-Engineer-Niveau. Es liefert präzise Antworten auf 15 tiefgehende Fachfragen.",
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
            "Durch das Dead-Letter-Queue-Muster (DLQ): `src/producer.py` injiziert 10% korrupte Nachrichten (`views = 'CORRUPT_INVALID_NUMBER'`), "
            "leitet diese aber sofort in das Quarantäne-Topic `topic_err` um, während die 295 validen Events über `topic_ingest` "
            "ungestört verarbeitet werden. `src/consumer_dlq.py` persistiert die 31 Fehler-Events samt `_error_reason` unter `data/quarantine/`."
        ),
        (
            "F6: Warum wird das Zielvideo `2kyS6SvSYSE` im Producer von der 10% Fault-Injection ausgenommen?",
            "Um 100% deterministische, reproduzierbare End-to-End-Tests für SCD-2 zu garantieren (`if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE`). "
            "Würde eine der drei Titel-Mutationen zufällig in der DLQ landen, wäre die SCD-2-Versionskette nicht deterministisch testbar."
        ),
        (
            "F7: Warum verbinden sich die Kafka-Skripte mit `127.0.0.1:9092` statt `localhost:9092`?",
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
            "3. dbt Core: Tabellen werden als `CREATE OR REPLACE TABLE` mit deterministischen MD5-Schlüsseln (`metric_key`) gebaut. "
            "4. Cloud Workflow: Aktualisiert `fact_video_metrics` atomar per `CREATE OR REPLACE TABLE`."
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
            "F15: Welche Komponenten aus Release v1.0.0 sind in Release v2.1.0 obsolet und warum?",
            "1. Der lokale Airflow-Stack (`docker-compose-airflow.yml`, `dags/`) wurde zu 100% durch serverlose Google Cloud Workflows ersetzt. "
            "2. Der lokale Prometheus/Grafana-Stack (`docker-compose-monitoring.yml`) wurde durch Grafana Cloud ('Weg 1' direkt auf GCP Monitoring) ersetzt. "
            "3. Das alte Spark-Gold-Skript (`src/transform_gold.py`) wurde durch das dbt Kimball Star-Schema in BigQuery ersetzt."
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
            P("< 5 MB Speicher (295 Zeilen) / < 100 MB Queries pro Monat.", s['td']),
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
            P("< 5 MB für `topic-youtube-ingest` & `topic-youtube-dlq`.", s['td']),
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
    story.append(P("• <b>Terraform Teardown-Garantie (`run_infra.ps1 destroy`):</b> Durch `force_destroy = true` am GCS-Bucket und `delete_contents_on_destroy = true` am BigQuery-Dataset lassen sich sämtliche Cloud-Ressourcen jederzeit mit einem einzigen Befehl rückstandslos entfernen.", s['bullet']))
    story.append(P("• <b>Grafana FinOps-Schwellenwerte:</b> Panel 4 (`BigQuery Bytes Billed`) schlägt bei über 100 MB auf Orange und bei 1 GB auf Rot um, sodass teure Abfragen sofort sichtbar werden.", s['bullet']))
    story.append(P("• <b>Verzicht auf 24/7-Cluster:</b> Weder für Compute (ephemerer Docker-PySpark) noch für Orchestrierung (Serverless Cloud Workflows) oder Monitoring (Grafana Cloud Weg 1) laufen dauerhafte VMs oder Kubernetes-Cluster.", s['bullet']))

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
