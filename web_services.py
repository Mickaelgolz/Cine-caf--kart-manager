"""Web integration: one result store, durable groups, visitor sessions and exports."""
from pathlib import Path
import json, secrets, hashlib, time, logging, threading, urllib.parse
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import database as db
import heat_calculator as calc

TOKENS = {}
LOCK = threading.Lock()
LOG = logging.getLogger('cinecafe')

def migrate(conn):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='web_meta'").fetchone():
        db.backup_database(conn,'antes_web_310')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS web_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS web_groups(event TEXT,category TEXT,group_name TEXT,pilot_id INTEGER REFERENCES pilots(id),UNIQUE(event,category,pilot_id));
    CREATE TABLE IF NOT EXISTS visitors(id INTEGER PRIMARY KEY,name TEXT,accessed_at TEXT);
    ''')
    fields={r['name'] for r in conn.execute('PRAGMA table_info(pilots)')}
    for f in ('cpf','city'):
        if f not in fields: conn.execute(f"ALTER TABLE pilots ADD COLUMN {f} TEXT NOT NULL DEFAULT ''")
    fields={r['name'] for r in conn.execute('PRAGMA table_info(developer_notes)')}
    if 'resolved' not in fields: conn.execute('ALTER TABLE developer_notes ADD COLUMN resolved INTEGER NOT NULL DEFAULT 0')
    fields={r['name'] for r in conn.execute('PRAGMA table_info(heat_calculations)')}
    if 'version' not in fields: conn.execute("ALTER TABLE heat_calculations ADD COLUMN version TEXT NOT NULL DEFAULT ''")
    conn.commit()
    if not conn.execute("SELECT 1 FROM web_meta WHERE key='legacy_import'").fetchone():
        # Preserve native completed sessions as official heat records, only if no web heat already exists.
        for s in conn.execute('SELECT s.*,c.name category,t.name stage_name,t.date FROM sessions s JOIN categories c ON c.id=s.category_id JOIN stages t ON t.id=s.stage_id WHERE s.status=?',('Concluída',)).fetchall():
            event=f"{s['stage_name']} - {s['date']}"
            if conn.execute('SELECT 1 FROM heat_calculations WHERE event_name=? AND category=? AND group_name=? AND session_type=?',(event,s['category'],s['group_name'],s['session_type'])).fetchone(): continue
            rows=[dict(pilot_id=r['pilot_id'],name=r['name'],position=r['position'],status='DSQ' if r['dq'] else 'FINISHED',fast=bool(r['fastest_manual']),penalty=bool(r['penalty']),points=r['points'],best_lap_ms=r['best_lap_ms']) for r in conn.execute('SELECT r.*,p.name FROM results r JOIN pilots p ON p.id=r.pilot_id WHERE session_id=?',(s['id'],))]
            conn.execute('INSERT INTO heat_calculations(title,created_at,session_type,payload,category,group_name,event_name) VALUES(?,?,?,?,?,?,?)',(f"{s['category']} / {s['group_name']} / {s['session_type']}",db.local_now(),s['session_type'],json.dumps(rows),s['category'],s['group_name'],event))
        for e in conn.execute("SELECT e.*,c.name category,t.name stage_name,t.date FROM stage_entries e JOIN categories c ON c.id=e.category_id JOIN stages t ON t.id=e.stage_id WHERE e.group_name IS NOT NULL AND e.status='Confirmado'").fetchall():
            conn.execute('INSERT OR IGNORE INTO web_groups VALUES(?,?,?,?)',(f"{e['stage_name']} - {e['date']}",e['category'],e['group_name'],e['pilot_id']))
        conn.execute("INSERT INTO web_meta VALUES('legacy_import','done')")
        conn.commit()

def save_profile(conn,pid,p):
    if p.status not in ('Ativo','Inativo'): raise ValueError('Situação de piloto inválida.')
    with conn:
        fields=db.PROFILE_FIELDS
        conn.execute('UPDATE pilots SET '+','.join(f+'=?' for f in fields)+' WHERE id=?',tuple(getattr(p,f) for f in fields)+(pid,))
        for cat in p.categories:
            c=conn.execute('SELECT id FROM categories WHERE name=?',(cat,)).fetchone()
            if not c: raise ValueError('Categoria inválida.')
            conn.execute('INSERT OR IGNORE INTO registrations(pilot_id,category_id,initial_points) VALUES(?,?,0)',(pid,c['id']))

def latest_records(conn,event):
    return [dict(r) for r in conn.execute('SELECT * FROM heat_calculations WHERE event_name=? ORDER BY id',(event,))]

def save_heat(conn,p):
    rows=[r.model_dump() for r in p.rows]
    if not p.event_name.strip() or p.group not in 'ABCDEFGHIJ' or len(p.group)!=1: raise ValueError('Informe evento e grupo de A a J.')
    if not conn.execute('SELECT 1 FROM categories WHERE name=?',(p.category,)).fetchone(): raise ValueError('Categoria inválida.')
    for r in rows:
        pilot=conn.execute('SELECT name FROM pilots WHERE id=?',(r['pilot_id'],)).fetchone()
        if not pilot: raise ValueError('Piloto não cadastrado.')
        r['name']=pilot['name']
    calculated=calc.calculate(p.session_type,rows)
    if not p.title.strip(): raise ValueError('Informe a identificação da bateria.')
    if p.record_id:
        db.backup_database(conn,'antes_corrigir_bateria')
    conn.execute('BEGIN IMMEDIATE')
    try:
        existing=conn.execute('SELECT * FROM heat_calculations WHERE id=?',(p.record_id,)).fetchone() if p.record_id else None
        if p.record_id and not existing: raise ValueError('Bateria não encontrada.')
        if existing and (existing['event_name'],existing['category'],existing['group_name'],existing['session_type'])!=(p.event_name,p.category,p.group,p.session_type):raise ValueError('Ao corrigir, mantenha a identificação da bateria original.')
        if existing and (existing['version'] or '')!=(p.expected_version or ''): raise ValueError('Outra pessoa alterou esta bateria. Reabra antes de salvar.')
        duplicate=conn.execute('SELECT id FROM heat_calculations WHERE event_name=? AND category=? AND group_name=? AND session_type=? AND id<>? ORDER BY id DESC LIMIT 1',(p.event_name,p.category,p.group,p.session_type,p.record_id or -1)).fetchone()
        if duplicate and not p.record_id: raise ValueError('Bateria já salva. Abra em Resultados para corrigir.')
        version=secrets.token_hex(12)
        vals=(p.title.strip(),db.local_now(),p.session_type,json.dumps(calculated,ensure_ascii=False),p.category,p.group,p.dnf_rule,p.event_name,version)
        if existing:
            conn.execute('UPDATE heat_calculations SET title=?,created_at=?,session_type=?,payload=?,category=?,group_name=?,dnf_rule=?,event_name=?,version=? WHERE id=?',vals+(p.record_id,)); pid=p.record_id
        else:
            pid=conn.execute('INSERT INTO heat_calculations(title,created_at,session_type,payload,category,group_name,dnf_rule,event_name,version) VALUES(?,?,?,?,?,?,?,?,?)',vals).lastrowid
        conn.commit()
        return {'ok':True,'id':pid,'version':version}
    except Exception:
        conn.rollback();raise

def summary(conn,event,official=False):
    records=latest_records(conn,event)
    if not records: raise ValueError('Nenhuma bateria salva para este evento.')
    s=calc.aggregate(records)
    groups={}
    for r in conn.execute('SELECT * FROM web_groups WHERE event=?',(event,)):
        groups.setdefault((r['category'],r['group_name']),set()).add(r['pilot_id'])
    used={(r['category'],r['group_name'],r['session_type']):r for r in s['used']}
    for (cat,g),ids in groups.items():
        for race in ('SUPER_POLE','RACE1','RACE2'):
            key=(cat,g,race)
            if key not in used: s['missing'].append(f'{cat} / {g} / {race}')
            elif {r['pilot_id'] for r in json.loads(used[key]['payload'])}!=ids:
                s['missing'].append(f'{cat} / {g} / {race}: participantes diferentes do grupo salvo')
    # Even manually assembled historical groups must contain the same pilots in every heat.
    rosters={}
    for key,r in used.items():rosters.setdefault(key[:2],[]).append({p['pilot_id'] for p in json.loads(r['payload'])})
    for key,sets in rosters.items():
        if any(x!=sets[0] for x in sets): s['missing'].append(f'{key[0]} / {key[1]}: pilotos diferentes entre sessões')
    ties={}
    for r in s['rows']:
        pilot=conn.execute('SELECT name FROM pilots WHERE id=?',(r['pilot_id'],)).fetchone()
        if pilot:r['name']=pilot['name']
        ties.setdefault((r['category'],r['total']),[]).append(r)
    for (cat,points),rows in ties.items():
        if len(rows)>1 and (any(not r.get('best_lap_ms') for r in rows) or len({r.get('best_lap_ms') for r in rows})<len(rows)):
            s['missing'].append(f'{cat}: empate em {points:g} pontos; informe melhor volta geral ou decisão da organização')
    s['missing']=sorted(set(s['missing']))
    if official and s['missing']: raise ValueError('Resultado ainda parcial: '+'; '.join(s['missing']))
    s['official']=not bool(s['missing'])
    return s

def championship_rows(conn,category):
    totals={r['id']:dict(pilot_id=r['id'],name=r['name'],total=r['initial_points']) for r in conn.execute('SELECT p.id,p.name,r.initial_points FROM registrations r JOIN pilots p ON p.id=r.pilot_id JOIN categories c ON c.id=r.category_id WHERE c.name=?',(category,))}
    for e in conn.execute('SELECT DISTINCT event_name FROM heat_calculations WHERE event_name IS NOT NULL').fetchall():
        try: s=calc.aggregate(latest_records(conn,e[0]))
        except ValueError:continue
        for r in s['rows']:
            if r['category']!=category:continue
            item=totals.setdefault(r['pilot_id'],dict(pilot_id=r['pilot_id'],name=r['name'],total=0));item['total']+=r['total']
    return sorted(totals.values(),key=lambda r:(-r['total'],r['name']))

class Visitor(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    key: str = ''
class GroupEdit(BaseModel):
    event: str
    category: str
    group: str
    pilot_ids: list[int]
class Resolution(BaseModel):
    resolved: bool
class Location(BaseModel):
    latitude: float=Field(ge=-90,le=90)
    longitude: float=Field(ge=-180,le=180)

WEATHER={'at':0,'value':None}
def current_weather():
    from weather_service import _get_json, FORECAST_URL, WEATHER_CODES
    with db.connect() as conn:
        loc=conn.execute("SELECT value FROM web_meta WHERE key='weather_location'").fetchone()
    if not loc:return {'available':False,'message':'Confirme as coordenadas do kartódromo em Configurações.'}
    if WEATHER['value'] and time.time()-WEATHER['at']<600:return WEATHER['value']
    try:
        params=json.loads(loc[0]);params.update(current='temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_gusts_10m',hourly='precipitation_probability',forecast_days=1,timezone='America/Sao_Paulo')
        data=_get_json(FORECAST_URL+'?'+urllib.parse.urlencode(params),timeout=5)
        c=data['current'];hour=c['time'][:13];h=data['hourly'];idx=next((i for i,t in enumerate(h['time']) if t[:13]==hour),0)
        value=dict(available=True,current=c,rain_probability=h['precipitation_probability'][idx],condition=WEATHER_CODES.get(c['weather_code'],'Condição não identificada'),updated=c['time'])
        WEATHER.update(at=time.time(),value=value);return value
    except Exception:
        LOG.exception('weather');return {'available':False,'message':'Previsão meteorológica indisponível.'}

def install(app):
    import main as m
    log_path=db.data_dir()/'cinecafe.log'
    handler=logging.FileHandler(log_path,encoding='utf-8');LOG.addHandler(handler)
    keypath=db.data_dir()/'CHAVE_ORGANIZADOR.txt'
    if not keypath.exists(): keypath.write_text(secrets.token_urlsafe(24),encoding='utf-8')
    admin_key=keypath.read_text().strip()
    public_reads={'/api/bootstrap','/api/history','/api/weather','/api/summary','/api/final/pdf'}
    @app.middleware('http')
    async def access(request:Request,call_next):
        path=request.url.path
        user=TOKENS.get(request.cookies.get('cinecafe',''))
        if user and user['expires']<time.time():user=None
        request.state.user=user
        if (path.startswith('/api/') or path=='/diagnostico') and path not in ('/api/access','/api/health'):
            if not user:return JSONResponse({'detail':'Informe seu nome para acessar.'},401)
            read= request.method=='GET' and (path in public_reads or path.startswith('/api/history/'))
            if user['role']!='admin' and not read:return JSONResponse({'detail':'Apenas o organizador pode alterar os dados.'},403)
            if request.method not in ('GET','HEAD','OPTIONS'):
                origin=request.headers.get('origin')
                if origin and urllib.parse.urlparse(origin).netloc!=request.headers.get('host'):return JSONResponse({'detail':'Origem não permitida.'},403)
        try:
            response=await call_next(request)
        except Exception:
            LOG.exception('request');return JSONResponse({'detail':'Não foi possível concluir. Os detalhes foram registrados no diagnóstico.'},500)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'"
        if path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        return response
    @app.post('/api/access')
    def login(p:Visitor,request:Request):
        name=p.name.strip()
        if len(name)<2:raise ValueError('Informe seu nome.')
        if p.key and not secrets.compare_digest(p.key,admin_key):raise HTTPException(403,'Chave do organizador incorreta.')
        role='admin' if p.key else 'visitor'
        token=secrets.token_urlsafe(32)
        TOKENS[token]={'name':name,'role':role,'expires':time.time()+43200}
        m.ensure_database()
        with db.connect() as conn:conn.execute('INSERT INTO visitors(name,accessed_at) VALUES(?,?)',(name,db.local_now()))
        response=JSONResponse({'name':name,'role':role})
        secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto')=='https'
        response.set_cookie('cinecafe',token,httponly=True,samesite='strict',secure=secure,max_age=43200)
        return response
    @app.get('/api/access')
    def who(request:Request):
        user=request.state.user
        return {'name':user['name'],'role':user['role']} if user else {'role':None}
    @app.delete('/api/access')
    def logout(request:Request):
        TOKENS.pop(request.cookies.get('cinecafe',''),None)
        res=JSONResponse({'ok':True});res.delete_cookie('cinecafe');return res
    @app.put('/api/pilots/{pid}')
    def edit_pilot(pid:int,p:m.PilotPayload):
        with db.connect() as conn:
            if not conn.execute('SELECT 1 FROM pilots WHERE id=?',(pid,)).fetchone():raise ValueError('Piloto não encontrado.')
            db.update_pilot(conn,pid,p.name,p.status);save_profile(conn,pid,p)
        return {'ok':True}
    @app.post('/api/stages')
    def new_stage(p:m.StagePayload):
        try:datetime.strptime(p.date,'%d/%m/%Y')
        except ValueError:raise ValueError('Data no formato DD/MM/AAAA.')
        if not p.name.strip() or not p.location.strip():raise ValueError('Informe nome e local.')
        with db.connect() as conn:
            db.backup_database(conn,'antes_nova_etapa')
            if conn.execute('SELECT 1 FROM stages WHERE name=? AND date=?',(p.name.strip(),p.date)).fetchone():raise ValueError('Já existe uma etapa com este nome e data.')
            champ=db.championship(conn)
            n=conn.execute('SELECT COALESCE(MAX(number),0)+1 FROM stages WHERE championship_id=?',(champ['id'],)).fetchone()[0]
            conn.execute("INSERT INTO stages(championship_id,number,name,date,location,status) VALUES(?,?,?,?,?,'Programada')",(champ['id'],n,p.name.strip(),p.date,p.location.strip()))
        return {'ok':True}
    @app.get('/api/groups')
    def groups(event:str,category:str):
        with db.connect() as conn:
            return [dict(r) for r in conn.execute('SELECT g.*,p.name,p.status FROM web_groups g JOIN pilots p ON p.id=g.pilot_id WHERE event=? AND category=? ORDER BY g.group_name,p.name',(event,category))]
    @app.put('/api/groups')
    def save_group(p:GroupEdit):
        if p.group not in list('ABCDEFGHIJ'):raise ValueError('Grupo de A a J.')
        if len(p.pilot_ids)!=len(set(p.pilot_ids)):raise ValueError('Piloto duplicado.')
        with db.connect() as conn:
            if not conn.execute('SELECT 1 FROM categories WHERE name=?',(p.category,)).fetchone():raise ValueError('Categoria inválida.')
            if not p.event.strip():raise ValueError('Selecione a etapa.')
            if conn.execute('SELECT 1 FROM heat_calculations WHERE event_name=? AND category=?',(p.event,p.category)).fetchone():raise ValueError('Há resultados nesta categoria. Corrija/exclua as baterias antes de reorganizar grupos.')
            for pid in p.pilot_ids:
                if not conn.execute("SELECT 1 FROM pilots WHERE id=? AND status='Ativo'",(pid,)).fetchone():raise ValueError('Piloto inexistente ou inativo.')
            conn.execute('DELETE FROM web_groups WHERE event=? AND category=? AND group_name=?',(p.event,p.category,p.group))
            for pid in p.pilot_ids:
                conn.execute('INSERT INTO web_groups VALUES(?,?,?,?) ON CONFLICT(event,category,pilot_id) DO UPDATE SET group_name=excluded.group_name',(p.event,p.category,p.group,pid))
        return {'ok':True}
    @app.get('/api/summary')
    def consolidate(event:str,official:bool=False):
        with db.connect() as conn:return summary(conn,event,official)
    @app.get('/api/final/pdf')
    def final(event:str):
        import heat_reports
        with db.connect() as conn:s=summary(conn,event,True)
        path=db.data_dir()/'relatorios'/('final_'+secrets.token_hex(8)+'.pdf')
        heat_reports.final_pdf(path,s)
        return FileResponse(path,filename='resultado_final_etapa.pdf')
    @app.get('/regulamento')
    def rules():return FileResponse(Path(__file__).parent/'docs/regulamento.pdf',media_type='application/pdf')
    @app.post('/api/backup')
    def backup():
        with db.connect() as conn:path=db.backup_database(conn,'manual')
        return FileResponse(path,filename=path.name)
    @app.put('/api/notes/{nid}')
    def resolve(nid:int,p:Resolution):
        with db.connect() as conn:conn.execute('UPDATE developer_notes SET resolved=? WHERE id=?',(p.resolved,nid))
        return {'ok':True}
    @app.get('/api/weather')
    def weather():return current_weather()
    @app.put('/api/weather/location')
    def set_location(p:Location):
        with db.connect() as conn:conn.execute("INSERT INTO web_meta VALUES('weather_location',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(p.model_dump_json(),))
        WEATHER.update(at=0,value=None);return {'ok':True}
    @app.get('/api/visitors')
    def visitors():
        with db.connect() as conn:return [dict(r) for r in conn.execute('SELECT * FROM visitors ORDER BY id DESC LIMIT 100')]
