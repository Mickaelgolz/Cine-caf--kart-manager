"""Heat calculations, with explicit non-finish rules."""
import json
import scoring

def initialize(conn):
    old=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='base_calculations'").fetchone()
    new=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='heat_calculations'").fetchone()
    if old and not new:
        import database as db
        db.backup_database(conn, 'antes_resultados_unificados')
        with conn: conn.execute('ALTER TABLE base_calculations RENAME TO heat_calculations')
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS heat_calculations(
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
            session_type TEXT NOT NULL, payload TEXT NOT NULL)''')
        columns={r[1] for r in conn.execute('PRAGMA table_info(heat_calculations)')}
        for name in ('category','group_name','dnf_rule','event_name'):
            if name not in columns:conn.execute(f'ALTER TABLE heat_calculations ADD COLUMN {name} TEXT')

def calculate(session_type,rows):
    if session_type not in ('SUPER_POLE','RACE1','RACE2'):raise ValueError('Sessão inválida.')
    if not rows:raise ValueError('Inclua os pilotos da bateria.')
    if len({r['pilot_id'] for r in rows})!=len(rows):raise ValueError('Piloto duplicado.')
    result=[];positions=[]
    for row in rows:
        r=dict(row);state=r.get('status','DSQ' if r.get('dq') else 'FINISHED')
        if state not in ('FINISHED','DNF','DNS','DSQ'):raise ValueError('Situação inválida.')
        eligible=state=='FINISHED' or state=='DNF' and r.get('dnf_points',False)
        position=r.get('position')
        if position not in (None,''):
            position=int(position)
            if position<1:raise ValueError('Posição deve ser positiva.')
        else:position=None
        if eligible and position is None:raise ValueError('Informe a posição dos pilotos que pontuam.')
        if position is not None:positions.append(position)
        if state in ('DNS','DSQ') and r.get('fast'):raise ValueError('DNS/DSQ não pode receber melhor volta.')
        r.update(position=position,status=state,dq=state=='DSQ')
        if session_type=='SUPER_POLE' and (r.get('fast') or r.get('penalty') or r.get('penalty_seconds')):raise ValueError('Bônus e punição de corrida não se aplicam à Super Pole.')
        if state in ('DNF','DNS') and not r.get('decision','').strip():raise ValueError('Registre a decisão da direção para DNF/DNS; o regulamento é omisso.')
        if r.get('penalty_seconds') and not r.get('penalty'):raise ValueError('Marque a punição de -3 pontos junto da penalidade em segundos.')
        bonus=int(bool(r.get('fast')) and session_type!='SUPER_POLE')
        r['points']=scoring._base_points(session_type,position)+bonus-(3 if r.get('penalty') else 0) if eligible else 0
        result.append(r)
    if len(set(positions))!=len(positions):raise ValueError('Use posições sem repetição; deixe em branco para não classificados.')
    if sum(bool(r.get('fast')) for r in rows)>1:raise ValueError('Marque apenas uma melhor volta.')
    return sorted(result,key=lambda r:(r['position'] is None,r['position'] or 0))

def save(conn,title,session_type,rows,category=None,group=None,dnf_rule=None,event_name=None):
    import database as db
    if not title.strip():raise ValueError('Dê um nome à bateria.')
    result=calculate(session_type,rows)
    with conn:
        return conn.execute('INSERT INTO heat_calculations(title,created_at,session_type,payload,category,group_name,dnf_rule,event_name) VALUES(?,?,?,?,?,?,?,?)',
            (title.strip(),db.local_now(),session_type,json.dumps(result,ensure_ascii=False),category,group,dnf_rule,event_name)).lastrowid


def aggregate(records):
    """One event, latest revision per heat; never sum duplicate heats or pilots."""
    if not records:raise ValueError('Selecione as baterias para consolidar.')
    events={r.get('event_name') for r in records}
    if None in events or '' in events:raise ValueError('Há resultados antigos sem evento. Use DEFINIR EVENTO antes de consolidar.')
    if len(events)!=1:raise ValueError('Selecione somente um evento para consolidar.')
    latest={};ignored=[]
    for r in sorted(records,key=lambda r:r['id']):
        if not r.get('category') or not r.get('group_name'):raise ValueError('Abra o resultado antigo, defina categoria e grupo e salve novamente.')
        key=(r['category'],r['group_name'],r['session_type'])
        if key in latest:ignored.append(latest[key]['id'])
        latest[key]=r
    totals={};seen=set();groups={(k[0],k[1]) for k in latest};missing=[]
    for cat,group in sorted(groups):
        for race in ('SUPER_POLE','RACE1','RACE2'):
            if (cat,group,race) not in latest:missing.append(f'{cat} / {group} / {race}')
    for (cat,group,race),record in latest.items():
        for r in json.loads(record['payload']):
            unique=(cat,race,r['pilot_id'])
            if unique in seen:raise ValueError(f"{r['name']} aparece em mais de um grupo na mesma sessão. Corrija a seleção.")
            seen.add(unique);key=(cat,r['pilot_id'])
            if key not in totals:totals[key]=dict(category=cat,pilot_id=r['pilot_id'],name=r['name'],SUPER_POLE=0,RACE1=0,RACE2=0,total=0)
            lap=r.get('best_lap_ms') if r.get('status') not in ('DNS','DSQ') else None
            if lap:totals[key]['best_lap_ms']=min(totals[key].get('best_lap_ms',lap),lap)
            points=r['points'];totals[key][race]+=points;totals[key]['total']+=points
    result=sorted(totals.values(),key=lambda r:(r['category'],-r['total'],r.get('best_lap_ms') or float('inf'),r['name'].casefold()))
    rank=0;prev_cat=None;prev_points=None
    for r in result:
        if r['category']!=prev_cat:rank=0;prev_points=None;index=0
        index+=1
        if (r['total'],r.get('best_lap_ms'))!=prev_points:rank=index
        r['rank']=rank;prev_cat=r['category'];prev_points=(r['total'],r.get('best_lap_ms'))
    return dict(event=next(iter(events)),rows=result,used=list(latest.values()),ignored=ignored,missing=missing)
