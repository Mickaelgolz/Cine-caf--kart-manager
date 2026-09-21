from __future__ import annotations

import json
import os
import sys
import sqlite3
import traceback
from pathlib import Path
from typing import Any, Optional, Literal

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "core"
DATA = Path(os.environ.get("CINECAFE_DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / "relatorios").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("CINECAFE_DATA_DIR", str(DATA))
os.environ.setdefault("CINECAFE_RELEASE_DIR", str(CORE))
sys.path.insert(0, str(CORE))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database as db
import heat_calculator as calc
import heat_reports

app = FastAPI(title="CineCafe Kart Manager Web", version="3.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

DB_READY = False
DB_ERROR = ""

def ensure_database(force: bool = False):
    global DB_READY, DB_ERROR
    if DB_READY and not force:
        return
    try:
        db.initialize_database()
        with db.connect() as conn:
            calc.initialize(conn)
            import web_services
            web_services.migrate(conn)
            # sanity check: these are the minimum tables the web UI needs
            for table in ("stages", "pilots", "categories"):
                if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    raise RuntimeError(f"Tabela obrigatória ausente: {table}")
        DB_READY = True
        DB_ERROR = ""
    except Exception as exc:
        DB_READY = False
        DB_ERROR = f"{type(exc).__name__}: {exc}"
        raise

def model_data(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()



@app.middleware("http")
async def api_database_guard(request: Request, call_next):
    # Static files, the main UI and diagnostics must always stay accessible.
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        try:
            ensure_database()
        except Exception as exc:
            return JSONResponse(status_code=500, content={"detail": "Banco indisponível. Consulte o diagnóstico no computador do organizador."})
    try:
        return await call_next(request)
    except sqlite3.Error as exc:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": "Não foi possível gravar. Confira os dados e tente novamente."})


class HeatRow(BaseModel):
    pilot_id: int
    name: str
    position: Optional[int] = None
    status: str = "FINISHED"
    fast: bool = False
    penalty: bool = False
    dq: bool = False
    dnf_points: bool = False
    best_lap_ms: Optional[int] = Field(default=None, gt=0)
    penalty_seconds: int = Field(default=0, ge=0, le=300)
    decision: str = ""


class CalculatePayload(BaseModel):
    session_type: str
    rows: list[HeatRow]


class SavePayload(CalculatePayload):
    record_id: Optional[int] = None
    expected_version: Optional[str] = None
    title: str
    category: str
    group: str
    dnf_rule: str = "Zero pontos"
    event_name: str


class NotePayload(BaseModel):
    note: str = Field(min_length=1, max_length=8000)


class PilotPayload(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    status: Literal["Ativo", "Inativo"] = "Ativo"
    number: str = ""
    whatsapp: str = ""
    state: str = ""
    email: str = ""
    birth_date: str = ""
    address: str = ""
    emergency_name: str = ""
    emergency_phone: str = ""
    notes: str = ""
    city: str = ""
    cpf: str = ""
    categories: list[str] = []


class StagePayload(BaseModel):
    name: str
    date: str
    location: str


class PdfPayload(SavePayload):
    pass


def rowdict(row):
    return dict(row) if row is not None else None


def active_stage(conn):
    rows = db.stages(conn)
    if not rows:
        raise ValueError("Nenhuma etapa cadastrada.")
    return rows[-1]


def get_events(conn) -> list[str]:
    calc.initialize(conn)
    rows = conn.execute(
        "SELECT DISTINCT event_name FROM heat_calculations WHERE event_name IS NOT NULL AND TRIM(event_name)<>'' ORDER BY event_name DESC"
    ).fetchall()
    stage = active_stage(conn)
    current = f"{stage['name']} - {stage['date']}"
    values = [current] + [r[0] for r in rows if r[0] != current]
    return values


@app.on_event("startup")
def startup():
    # Do not abort the web server if a migrated database needs repair.
    # The UI can still open and /api/bootstrap will report the exact error.
    try:
        ensure_database(force=True)
    except Exception:
        traceback.print_exc()


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
def home():
    # Serve the UI directly. It must remain available even when SQLite has a problem.
    return FileResponse(ROOT / "templates" / "index.html", media_type="text/html")


@app.get("/api/bootstrap")
def bootstrap():
    try:
        ensure_database()
    except Exception as exc:
        raise HTTPException(500, f"Falha ao preparar o banco do CineCafe: {exc}")
    with db.connect() as conn:
        calc.initialize(conn)
        stage = active_stage(conn)
        champ = db.championship(conn)
        categories = [rowdict(r) for r in db.categories(conn)]
        pilots = [rowdict(r) for r in conn.execute("SELECT id,name,status FROM pilots ORDER BY name COLLATE NOCASE")]
        counts = db.pilot_counts(conn)
        history_count = conn.execute("SELECT COUNT(*) FROM heat_calculations").fetchone()[0]
        notes_count = conn.execute("SELECT COUNT(*) FROM developer_notes WHERE stage_id=?", (stage["id"],)).fetchone()[0]
        event = f"{stage['name']} - {stage['date']}"
        scheduled = []
        for group in conn.execute('SELECT category,group_name,COUNT(*) size FROM web_groups WHERE event=? GROUP BY category,group_name ORDER BY category,group_name',(event,)):
            for race in ('SUPER_POLE','RACE1','RACE2'):
                done=conn.execute('SELECT 1 FROM heat_calculations WHERE event_name=? AND category=? AND group_name=? AND session_type=?',(event,group['category'],group['group_name'],race)).fetchone()
                scheduled.append(dict(category_name=group['category'],group_name=group['group_name'],session_type=race,status='Salva' if done else 'Pendente',planned_start=None))
        standings = {}
        for cat in categories:
            import web_services
            standings[cat["name"]] = web_services.championship_rows(conn, cat["name"])
        return {
            "brand": {"name": "CineCafe", "product": "KART MANAGER", "version": "WEB 3.2 MOBILE"},
            "championship": rowdict(champ),
            "stage": rowdict(stage),
            "categories": categories,
            "pilots": pilots,
            "counts": counts,
            "history_count": history_count,
            "notes_count": notes_count,
            "events": get_events(conn),
            "scheduled": scheduled[:12],
            "standings": standings,
            "data_dir": str(db.data_dir()),
        }


@app.get("/api/pilots")
def pilots(q: str = "", category: str = "", include_inactive: bool = False):
    with db.connect() as conn:
        params: list[Any] = []
        where = ["1=1"] if include_inactive else ["p.status='Ativo'"]
        if q.strip():
            where.append("LOWER(p.name) LIKE ?")
            params.append(f"%{q.strip().lower()}%")
        if category:
            where.append("EXISTS(SELECT 1 FROM registrations r JOIN categories c ON c.id=r.category_id WHERE r.pilot_id=p.id AND c.name=?)")
            params.append(category)
        sql = "SELECT p.* FROM pilots p WHERE " + " AND ".join(where) + " ORDER BY p.name COLLATE NOCASE"
        result = []
        for p in conn.execute(sql, params):
            cats = [r[0] for r in conn.execute("SELECT c.name FROM categories c JOIN registrations r ON r.category_id=c.id WHERE r.pilot_id=? ORDER BY c.name", (p["id"],))]
            result.append({**dict(p), "categories": cats})
        return result


@app.post("/api/pilots")
def create_pilot(payload: PilotPayload):
    with db.connect() as conn:
        pid = db.create_pilot(conn, payload.name.strip(), payload.status)
        import web_services
        web_services.save_profile(conn, pid, payload)
        return {"id": pid, "name": payload.name.strip(), "status": payload.status}


@app.post("/api/calculate")
def calculate(payload: CalculatePayload):
    rows = [model_data(r) for r in payload.rows]
    return calc.calculate(payload.session_type, rows)


@app.post("/api/save")
def save(payload: SavePayload):
    rows = [model_data(r) for r in payload.rows]
    with db.connect() as conn:
        calc.initialize(conn)
        import web_services
        return web_services.save_heat(conn, payload)


@app.get("/api/history")
def history(event: str = ""):
    with db.connect() as conn:
        calc.initialize(conn)
        sql = "SELECT * FROM heat_calculations"
        params: tuple[Any, ...] = ()
        if event:
            sql += " WHERE event_name=?"
            params = (event,)
        sql += " ORDER BY id DESC"
        result = []
        for r in conn.execute(sql, params):
            item = dict(r)
            payload = json.loads(item["payload"])
            item["pilots"] = len(payload)
            item["payload"] = payload
            result.append(item)
        return result


@app.get("/api/history/{record_id}")
def history_one(record_id: int):
    with db.connect() as conn:
        calc.initialize(conn)
        r = conn.execute("SELECT * FROM heat_calculations WHERE id=?", (record_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Resultado não encontrado.")
        item = dict(r)
        item["payload"] = json.loads(item["payload"])
        return item


@app.delete("/api/history/{record_id}")
def history_delete(record_id: int):
    with db.connect() as conn:
        calc.initialize(conn)
        if not conn.execute("SELECT id FROM heat_calculations WHERE id=?", (record_id,)).fetchone():
            raise HTTPException(404, "Resultado não encontrado.")
        db.backup_database(conn, "antes_excluir_resultado_web")
        with conn:
            conn.execute("DELETE FROM heat_calculations WHERE id=?", (record_id,))
        return {"ok": True}


@app.get("/api/notes")
def notes():
    with db.connect() as conn:
        stage = active_stage(conn)
        return [dict(r) for r in conn.execute("SELECT * FROM developer_notes ORDER BY id DESC")]


@app.post("/api/notes")
def note_add(payload: NotePayload):
    with db.connect() as conn:
        stage = active_stage(conn)
        note_id = db.add_developer_note(conn, stage["id"], payload.note.strip())
        return {"ok": True, "id": note_id}


@app.delete("/api/notes/{note_id}")
def note_delete(note_id: int):
    with db.connect() as conn:
        stage = active_stage(conn)
        with conn: conn.execute("DELETE FROM developer_notes WHERE id=?", (note_id,))
        return {"ok": True}


@app.put("/api/stage")
def stage_update(payload: StagePayload):
    with db.connect() as conn:
        stage = active_stage(conn)
        if conn.execute("SELECT 1 FROM stages WHERE name=? AND date=? AND id<>?", (payload.name.strip(),payload.date,stage["id"])).fetchone():raise ValueError("Já existe uma etapa com este nome e data.")
        old_event = f"{stage['name']} - {stage['date']}"
        db.save_stage_details(conn, stage["id"], payload.name, payload.date, payload.location)
        with conn:
            conn.execute("UPDATE heat_calculations SET event_name=? WHERE event_name=?", (f"{payload.name.strip()} - {payload.date}", old_event))
            conn.execute("UPDATE web_groups SET event=? WHERE event=?", (f"{payload.name.strip()} - {payload.date}", old_event))
        return {"ok": True}


@app.post("/api/export/pdf")
def export_pdf(payload: PdfPayload):
    rows = calc.calculate(payload.session_type, [model_data(r) for r in payload.rows])
    import uuid
    filename = "bateria_" + uuid.uuid4().hex + ".pdf"
    target = db.data_dir() / "relatorios" / filename
    record = {
        "title": payload.title,
        "category": payload.category,
        "group_name": payload.group,
        "session_type": payload.session_type,
        "payload": rows,
        "event_name": payload.event_name,
        "dnf_rule": payload.dnf_rule,
    }
    heat_reports.heats_pdf(target, [record])
    return FileResponse(target, media_type="application/pdf", filename=filename)


@app.get("/api/health")
def health():
    try:
        ensure_database()
    except Exception:
        pass
    return {
        "ok": True,
        "app": "CineCafe Kart Manager Web",
        "version": "3.2.0",
        "database_ready": DB_READY,
        "database_error": DB_ERROR,
        "data_dir": str(DATA),
    }

@app.get("/diagnostico")
def diagnostico():
    try:
        ensure_database(force=True)
        status = "Banco de dados OK"
    except Exception as exc:
        status = f"ERRO: {exc}"
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>CineCafe Diagnóstico</title>
    <style>body{{font-family:Segoe UI;background:#0b0b0d;color:#f4f4f4;padding:32px}}code{{color:#c9a96b}}.ok{{color:#54d18b}}.err{{color:#ff7773}}</style></head>
    <body><h1>CineCafe Web • Diagnóstico</h1><p>Servidor: <span class='ok'>OK</span></p>
    <p>Banco: <code>{status}</code></p><p>Pasta de dados: <code>{DATA}</code></p>
    <p>Se a página principal não carregar, envie uma captura desta tela.</p></body></html>"""
    return HTMLResponse(html)


import web_services
web_services.install(app)
