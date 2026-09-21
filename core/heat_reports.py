"""Printable race results; rendering has no file-opening side effects."""
import json
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import database as db
RACES={'SUPER_POLE':'Super Pole','RACE1':'Corrida 1','RACE2':'Corrida 2'}
STATES={'FINISHED':'Concluiu','DNF':'DNF','DNS':'DNS','DSQ':'DSQ'}
from reports import FONT_REGULAR,FONT_BOLD
styles=getSampleStyleSheet()
for name in ('BodyText','Normal'):
    styles[name].fontName=FONT_REGULAR;styles[name].fontSize=9;styles[name].leading=13
for name in ('Title','Heading2'):
    styles[name].fontName=FONT_BOLD;styles[name].keepWithNext=True
def para(text,style='BodyText'):
    if isinstance(text,(int,float)):text=f'{text:g}'
    return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
def table(data,widths):
    content=[[para(v) for v in row] for row in data]
    t=Table(content,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#FFC800')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F7F7F7'),colors.HexColor('#ECECEC')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#D4B000')),('LEFTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));return t

def build(path,story):
    def footer(c,doc):
        c.saveState();c.setFont(FONT_REGULAR,8);c.drawString(16*mm,10*mm,'CineCafe Kart Manager');c.drawRightString(194*mm,10*mm,str(doc.page));c.restoreState()
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=16*mm,rightMargin=16*mm,topMargin=15*mm,bottomMargin=18*mm).build(story,onFirstPage=footer,onLaterPages=footer)
    return str(path)

def heat_story(record):
    rows=json.loads(record['payload']) if isinstance(record['payload'],str) else record['payload']
    story=[para('RESULTADOS DA BATERIA','Title'),para(record['title'],'Heading2'),para(f"Evento: {record.get('event_name') or 'Não informado'}"),para(f"{record.get('category') or 'Categoria não informada'} | Grupo {record.get('group_name') or '-'} | {RACES[record['session_type']]}"),para(f"Emissão: {db.local_now()} | DNF: {record.get('dnf_rule') or 'conforme registro'}"),Spacer(1,5*mm)]
    data=[['Pos.','Piloto','Situação','MV','Punição','Pontos']]
    for r in rows:data.append([r.get('position') or '-',r['name'],STATES.get(r.get('status'),'DSQ' if r.get('dq') else 'Concluiu'),'Sim' if r.get('fast') else '-', '-3' if r.get('penalty') else '-',r['points']])
    story.append(table(data,[13,75,26,15,23,26]));return story

def heats_pdf(path,records):
    if not records:raise ValueError('Selecione ao menos uma bateria.')
    story=[]
    for i,r in enumerate(records):
        if i:story.append(PageBreak())
        story+=heat_story(r)
    return build(path,story)

def final_pdf(path,summary):
    title='RESULTADOS PARCIAIS' if summary['missing'] else 'RESULTADOS FINAIS'
    story=[para(title,'Title'),para(summary['event'],'Heading2'),para(f'Emissão: {db.local_now()}'),para('Pontuação por piloto e categoria. Desempate pela melhor volta geral registrada.'),Spacer(1,4*mm)]
    if summary['ignored']:story.append(para(f"Revisões anteriores excluídas da soma: {', '.join(map(str,summary['ignored']))}. Usada a gravação mais recente de cada bateria."))
    if summary['missing']:story.append(para('Sessões ainda ausentes: '+ '; '.join(summary['missing'])))
    categories=sorted({r['category'] for r in summary['rows']})
    for cat in categories:
        story+=[para(cat,'Heading2')];data=[['Pos.','Piloto','Super Pole','Corrida 1','Corrida 2','Total']]
        for r in summary['rows']:
            if r['category']==cat:data.append([r['rank'],r['name'],r['SUPER_POLE'],r['RACE1'],r['RACE2'],r['total']])
        story.append(table(data,[12,70,25,24,24,23]));story.append(Spacer(1,4*mm))
    story.append(PageBreak());story.append(para('BATERIAS INCLUÍDAS','Title'))
    story.append(table([['ID','Categoria','Grupo','Sessão','Registro']]+[[r['id'],r['category'],r['group_name'],RACES[r['session_type']],r['created_at']] for r in summary['used']],[12,27,15,35,89]))
    return build(path,story)
