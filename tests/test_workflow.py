import os,sys,tempfile,json,sqlite3
from pathlib import Path
os.environ['CINECAFE_DATA_DIR']=tempfile.mkdtemp(prefix='cinecafe-tests-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import main as m
import web_services as w
import pytest

@pytest.fixture(scope='module')
def client():
 with TestClient(m.app) as c:
  assert c.post('/api/access',json={'name':'Organizador Teste','key':(m.db.data_dir()/'CHAVE_ORGANIZADOR.txt').read_text().strip()}).status_code==200
  yield c

def row(i=1,position=1,**kw):return dict(pilot_id=i,name='Piloto '+str(i),position=position,status='FINISHED',**kw)

def test_points_table():
 for race,points in [('SUPER_POLE',[11,10,9,8,7,6,5,4,3,2,1]),('RACE1',[18,15,13,11,9,7,5,4,3,2,1]),('RACE2',[18,15,13,11,9,7,5,4,3,2,1])]:
  assert [r['points'] for r in m.calc.calculate(race,[row(i,i) for i in range(1,12)])]==points

def test_bonus_penalty():
 assert m.calc.calculate('RACE1',[row(fast=True,penalty=True)])[0]['points']==16
 with pytest.raises(ValueError):m.calc.calculate('SUPER_POLE',[row(fast=True)])
 with pytest.raises(ValueError):m.calc.calculate('RACE1',[row(penalty_seconds=5)])

@pytest.mark.parametrize('status',['DNF','DNS','DSQ'])
def test_nonfinish(status):
 r=row();r.update(status=status,position=None,decision='Direção confirmou zero pontos')
 assert m.calc.calculate('RACE1',[r])[0]['points']==0

def test_dnf_explicit():
 r=row();r.update(status='DNF',dnf_points=True,decision='Direção confirmou a posição')
 assert m.calc.calculate('RACE1',[r])[0]['points']==18
 r['decision']=''
 with pytest.raises(ValueError):m.calc.calculate('RACE1',[r])

@pytest.mark.parametrize('rows',[[row(),row()],[row(1),row(2)],[row(1,1,fast=True),row(2,2,fast=True)]])
def test_duplicate(rows):
 with pytest.raises(ValueError):m.calc.calculate('RACE1',rows)

def test_dsq_fast():
 r=row(fast=True);r['status']='DSQ'
 with pytest.raises(ValueError):m.calc.calculate('RACE1',[r])

def test_access_permissions(client):
 with TestClient(m.app) as v:
  assert v.get('/api/bootstrap').status_code==401
  assert v.post('/api/access',json={'name':'Convidado','key':'errada'}).status_code==403
  assert v.post('/api/access',json={'name':'Convidado'}).status_code==200
  assert v.get('/api/bootstrap').status_code==200
  assert v.post('/api/save',json={}).status_code==403
  assert v.get('/api/pilots').status_code==403
  assert v.post('/api/backup').status_code==403
  assert v.get('/static/tracado.mp4',headers={'Range':'bytes=0-99'}).status_code==206
  assert v.get('/regulamento').content.startswith(b'%PDF')

def test_full_flow(client):
 c=client
 boot=c.get('/api/bootstrap').json();event=boot['events'][0]
 pilot={'name':'Piloto Teste Novo','status':'Ativo','number':'99','cpf':'123','whatsapp':'48999','city':'São José','categories':['90 KG']}
 r=c.post('/api/pilots',json=pilot);assert r.status_code==200,r.text
 pid=r.json()['id'];pilot['name']='Piloto Corrigido'
 assert c.put(f'/api/pilots/{pid}',json=pilot).status_code==200
 pilot['status']='Inativo';assert c.put(f'/api/pilots/{pid}',json=pilot).status_code==200
 assert pid not in [r['id'] for r in c.get('/api/pilots').json()]
 assert pid in [r['id'] for r in c.get('/api/pilots?include_inactive=true').json()]
 pilot['status']='Ativo';c.put(f'/api/pilots/{pid}',json=pilot)
 g={'event':event,'category':'90 KG','group':'J','pilot_ids':[pid]}
 assert c.put('/api/groups',json=g).status_code==200
 assert c.get('/api/groups',params={'event':event,'category':'90 KG'}).status_code==200
 saved=[]
 for race in ['SUPER_POLE','RACE1','RACE2']:
  p={'title':'Teste '+race,'category':'90 KG','group':'J','session_type':race,'event_name':event,'rows':[row(pid,1,best_lap_ms=58432)]}
  assert c.post('/api/calculate',json=p).status_code==200
  r=c.post('/api/save',json=p);assert r.status_code==200,r.text
  saved.append(r.json()['id'])
  assert c.post('/api/save',json=p).status_code==400
  h=c.get('/api/history/'+str(saved[-1])).json();assert h['payload'][0]['points']>0
  p.update(record_id=h['id'],expected_version=h['version'])
  assert c.post('/api/save',json=p).status_code==200
  assert c.post('/api/save',json=p).status_code==400  # stale revision
  pdf=c.post('/api/export/pdf',json=p);assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
  if race=='SUPER_POLE':assert c.get('/api/summary',params={'event':event,'official':True}).status_code==400
 # Seed groups are empty in this source; if legacy groups existed they'd be pending.
 r=c.get('/api/summary',params={'event':event});assert r.status_code==200,r.text
 total=next(r for r in r.json()['rows'] if r['pilot_id']==pid);assert total['total']==47
 assert c.put('/api/groups',json=g).status_code==400
 # Confirm data survives a fresh connection and re-initialization.
 m.DB_READY=False;m.ensure_database(force=True)
 with m.db.connect() as conn:assert conn.execute('SELECT count(*) FROM heat_calculations WHERE id IN (?,?,?)',saved).fetchone()[0]==3
 s=c.get('/api/summary',params={'event':event}).json()
 if not s['missing']:
  pdf=c.get('/api/final/pdf',params={'event':event});assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
  (Path(__file__).parent/'sample-final.pdf').write_bytes(pdf.content)
 assert c.post('/api/backup').content.startswith(b'SQLite format 3')
 assert c.delete('/api/history/'+str(saved[-1])).status_code==200
 assert c.get('/api/history/'+str(saved[-1])).status_code==404
 assert list((m.db.data_dir()/'backups').glob('*.db'))

def test_notes(client):
 c=client;r=c.post('/api/notes',json={'note':'Teste global'});assert r.status_code==200
 nid=r.json()['id'];assert c.put('/api/notes/'+str(nid),json={'resolved':True}).status_code==200
 assert next(n for n in c.get('/api/notes').json() if n['id']==nid)['resolved']==1

def test_weather_offline(client,monkeypatch):
 import weather_service
 client.put('/api/weather/location',json={'latitude':-27,'longitude':-48})
 def fail(*a,**k):raise OSError('offline')
 monkeypatch.setattr(weather_service,'_get_json',fail)
 w.WEATHER.update(at=0,value=None)
 assert client.get('/api/weather').json()['available']==False
 assert client.post('/api/calculate',json={'session_type':'RACE1','rows':[row()]}).status_code==200

def test_weather_values(client,monkeypatch):
 import weather_service
 monkeypatch.setattr(weather_service,'_get_json',lambda *a,**k:{'current':{'time':'2026-09-17T10:15','temperature_2m':22,'weather_code':0},'hourly':{'time':['2026-09-17T10:00'],'precipitation_probability':[20]}})
 w.WEATHER.update(at=0,value=None)
 assert client.get('/api/weather').json()['rain_probability']==20

def test_tie_break():
 records=[]
 for race in ['SUPER_POLE','RACE1','RACE2']:
  rows=[row(1,1,best_lap_ms=60000),row(2,2,best_lap_ms=58000)]
  for r in rows:r['points']=10
  records.append(dict(id=len(records)+1,event_name='e',category='90 KG',group_name='A',session_type=race,payload=json.dumps(rows)))
 s=m.calc.aggregate(records)
 assert s['rows'][0]['pilot_id']==2 and s['rows'][0]['rank']==1
 assert s['rows'][1]['rank']==2

def test_legacy_migration(tmp_path):
 path=tmp_path/'legacy.db'
 conn=sqlite3.connect(path);conn.row_factory=sqlite3.Row
 conn.execute('CREATE TABLE base_calculations(id INTEGER PRIMARY KEY,title TEXT,created_at TEXT,session_type TEXT,payload TEXT)')
 conn.execute("INSERT INTO base_calculations VALUES(1,'antigo','hoje','RACE1','[]')");conn.commit()
 m.calc.initialize(conn)
 assert conn.execute('SELECT title FROM heat_calculations WHERE id=1').fetchone()[0]=='antigo'
 conn.close()

def test_official_final_pdf(client):
 c=client;event='Evento final isolado'
 for race in ('SUPER_POLE','RACE1','RACE2'):
  p={'title':race,'category':'90 KG','group':'A','session_type':race,'event_name':event,'rows':[row(1,1,best_lap_ms=58000),row(2,2,best_lap_ms=59000)]}
  r=c.post('/api/save',json=p);assert r.status_code==200,r.text
 s=c.get('/api/summary',params={'event':event,'official':True});assert s.status_code==200,s.text
 pdf=c.get('/api/final/pdf',params={'event':event});assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
 (Path(__file__).parent/'sample-final.pdf').write_bytes(pdf.content)

def test_inconsistent_roster_blocked(client):
 c=client;event='Evento inconsistente'
 for race in ('SUPER_POLE','RACE1','RACE2'):
  rows=[row(1)] if race!='RACE2' else [row(2)]
  p={'title':race,'category':'90 KG','group':'A','session_type':race,'event_name':event,'rows':rows}
  assert c.post('/api/save',json=p).status_code==200
 assert c.get('/api/summary',params={'event':event,'official':True}).status_code==400

def test_csrf(client):
 assert client.post('/api/notes',json={'note':'csrf'},headers={'Origin':'https://example.org'}).status_code==403

def test_new_stage(client):
 p={'name':'Etapa Seguinte','date':'25/10/2026','location':'Kartódromo dos Ingleses'}
 assert client.post('/api/stages',json=p).status_code==200
 assert client.get('/api/bootstrap').json()['stage']['name']==p['name']
 assert client.post('/api/stages',json=p).status_code==400
