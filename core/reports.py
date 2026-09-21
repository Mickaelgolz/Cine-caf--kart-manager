from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import database as db
import json
from io import BytesIO
from xml.sax.saxutils import escape
from datetime import datetime
from weather_visual import weather_image, font
# Use ReportLab built-in fonts for maximum compatibility on Linux/Railway.
# Helvetica supports the Portuguese text used by the application and avoids
# startup failures caused by invalid or unavailable external TTF files.
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

YELLOW = colors.HexColor("#F2C500")
BLACK = colors.HexColor("#0B0B0D")

SESSION_LABEL = {"SUPER_POLE": "Super Pole", "RACE1": "Corrida 1", "RACE2": "Corrida 2"}


def _styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle("cc_title", parent=s["Title"], fontName=FONT_BOLD, fontSize=19, leading=22, textColor=BLACK, alignment=TA_CENTER)
    h2 = ParagraphStyle("cc_h2", parent=s["Heading2"], fontName=FONT_BOLD, fontSize=12, textColor=BLACK, spaceBefore=7, spaceAfter=5, keepWithNext=True)
    small = ParagraphStyle("cc_small", parent=s["BodyText"], fontName=FONT_REGULAR, fontSize=8, leading=10)
    return title, h2, small


def _logo(story):
    logo = db.resource_path("assets/logo_cine_cafe.png")
    if logo.exists():
        im = Image(str(logo), width=32*mm, height=32*mm)
        im.hAlign = "CENTER"
        story.extend([im, Spacer(1, 2*mm)])


def _table(data, widths=None, font=8):
    body_style=ParagraphStyle('table_body',fontName=FONT_REGULAR,fontSize=font,leading=font+2)
    head_style=ParagraphStyle('table_head',parent=body_style,fontName=FONT_BOLD)
    data=[[Paragraph(escape(str(v)),head_style if i==0 else body_style) for v in row] for i,row in enumerate(data)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), YELLOW),
        ("TEXTCOLOR", (0,0), (-1,0), BLACK),
        ("FONTNAME", (0,0), (-1,0), FONT_BOLD),
        ("FONTNAME", (0,1), (-1,-1), FONT_REGULAR),
        ("FONTSIZE", (0,0), (-1,-1), font),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#888888")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    return t


def classification_report(conn, output: str, stage_id=None) -> str:
    title, h2, small = _styles()
    champ = db.championship(conn)
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=12*mm)
    story = []
    _logo(story)
    story.append(Paragraph("CLASSIFICAÇÃO ATUAL DO CAMPEONATO", title))
    story.append(Paragraph(f"{champ['name']} - {champ['year']}", ParagraphStyle("sub", parent=small, alignment=TA_CENTER, fontSize=10)))
    story.append(Spacer(1, 4*mm))
    if stage_id is not None:
        _stage_weather(story, db.stage_row(conn, stage_id))
    for cat in db.categories(conn):
        story.append(Paragraph(cat["name"], h2))
        data = [["Pos.", "Piloto", "Anterior", "Etapas finalizadas", "Total"]]
        for i, r in enumerate(db.classification(conn, cat["id"]), 1):
            data.append([i, r["name"], f"{r['initial_points']:.0f}", f"{r['stage_points']:.0f}", f"{r['total']:.0f}"])
        story.append(_table(data, [14*mm, 72*mm, 25*mm, 35*mm, 20*mm], 8))
        story.append(Spacer(1, 7*mm))
    doc.build(story)
    return output


def partial_stage_report(conn, stage_id: int, output: str, official=False) -> str:
    stage = db.stage_row(conn, stage_id)
    title, h2, small = _styles()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=10*mm, bottomMargin=12*mm)
    story = []
    _logo(story)
    story.append(Paragraph("RELATÓRIO OFICIAL DA ETAPA" if official else "ACOMPANHAMENTO DA ETAPA", title))
    story.append(Paragraph(f"{stage['name']} - {stage['date']} - {stage['location']}", ParagraphStyle("sub2", parent=small, alignment=TA_CENTER, fontSize=10)))
    story.append(Spacer(1, 4*mm))
    _stage_weather(story, stage)
    sessions = db.stage_sessions(conn, stage_id)
    if not sessions:
        story.append(Paragraph("Nenhuma bateria foi iniciada até o momento.", small))
    for sess in sessions:
        story.append(Paragraph(f"{sess['category_name']} - Grupo {sess['group_name']} - {SESSION_LABEL[sess['session_type']]} - {sess['status']}", h2))
        rows = db.session_grid_rows(conn, sess["id"])
        data = [["Pos.", "Piloto", "Melhor volta", "Punição", "DSQ", "Pts"]]
        ordered = sorted(rows, key=lambda r: (r["position"] is None, r["position"] or 9999, r["name"]))
        for r in ordered:
            data.append([
                r["position"] if r["position"] is not None else "-", r["name"],
                "SIM" if r["fastest_manual"] else "", "-3" if r["penalty"] else "",
                "SIM" if r["dq"] else "", f"{r['points']:.0f}",
            ])
        story.append(_table(data, [12*mm, 65*mm, 25*mm, 18*mm, 14*mm, 14*mm], 7.5))
        story.append(Spacer(1, 4*mm))
    doc.build(story)
    return output



def reset_snapshot_report(conn, stage_id: int, output: str) -> str:
    stage = db.stage_row(conn, stage_id)
    title, h2, small = _styles()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=10*mm, bottomMargin=12*mm)
    story = []
    _logo(story)
    story.append(Paragraph("REGISTRO DA ETAPA ANTES DO RESET", title))
    info = [
        ["Etapa", stage["name"]],
        ["Data", stage["date"] or "-"],
        ["Local", stage["location"] or "-"],
        ["Status", stage["status"]],
        ["Responsável", stage["responsible"] or "-"],
        ["Início", stage["started_at"] or "-"],
        ["Encerramento", stage["ended_at"] or "-"],
        ["Previsão de chuva", stage["rain_forecast"] or "-"],
    ]
    story.append(_table([["Informação", "Valor"]] + info, [45*mm, 120*mm], 8))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("PILOTOS E GRUPOS DA ETAPA", h2))
    groups = db.stage_group_listing(conn, stage_id)
    data = [["Categoria", "Grupo", "Piloto", "Status"]]
    for r in groups:
        data.append([r["category_name"], r["group_name"], r["name"], r["status"]])
    story.append(_table(data, [28*mm, 22*mm, 82*mm, 30*mm], 7.5))
    story.append(Spacer(1, 5*mm))

    _stage_weather(story, stage)
    sessions = db.stage_sessions(conn, stage_id)
    story.append(Paragraph("BATERIAS E RESULTADOS ATÉ O RESET", h2))
    if not sessions:
        story.append(Paragraph("Nenhuma bateria havia sido iniciada.", small))
    for sess in sessions:
        story.append(Paragraph(f"{sess['category_name']} - Grupo {sess['group_name']} - {SESSION_LABEL[sess['session_type']]} - {sess['status']}", h2))
        rows = db.session_grid_rows(conn, sess["id"])
        data = [["Pos.", "Piloto", "Melhor volta", "Punição", "DSQ", "Pts"]]
        ordered = sorted(rows, key=lambda r: (r["position"] is None, r["position"] or 9999, r["name"]))
        for r in ordered:
            data.append([
                r["position"] if r["position"] is not None else "-", r["name"],
                "SIM" if r["fastest_manual"] else "", "-3" if r["penalty"] else "",
                "SIM" if r["dq"] else "", f"{r['points']:.0f}",
            ])
        story.append(_table(data, [12*mm, 65*mm, 25*mm, 18*mm, 14*mm, 14*mm], 7.5))
        story.append(Spacer(1, 3*mm))

    story.append(PageBreak())
    story.append(Paragraph("CLASSIFICAÇÃO NO MOMENTO DO RESET", title))
    story.append(Spacer(1, 3*mm))
    for cat in db.categories(conn):
        story.append(Paragraph(cat["name"], h2))
        data = [["Pos.", "Piloto", "Anterior", "Etapas finalizadas", "Total"]]
        for i, r in enumerate(db.classification(conn, cat["id"]), 1):
            data.append([i, r["name"], f"{r['initial_points']:.0f}", f"{r['stage_points']:.0f}", f"{r['total']:.0f}"])
        story.append(_table(data, [14*mm, 72*mm, 25*mm, 35*mm, 20*mm], 8))
        story.append(Spacer(1, 6*mm))

    doc.build(story)
    return output

def developer_notes_report(conn, stage_id: int, output: str) -> str:
    stage = db.stage_row(conn, stage_id)
    title, h2, small = _styles()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=12*mm)
    story = []
    _logo(story)
    story.append(Paragraph("OBSERVAÇÕES PARA O DESENVOLVEDOR", title))
    story.append(Paragraph(f"{stage['name']} - {stage['date']} - {stage['location']}", ParagraphStyle("devsub", parent=small, alignment=TA_CENTER, fontSize=10)))
    story.append(Spacer(1, 5*mm))
    _stage_weather(story, stage)
    notes = db.developer_notes(conn, stage_id)
    if not notes:
        story.append(Paragraph("Nenhuma observação foi registrada.", small))
    else:
        for i, row in enumerate(reversed(notes), 1):
            story.append(Paragraph(f"{i}. {row['created_at']}", h2))
            if row['updated_at']:
                story.append(Paragraph(f"Editada em: {row['updated_at']}", small))
            safe = (row['note'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
            story.append(Paragraph(safe, small))
            if row['image_path']:
                path=db.data_dir()/row['image_path']
                if path.is_file():
                    from PIL import Image as PILImage
                    with PILImage.open(path) as source:
                        width,height=source.size
                    max_w,max_h=175*mm,115*mm
                    scale=min(max_w/width,max_h/height)
                    story.append(Spacer(1,2*mm))
                    story.append(Image(str(path),width=width*scale,height=height*scale))
            story.append(Spacer(1, 4*mm))
    doc.build(story)
    return output


def official_stage_report(conn, stage_id: int, output: str) -> str:
    stage = db.stage_row(conn, stage_id)
    if stage["status"] != "Finalizada":
        raise ValueError("A etapa precisa estar finalizada antes de gerar o relatório oficial.")
    partial_stage_report(conn, stage_id, output, official=True)
    return output


def groups_formation_report(conn, stage_id: int, output: str, include_absent=False) -> str:
    """PDF operacional com a formação dos grupos da etapa."""
    stage = db.stage_row(conn, stage_id)
    title, h2, small = _styles()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=12*mm,
        leftMargin=12*mm,
        topMargin=10*mm,
        bottomMargin=12*mm,
    )
    story = []
    _logo(story)
    story.append(Paragraph("FORMAÇÃO DAS BATERIAS", title))
    story.append(Paragraph(
        f"{stage['name']} - {stage['date'] or '-'} - {stage['location'] or '-'}",
        ParagraphStyle("groupsub", parent=small, alignment=TA_CENTER, fontSize=10),
    ))
    story.append(Spacer(1, 4*mm))

    _stage_weather(story, stage)
    _schedule_section(story, conn, stage_id)
    for cat in db.categories(conn):
        summary = db.organization_summary(conn, stage_id, cat["id"])
        story.append(Paragraph(cat["name"], h2))
        overview = [["Inscritos", "Participando", "Não participam", "Pendentes"]]
        overview.append([summary["registered"],summary["participating"],summary["absent"],summary["pending"]])
        story.append(_table(overview,[40*mm,40*mm,45*mm,40*mm],8))
        story.append(Spacer(1, 3*mm))

        for group in db.GROUP_NAMES:
            pilots = db.group_pilots(conn, stage_id, cat["id"], group)
            if not pilots:
                continue
            story.append(Paragraph(f"Grupo {group} - {len(pilots)} piloto(s)", h2))
            data = [["#", "Piloto"]]
            if pilots:
                for i, p in enumerate(pilots, 1):
                    data.append([i, p["name"]])
            else:
                data.append(["-", "Nenhum piloto definido"])
            story.append(_table(data, [15*mm, 150*mm], 8))
            story.append(Spacer(1, 2.5*mm))

        absent = db.organization_absent_pilots(conn, stage_id, cat["id"])
        if absent and include_absent:
            story.append(Paragraph("Não participam desta etapa", h2))
            data = [["#", "Piloto"]] + [[i, p["name"]] for i, p in enumerate(absent, 1)]
            story.append(_table(data, [15*mm, 150*mm], 8))
            story.append(Spacer(1, 2.5*mm))

        pending = db.organization_available_pilots(conn, stage_id, cat["id"])
        if pending:
            story.append(Paragraph("Disponíveis no rascunho (não incluídos na formação)", h2))
            data = [["#", "Piloto"]] + [[i, p["name"]] for i, p in enumerate(pending, 1)]
            story.append(_table(data, [15*mm, 150*mm], 8))
        story.append(Spacer(1, 6*mm))

    doc.build(story)
    return output


def _stage_weather(story, stage):
    _,h2,small=_styles()
    story.append(Paragraph("PREVISÃO REGISTRADA NO INÍCIO DA ETAPA",h2))
    story.append(Paragraph(f"Emissão do relatório: {db.local_now()} (UTC-3) | Revisão da organização: {stage['organization_revision']}",small))
    if not stage['weather_forecast']:
        status='A etapa ainda não foi iniciada; previsão não consultada.' if stage['status']=='Programada' else stage['weather_status']
        if stage['weather_fetched_at']:
            status+=f" | Tentativa em {stage['weather_fetched_at']} (UTC-3)"
        story.append(Paragraph(escape(status),small));story.append(Spacer(1,4*mm));return
    forecast=json.loads(stage['weather_forecast'])
    story.append(Paragraph(escape(f"Verificada em: {forecast['fetched_at']} (UTC-3)"),small))
    story.append(Paragraph("Previsão fixa da etapa; não é atualizada ao emitir este relatório. Válida para as horas indicadas abaixo.",small))
    stream=BytesIO();weather_image(forecast).save(stream,format='PNG');stream.seek(0)
    picture=Image(stream,width=170*mm,height=25.5*mm)
    story.extend([Spacer(1,3*mm),picture,Spacer(1,4*mm)])


def _schedule_section(story,conn,stage_id):
    _,h2,small=_styles()
    story.append(Paragraph('PROGRAMAÇÃO DAS SESSÕES',h2))
    rows=db.scheduled_sessions(conn,stage_id)
    if not rows:
        story.append(Paragraph('Programação ainda não definida. Salve os grupos e organize os horários.',small));return
    data=[['#','Categoria','Grupo','Sessão','Início','Próxima em']]
    for i,r in enumerate(rows,1):
        when=datetime.fromisoformat(r['planned_start']).strftime('%d/%m %H:%M') if r['planned_start'] else 'A definir'
        data.append([i,r['category_name'],r['group_name'],('Corrida 1 + Super Pole' if r['session_type']=='RACE1' else SESSION_LABEL[r['session_type']]),when,f"{r['duration']+r['gap']} min"])
    story.append(_table(data,[9*mm,25*mm,16*mm,45*mm,42*mm,30*mm],8))
    story.append(Spacer(1,4*mm))


def _lap_text(value):
    """Format a lap time stored in milliseconds, matching the web UI."""
    if value is None:
        return ""
    try:
        return f"{int(value) / 1000:.3f} s"
    except (TypeError, ValueError):
        return ""


def combined_report(conn,stage_id,output,sections,active_only=True,include_weather=True):
    stage=db.stage_row(conn,stage_id);title,h2,small=_styles()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=12*mm,bottomMargin=14*mm)
    story=[];_logo(story)
    story.append(Paragraph('CINECAFÉ • RELATÓRIO DA ETAPA',title))
    story.append(Paragraph(escape(f"{stage['name']} • {stage['date']} • {stage['location']}"),small))
    if include_weather:_stage_weather(story,stage)
    if sections.get('summary'):
        story.append(Paragraph('RESUMO DA ETAPA',h2))
        sessions=db.stage_sessions(conn,stage_id)
        summary=[['Informação','Valor'],['Situação',stage['status']],['Responsável',stage['responsible'] or '—'],['Início',stage['started_at'] or '—'],['Encerramento',stage['ended_at'] or '—'],['Sessões iniciadas / concluídas',f"{len(sessions)} / {sum(r['status']=='Concluída' for r in sessions)}"],['Emissão do relatório',db.local_now()]]
        story.append(_table(summary,[65*mm,105*mm],9))
    if sections.get('pilots'):
        story.append(Paragraph('LISTA DE PILOTOS'+(' ATIVOS' if active_only else ''),h2))
        data=[['Nome','Nº','Categorias','Situação']]
        for pilot in conn.execute("SELECT * FROM pilots WHERE (?=0 OR status='Ativo') ORDER BY name COLLATE NOCASE",(int(active_only),)):
            cats=[m['category']['name'] for m in db.pilot_registration_membership(conn,pilot['id']).values() if m['enabled']]
            data.append([pilot['name'],pilot['number'],', '.join(cats),pilot['status']])
        story.append(_table(data,[85*mm,15*mm,43*mm,27*mm],8))
    if sections.get('groups'):
        _schedule_section(story,conn,stage_id)
        for cat in db.categories(conn):
            for group in db.GROUP_NAMES:
                pilots=db.group_pilots(conn,stage_id,cat['id'],group)
                scheduled=conn.execute('SELECT 1 FROM schedule WHERE stage_id=? AND category_id=? AND group_name=?',(stage_id,cat['id'],group)).fetchone()
                if not pilots and not scheduled:continue
                story.append(Paragraph(escape(f"{cat['name']} • Grupo {group} • {len(pilots)} pilotos"),h2))
                story.append(_table([['#','Piloto']]+([[i,p['name']] for i,p in enumerate(pilots,1)] if pilots else [['—','Grupo planejado, ainda sem pilotos']]),[15*mm,155*mm],8))
    if sections.get('results'):
        sessions=db.stage_sessions(conn,stage_id)
        if not sessions:story.append(Paragraph('Nenhuma sessão iniciada.',small))
        for session in sessions:
            story.append(Paragraph(escape(f"{session['category_name']} • Grupo {session['group_name']} • {SESSION_LABEL[session['session_type']]} • {session['status']}"),h2))
            data=[['Piloto','Pos.','Melhor tempo','MV','Punição','DSQ','Pts']]
            for r in sorted(db.session_grid_rows(conn,session['id']),key=lambda r:(r['position'] is None,r['position'] or 999,r['name'])):
                data.append([r['name'],r['position'] or '—',_lap_text(r['best_lap_ms']) or '—','Sim' if r['fastest_manual'] else '', '-3' if r['penalty'] else '', 'Sim' if r['dq'] else '',f"{r['points']:.0f}"])
            story.append(_table(data,[66*mm,13*mm,33*mm,13*mm,18*mm,13*mm,14*mm],8))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont(FONT_REGULAR,8);canvas.drawRightString(195*mm,8*mm,f'Página {doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output
