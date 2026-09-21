from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timedelta
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Optional

APP_NAME = "CineCafeKartManager_Apresentacao_v12"
GROUP_NAMES = tuple("ABCDEFGHIJ")


def resource_path(relative: str) -> Path:
    base = Path(os.environ.get("CINECAFE_RELEASE_DIR", getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)))
    return base / relative


def data_dir() -> Path:
    override = os.environ.get("CINECAFE_DATA_DIR") or os.environ.get("CINECAFE_DEMO_DATA_DIR")
    if override:
        path = Path(override)
    elif os.name == "nt":
        path = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    else:
        path = Path.home() / ".cine_cafe_kart_manager_apresentacao_v12"
    path.mkdir(parents=True, exist_ok=True)
    (path / "relatorios").mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "apresentacao_v12.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS championships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pilots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    status TEXT NOT NULL DEFAULT 'Ativo'
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pilot_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    initial_points REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(pilot_id) REFERENCES pilots(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(pilot_id, category_id)
);

CREATE TABLE IF NOT EXISTS stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    championship_id INTEGER NOT NULL,
    number INTEGER NOT NULL,
    name TEXT NOT NULL,
    date TEXT,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'Programada',
    responsible TEXT,
    started_at TEXT,
    ended_at TEXT,
    rain_forecast TEXT,
    FOREIGN KEY(championship_id) REFERENCES championships(id) ON DELETE CASCADE,
    UNIQUE(championship_id, number)
);

CREATE TABLE IF NOT EXISTS stage_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    pilot_id INTEGER NOT NULL,
    group_name TEXT,
    status TEXT NOT NULL DEFAULT 'Confirmado',
    signup_order INTEGER,
    FOREIGN KEY(stage_id) REFERENCES stages(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY(pilot_id) REFERENCES pilots(id) ON DELETE CASCADE,
    UNIQUE(stage_id, category_id, pilot_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    session_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Em andamento',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    weather_forecast TEXT,
    weather_summary TEXT,
    weather_fetched_at TEXT,
    FOREIGN KEY(stage_id) REFERENCES stages(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(stage_id, category_id, group_name, session_type)
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    pilot_id INTEGER NOT NULL,
    position INTEGER,
    fastest_manual INTEGER NOT NULL DEFAULT 0,
    penalty INTEGER NOT NULL DEFAULT 0,
    dq INTEGER NOT NULL DEFAULT 0,
    fastest_bonus REAL NOT NULL DEFAULT 0,
    points REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(pilot_id) REFERENCES pilots(id) ON DELETE CASCADE,
    UNIQUE(session_id, pilot_id)
);

CREATE TABLE IF NOT EXISTS developer_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    note TEXT NOT NULL,
    FOREIGN KEY(stage_id) REFERENCES stages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stage_totals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    pilot_id INTEGER NOT NULL,
    points REAL NOT NULL,
    FOREIGN KEY(stage_id) REFERENCES stages(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY(pilot_id) REFERENCES pilots(id) ON DELETE CASCADE,
    UNIQUE(stage_id, category_id, pilot_id)
);
"""

# Pontuação acumulada antes da 3ª etapa.
STANDINGS_110 = [
    ("Dheny Lobao", 82), ("Thiago Lopes", 76), ("Maicon Tessaro", 66),
    ("Toninho Silva", 59), ("Adriano Santos", 54), ("Elisandro Salsicha", 51),
    ("Jefferson Salaro", 47), ("Bruno Yoshida", 34), ("Saul Perotto", 30),
    ("Anderson Kahl", 28), ("Slava Konkin", 23), ("Leo Ottoni", 19),
    ("Diogo Barbosa", 17), ("Pedro Zimmermann", 17), ("Stanisalv Shchukin", 13),
    ("Eber Almeida", 12), ("Wander Pasternack", 11), ("Valdecir Kievel", 10),
    ("Ilia Fabrikantov", 0), ("Gregory Panda", 0),
]

STANDINGS_90 = [
    ("Felisberto Cordova", 78), ("Thiago Lopes", 78), ("Lucas Diefenthaeler", 77),
    ("Rafael Laurentino", 76), ("Raphael Donida", 65), ("Maicon Peixoto", 63),
    ("Mickael Golz", 63), ("Joao Zannata", 60), ("Hallan Silveira", 58),
    ("Rodrigo Bim", 48), ("Thiago Ferreira", 48), ("Victor Txai", 43),
    ("Mateus Martins", 42), ("Mirko Barcia", 41), ("Marcos Vinicius", 39),
    ("Anderson Kahl", 36), ("Eliandro Xavier", 36), ("Wander Pasternack", 31),
    ("Ottavio Rochadel", 25), ("Valdecir Kievel", 25), ("Ademilson Junior", 22),
    ("Diogo Freitas", 19), ("Gabriel Lino", 19), ("Matheus Lino", 18),
    ("Edmundo Souza", 18), ("Fernando Risan", 15), ("Eber Almeida", 11),
    ("Douglas Freitas", 9), ("Pedro Scholtz", 9), ("Alexsandro Silveira", 0),
]

CONFIRMADOS_110 = [
    "Adriano Santos", "Toninho Silva", "Jefferson Salaro", "Maicon Tessaro",
    "Diogo Barbosa", "Dheny Lobao", "Slava Konkin", "Stanisalv Shchukin",
    "Ilia Fabrikantov", "Valdecir Kievel", "Anderson Kahl", "Andre Gomes",
    "Leo Ottoni", "Thiago Lopes", "Erich Frentzlaff",
]

CONFIRMADOS_90 = [
    "Rafael Laurentino", "Alexsandro Silveira", "Lucas Diefenthaeler",
    "Felisberto Cordova", "Luciano Ferreira", "Mirko Barcia", "Joao Zannata",
    "Fernando Risan", "Rodrigo Bim", "Mateus Martins", "Anderson Lucinda",
    "Pedro Scholtz", "Gabriel Scholtz", "Mickael Golz", "Raphael Donida",
    "Valdecir Kievel", "Andre Gomes", "Anna Nury", "Diego Leite", "Maicon Peixoto",
    "Marcos Vinicius", "Victor Txai", "Ademilson Junior", "Hallan Silveira",
    "Thiago Lopes", "Matheus Cruz", "Ottavio Oliveira",
]

# Grupos observados nas artes fornecidas anteriormente. Pilotos novos ficam sem grupo.
PRIOR_GROUPS_110 = {
    "Adriano Santos": "A", "Anderson Kahl": "A", "Diogo Barbosa": "A",
    "Jefferson Salaro": "A", "Leo Ottoni": "A", "Maicon Tessaro": "A", "Thiago Lopes": "A",
    "Ilia Fabrikantov": "B", "Dheny Lobao": "B", "Slava Konkin": "B",
    "Stanisalv Shchukin": "B", "Toninho Silva": "B",
}
PRIOR_GROUPS_90 = {
    "Anderson Lucinda": "A", "Felisberto Cordova": "A",
    "Gabriel Scholtz": "B", "Joao Zannata": "B", "Lucas Diefenthaeler": "B",
    "Maicon Peixoto": "B", "Mateus Martins": "B", "Thiago Lopes": "B",
    "Alexsandro Silveira": "C", "Hallan Silveira": "C", "Luciano Ferreira": "C",
    "Mirko Barcia": "C", "Ottavio Oliveira": "C", "Pedro Scholtz": "C",
    "Rafael Laurentino": "C", "Rodrigo Bim": "C",
}


def _norm(text: str) -> str:
    txt = unicodedata.normalize("NFKD", (text or "").strip().upper())
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return " ".join(txt.split())


def initialize_database() -> None:
    with connect() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 15 and conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pilots'").fetchone():
            backup_database(conn, "antes_v15")
        conn.executescript(SCHEMA)
        _migrate_schema(conn)
        if conn.execute("SELECT id FROM championships LIMIT 1").fetchone() is None:
            seed(conn)
        migrate_v15(conn)
        migrate_v17(conn)
        migrate_v18(conn)
        migrate_v20(conn)
        migrate_v21(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(stages)").fetchall()}
    for name in ("responsible", "started_at", "ended_at", "rain_forecast"):
        if name not in cols:
            conn.execute(f"ALTER TABLE stages ADD COLUMN {name} TEXT")
    session_cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    for name in ("weather_forecast", "weather_summary", "weather_fetched_at"):
        if name not in session_cols:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} TEXT")
    conn.execute("""CREATE TABLE IF NOT EXISTS developer_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        note TEXT NOT NULL,
        FOREIGN KEY(stage_id) REFERENCES stages(id) ON DELETE CASCADE
    )""")
    conn.commit()


def find_pilot_by_name(conn: sqlite3.Connection, name: str):
    target = _norm(name)
    if not target:
        return None
    for row in conn.execute("SELECT * FROM pilots ORDER BY id").fetchall():
        if _norm(row["name"]) == target:
            return row
    return None


def _pilot_id(conn: sqlite3.Connection, name: str) -> int:
    row = find_pilot_by_name(conn, name)
    if row:
        return row["id"]
    return conn.execute("INSERT INTO pilots(name) VALUES(?)", (name.strip(),)).lastrowid


def seed(conn: sqlite3.Connection) -> None:
    champ_id = conn.execute(
        "INSERT INTO championships(name,year) VALUES(?,?)", ("GP Cine Café 2026", 2026)
    ).lastrowid
    cat90 = conn.execute("INSERT INTO categories(name) VALUES('90 KG')").lastrowid
    cat110 = conn.execute("INSERT INTO categories(name) VALUES('110 KG')").lastrowid
    stage_id = conn.execute(
        "INSERT INTO stages(championship_id,number,name,date,location,status) VALUES(?,?,?,?,?,?)",
        (champ_id, 3, "3ª Etapa", "26/09/2026", "Kartódromo dos Ingleses", "Programada"),
    ).lastrowid

    points90 = dict(STANDINGS_90)
    points110 = dict(STANDINGS_110)
    names90 = list(dict.fromkeys([n for n, _ in STANDINGS_90] + CONFIRMADOS_90))
    names110 = list(dict.fromkeys([n for n, _ in STANDINGS_110] + CONFIRMADOS_110))

    for name in names90:
        pid = _pilot_id(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO registrations(pilot_id,category_id,initial_points) VALUES(?,?,?)",
            (pid, cat90, points90.get(name, 0)),
        )
    for name in names110:
        pid = _pilot_id(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO registrations(pilot_id,category_id,initial_points) VALUES(?,?,?)",
            (pid, cat110, points110.get(name, 0)),
        )

    for order, name in enumerate(CONFIRMADOS_90, 1):
        pid = _pilot_id(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO stage_entries(stage_id,category_id,pilot_id,group_name,status,signup_order) VALUES(?,?,?,?,?,?)",
            (stage_id, cat90, pid, PRIOR_GROUPS_90.get(name), "Confirmado", order),
        )
    for order, name in enumerate(CONFIRMADOS_110, 1):
        pid = _pilot_id(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO stage_entries(stage_id,category_id,pilot_id,group_name,status,signup_order) VALUES(?,?,?,?,?,?)",
            (stage_id, cat110, pid, PRIOR_GROUPS_110.get(name), "Confirmado", order),
        )


def championship(conn):
    return conn.execute("SELECT * FROM championships ORDER BY id LIMIT 1").fetchone()


def stages(conn):
    return conn.execute("SELECT * FROM stages ORDER BY number").fetchall()


def categories(conn):
    return conn.execute("SELECT * FROM categories ORDER BY CASE name WHEN '90 KG' THEN 1 ELSE 2 END, name").fetchall()


def stage_row(conn, stage_id: int):
    return conn.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()


def registered_pilots(conn, category_id: int):
    return conn.execute(
        """
        SELECT p.id, p.name, p.status, r.initial_points
        FROM registrations r JOIN pilots p ON p.id=r.pilot_id
        WHERE r.category_id=? ORDER BY p.name COLLATE NOCASE
        """,
        (category_id,),
    ).fetchall()


def group_pilots(conn, stage_id: int, category_id: int, group_name: str):
    return conn.execute(
        """
        SELECT p.id, p.name, se.status, se.signup_order
        FROM stage_entries se JOIN pilots p ON p.id=se.pilot_id
        WHERE se.stage_id=? AND se.category_id=? AND se.group_name=? AND se.status='Confirmado'
        ORDER BY COALESCE(se.signup_order,9999), p.name COLLATE NOCASE
        """,
        (stage_id, category_id, group_name),
    ).fetchall()


def unassigned_confirmed(conn, stage_id: int):
    return conn.execute(
        """
        SELECT se.*, p.name, c.name category_name
        FROM stage_entries se
        JOIN pilots p ON p.id=se.pilot_id
        JOIN categories c ON c.id=se.category_id
        WHERE se.stage_id=? AND se.status='Confirmado' AND (se.group_name IS NULL OR se.group_name='')
        ORDER BY c.name,p.name
        """,
        (stage_id,),
    ).fetchall()


def pilot_summary(conn, stage_id: int):
    cats = {r["name"]: r["id"] for r in categories(conn)}
    rows = conn.execute("SELECT * FROM pilots ORDER BY name COLLATE NOCASE").fetchall()
    out = []
    for p in rows:
        item = {"id": p["id"], "name": p["name"], "status": p["status"]}
        for cat_name in ("90 KG", "110 KG"):
            cid = cats.get(cat_name)
            reg = conn.execute("SELECT id,initial_points FROM registrations WHERE pilot_id=? AND category_id=?", (p["id"], cid)).fetchone() if cid else None
            entry = conn.execute("SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?", (stage_id, cid, p["id"])).fetchone() if cid else None
            prefix = "c90" if cat_name == "90 KG" else "c110"
            item[prefix] = bool(reg)
            item[prefix + "_group"] = (entry["group_name"] if entry and entry["group_name"] else "—")
            item[prefix + "_confirmed"] = bool(entry and entry["status"] == "Confirmado")
        out.append(item)
    return out


def create_pilot(conn: sqlite3.Connection, name: str, status: str = "Ativo") -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Digite o nome do piloto.")
    existing = find_pilot_by_name(conn, name)
    if existing:
        raise ValueError(f"O piloto '{existing['name']}' já está cadastrado.")
    pid = conn.execute("INSERT INTO pilots(name,status) VALUES(?,?)", (name, status)).lastrowid
    conn.commit()
    return pid


def update_pilot(conn: sqlite3.Connection, pilot_id: int, name: str, status: str = "Ativo") -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("Digite o nome do piloto.")
    existing = find_pilot_by_name(conn, name)
    if existing and existing["id"] != pilot_id:
        raise ValueError(f"O piloto '{existing['name']}' já está cadastrado.")
    conn.execute("UPDATE pilots SET name=?,status=? WHERE id=?", (name, status, pilot_id))
    conn.commit()


def pilot_registration_membership(conn: sqlite3.Connection, pilot_id: int):
    """Cadastro permanente do piloto no campeonato, sem relação com a etapa atual."""
    data = {}
    for cat in categories(conn):
        reg = conn.execute(
            "SELECT * FROM registrations WHERE pilot_id=? AND category_id=?",
            (pilot_id, cat["id"]),
        ).fetchone()
        data[cat["id"]] = {
            "category": cat,
            "enabled": bool(reg),
            "initial_points": float(reg["initial_points"] or 0) if reg else 0.0,
        }
    return data


def set_pilot_registration(
    conn: sqlite3.Connection,
    pilot_id: int,
    category_id: int,
    enabled: bool,
) -> None:
    """Liga/desliga a inscrição permanente do piloto em uma categoria.

    A organização da etapa fica em stage_entries e não é criada aqui.
    """
    reg = conn.execute(
        "SELECT * FROM registrations WHERE pilot_id=? AND category_id=?",
        (pilot_id, category_id),
    ).fetchone()
    if enabled:
        if not reg:
            conn.execute(
                "INSERT INTO registrations(pilot_id,category_id,initial_points) VALUES(?,?,0)",
                (pilot_id, category_id),
            )
            conn.commit()
        return

    if not reg:
        return

    if float(reg["initial_points"] or 0) != 0:
        raise ValueError("Este piloto possui pontuação anterior nessa categoria e não pode ser removido do campeonato.")

    historical_entries = conn.execute(
        "SELECT COUNT(*) n FROM stage_entries WHERE pilot_id=? AND category_id=?",
        (pilot_id, category_id),
    ).fetchone()["n"]
    historical_totals = conn.execute(
        "SELECT COUNT(*) n FROM stage_totals WHERE pilot_id=? AND category_id=?",
        (pilot_id, category_id),
    ).fetchone()["n"]
    historical_results = conn.execute(
        """
        SELECT COUNT(*) n
        FROM results r JOIN sessions s ON s.id=r.session_id
        WHERE r.pilot_id=? AND s.category_id=?
        """,
        (pilot_id, category_id),
    ).fetchone()["n"]
    if historical_entries or historical_totals or historical_results:
        raise ValueError(
            "Este piloto já possui histórico nessa categoria. Para preservar os resultados, mantenha a categoria cadastrada."
        )

    conn.execute("DELETE FROM registrations WHERE id=?", (reg["id"],))
    conn.commit()


def category_has_started_session(conn: sqlite3.Connection, stage_id: int, category_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sessions WHERE stage_id=? AND category_id=? LIMIT 1",
        (stage_id, category_id),
    ).fetchone()
    return bool(row)


def _ensure_category_editable(conn: sqlite3.Connection, stage_id: int, category_id: int) -> None:
    if stage_row(conn, stage_id)["status"] == "Finalizada":
        raise ValueError("A etapa está finalizada.")
    if category_has_started_session(conn, stage_id, category_id):
        raise ValueError(
            "Já existe bateria iniciada nesta categoria. A formação dos grupos foi bloqueada para preservar os resultados."
        )


def category_organization_rows(conn: sqlite3.Connection, stage_id: int, category_id: int):
    """Todos os pilotos ativos inscritos na categoria e seu estado nesta etapa."""
    return conn.execute(
        """
        SELECT p.id,p.name,p.status,
               se.id entry_id,se.group_name,se.status entry_status,se.signup_order
        FROM registrations r
        JOIN pilots p ON p.id=r.pilot_id
        LEFT JOIN stage_entries se
          ON se.stage_id=? AND se.category_id=r.category_id AND se.pilot_id=p.id
        WHERE r.category_id=? AND p.status='Ativo'
        ORDER BY p.name COLLATE NOCASE
        """,
        (stage_id, category_id),
    ).fetchall()


def organization_available_pilots(conn: sqlite3.Connection, stage_id: int, category_id: int):
    return [
        r for r in category_organization_rows(conn, stage_id, category_id)
        if (r["entry_status"] is None)
        or (r["entry_status"] == "Confirmado" and not (r["group_name"] or "").strip())
    ]


def organization_absent_pilots(conn: sqlite3.Connection, stage_id: int, category_id: int):
    return [
        r for r in category_organization_rows(conn, stage_id, category_id)
        if r["entry_status"] == "Não participa"
    ]


def organization_summary(conn: sqlite3.Connection, stage_id: int, category_id: int):
    rows = category_organization_rows(conn, stage_id, category_id)
    groups = {g: 0 for g in GROUP_NAMES}
    absent = 0
    pending = 0
    for r in rows:
        if r["entry_status"] == "Não participa":
            absent += 1
        elif r["entry_status"] == "Confirmado" and r["group_name"] in groups:
            groups[r["group_name"]] += 1
        else:
            pending += 1
    participating = sum(groups.values())
    return {
        "registered": len(rows),
        "participating": participating,
        "absent": absent,
        "pending": pending,
        **groups,
    }


def assign_pilots_to_group(
    conn: sqlite3.Connection,
    stage_id: int,
    category_id: int,
    pilot_ids,
    group_name: str,
    _commit: bool = True,
) -> None:
    group_name = (group_name or "").strip().upper()
    if group_name not in GROUP_NAMES:
        raise ValueError("Grupo inválido. Use uma letra de A até J.")
    ids = [int(x) for x in pilot_ids]
    if not ids:
        raise ValueError("Selecione pelo menos um piloto.")
    _ensure_category_editable(conn, stage_id, category_id)
    ids = list(dict.fromkeys(ids))
    existing = {p["id"] for p in group_pilots(conn, stage_id, category_id, group_name)}
    if len(existing | set(ids)) > organization_limit(conn, stage_id, category_id):
        raise ValueError("Limite do grupo excedido. Ajuste o limite antes de incluir pilotos.")
    for pid in ids:
        if not conn.execute("SELECT 1 FROM registrations r JOIN pilots p ON p.id=r.pilot_id WHERE r.pilot_id=? AND r.category_id=? AND p.status='Ativo'", (pid, category_id)).fetchone():
            raise ValueError("Piloto inativo ou sem inscrição nesta categoria.")

    for pid in ids:
        reg = conn.execute(
            "SELECT 1 FROM registrations WHERE pilot_id=? AND category_id=?",
            (pid, category_id),
        ).fetchone()
        if not reg:
            raise ValueError("Um dos pilotos selecionados não está cadastrado nesta categoria.")
        entry = conn.execute(
            "SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?",
            (stage_id, category_id, pid),
        ).fetchone()
        if entry:
            conn.execute(
                "UPDATE stage_entries SET group_name=?,status='Confirmado' WHERE id=?",
                (group_name, entry["id"]),
            )
        else:
            order = conn.execute(
                "SELECT COALESCE(MAX(signup_order),0)+1 n FROM stage_entries WHERE stage_id=? AND category_id=?",
                (stage_id, category_id),
            ).fetchone()["n"]
            conn.execute(
                "INSERT INTO stage_entries(stage_id,category_id,pilot_id,group_name,status,signup_order) VALUES(?,?,?,?,?,?)",
                (stage_id, category_id, pid, group_name, "Confirmado", order),
            )
    if _commit:
        conn.commit()


def set_pilots_not_participating(
    conn: sqlite3.Connection,
    stage_id: int,
    category_id: int,
    pilot_ids,
) -> None:
    ids = [int(x) for x in pilot_ids]
    if not ids:
        raise ValueError("Selecione pelo menos um piloto.")
    _ensure_category_editable(conn, stage_id, category_id)
    for pid in ids:
        reg = conn.execute(
            "SELECT 1 FROM registrations WHERE pilot_id=? AND category_id=?",
            (pid, category_id),
        ).fetchone()
        if not reg:
            continue
        entry = conn.execute(
            "SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?",
            (stage_id, category_id, pid),
        ).fetchone()
        if entry:
            conn.execute(
                "UPDATE stage_entries SET group_name=NULL,status='Não participa' WHERE id=?",
                (entry["id"],),
            )
        else:
            order = conn.execute(
                "SELECT COALESCE(MAX(signup_order),0)+1 n FROM stage_entries WHERE stage_id=? AND category_id=?",
                (stage_id, category_id),
            ).fetchone()["n"]
            conn.execute(
                "INSERT INTO stage_entries(stage_id,category_id,pilot_id,group_name,status,signup_order) VALUES(?,?,?,?,?,?)",
                (stage_id, category_id, pid, None, "Não participa", order),
            )
    conn.commit()


def return_pilots_to_available(
    conn: sqlite3.Connection,
    stage_id: int,
    category_id: int,
    pilot_ids,
) -> None:
    ids = [int(x) for x in pilot_ids]
    if not ids:
        raise ValueError("Selecione pelo menos um piloto.")
    _ensure_category_editable(conn, stage_id, category_id)
    for pid in ids:
        entry = conn.execute(
            "SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?",
            (stage_id, category_id, pid),
        ).fetchone()
        if entry:
            # Mantemos a ordem de inscrição e removemos apenas a definição de participação/grupo.
            conn.execute(
                "UPDATE stage_entries SET group_name=NULL,status='Confirmado' WHERE id=?",
                (entry["id"],),
            )
    conn.commit()


def auto_distribute_pilots(conn, stage_id, category_id, pilot_ids):
    import random
    ids=list(dict.fromkeys(int(p) for p in pilot_ids))
    random.SystemRandom().shuffle(ids)
    if not ids: raise ValueError("Selecione os pilotos.")
    _ensure_category_editable(conn,stage_id,category_id)
    available={r['id'] for r in organization_available_pilots(conn,stage_id,category_id)}
    if not set(ids)<=available: raise ValueError("Selecione apenas pilotos disponíveis.")
    summary=organization_summary(conn,stage_id,category_id)
    scheduled={r['group_name'] for r in scheduled_sessions(conn,stage_id) if r['category_id']==category_id}
    occupied={g for g in GROUP_NAMES if summary[g]}
    enabled=tuple(g for g in GROUP_NAMES if g in scheduled) or GROUP_NAMES[:max(4,max((GROUP_NAMES.index(g)+1 for g in occupied),default=0))]
    counts={g:summary[g] for g in enabled}; plan={g:[] for g in counts}
    for pid in ids:
        target=min(counts,key=lambda g:(counts[g],g));plan[target].append(pid);counts[target]+=1
    if max(counts.values())>organization_limit(conn,stage_id,category_id):
        raise ValueError("A distribuição ultrapassa o limite. Ajuste o limite ou selecione menos pilotos.")
    with conn:
        for g,group_ids in plan.items():
            if group_ids: assign_pilots_to_group(conn,stage_id,category_id,group_ids,g,_commit=False)
    return counts


def previous_stage(conn: sqlite3.Connection, stage_id: int):
    stage = stage_row(conn, stage_id)
    return conn.execute(
        """
        SELECT * FROM stages
        WHERE championship_id=? AND number<?
        ORDER BY number DESC LIMIT 1
        """,
        (stage["championship_id"], stage["number"]),
    ).fetchone()


def copy_category_groups_from_previous_stage(
    conn: sqlite3.Connection,
    stage_id: int,
    category_id: int,
) -> int:
    _ensure_category_editable(conn, stage_id, category_id)
    prev = previous_stage(conn, stage_id)
    if not prev:
        raise ValueError("Não existe etapa anterior cadastrada para copiar os grupos.")
    rows = conn.execute(
        """
        SELECT se.pilot_id,se.group_name,se.status
        FROM stage_entries se
        JOIN registrations r ON r.pilot_id=se.pilot_id AND r.category_id=se.category_id
        WHERE se.stage_id=? AND se.category_id=?
          AND (se.status='Não participa' OR (se.status='Confirmado' AND se.group_name BETWEEN 'A' AND 'J'))
        """,
        (prev["id"], category_id),
    ).fetchall()
    if not rows:
        raise ValueError("A etapa anterior não possui organização salva para esta categoria.")
    final={r['id']:r['group_name'] for r in category_organization_rows(conn,stage_id,category_id) if r['entry_status']=='Confirmado'}
    active={r['id'] for r in category_organization_rows(conn,stage_id,category_id)}
    rows=[r for r in rows if r['pilot_id'] in active]
    for row in rows:
        final[row['pilot_id']]=row['group_name'] if row['status']=='Confirmado' else None
    if any(sum(v==g for v in final.values())>organization_limit(conn,stage_id,category_id) for g in GROUP_NAMES):
        raise ValueError('A formação anterior ultrapassa o limite atual. Ajuste o limite antes de copiar.')
    # Remove old memberships first so moving between full groups is possible.
    with conn:
        for row in rows:
            conn.execute("UPDATE stage_entries SET group_name=NULL,status='Não participa' WHERE stage_id=? AND category_id=? AND pilot_id=?",(stage_id,category_id,row['pilot_id']))
    copied = 0
    for row in rows:
        if row["status"] == "Não participa":
            set_pilots_not_participating(conn, stage_id, category_id, [row["pilot_id"]])
        else:
            assign_pilots_to_group(conn, stage_id, category_id, [row["pilot_id"]], row["group_name"])
        copied += 1
    return copied


def set_pilot_category_group(
    conn: sqlite3.Connection,
    stage_id: int,
    pilot_id: int,
    category_id: int,
    enabled: bool,
    group_name: Optional[str],
) -> None:
    reg = conn.execute("SELECT * FROM registrations WHERE pilot_id=? AND category_id=?", (pilot_id, category_id)).fetchone()
    entry = conn.execute("SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?", (stage_id, category_id, pilot_id)).fetchone()
    if enabled:
        if not reg:
            conn.execute("INSERT INTO registrations(pilot_id,category_id,initial_points) VALUES(?,?,0)", (pilot_id, category_id))
        # Uma única linha por etapa+categoria+piloto garante que ele nunca esteja em dois grupos da mesma categoria.
        if entry:
            conn.execute("UPDATE stage_entries SET group_name=?,status='Confirmado' WHERE id=?", (group_name, entry["id"]))
        else:
            order = conn.execute("SELECT COALESCE(MAX(signup_order),0)+1 n FROM stage_entries WHERE stage_id=? AND category_id=?", (stage_id, category_id)).fetchone()["n"]
            conn.execute(
                "INSERT INTO stage_entries(stage_id,category_id,pilot_id,group_name,status,signup_order) VALUES(?,?,?,?,?,?)",
                (stage_id, category_id, pilot_id, group_name, "Confirmado", order),
            )
    else:
        used = conn.execute(
            """
            SELECT COUNT(*) n FROM results r JOIN sessions s ON s.id=r.session_id
            WHERE r.pilot_id=? AND s.stage_id=? AND s.category_id=?
            """,
            (pilot_id, stage_id, category_id),
        ).fetchone()["n"]
        if used:
            raise ValueError("Este piloto já possui resultados nessa categoria e não pode ser removido dela.")
        if entry:
            conn.execute("DELETE FROM stage_entries WHERE id=?", (entry["id"],))
        if reg and float(reg["initial_points"] or 0) == 0:
            conn.execute("DELETE FROM registrations WHERE id=?", (reg["id"],))
        elif reg:
            raise ValueError("Este piloto possui pontuação anterior nessa categoria e não pode ser removido do campeonato.")
    conn.commit()


def pilot_membership(conn, stage_id: int, pilot_id: int):
    data = {}
    for cat in categories(conn):
        reg = conn.execute("SELECT * FROM registrations WHERE pilot_id=? AND category_id=?", (pilot_id, cat["id"])).fetchone()
        entry = conn.execute("SELECT * FROM stage_entries WHERE stage_id=? AND category_id=? AND pilot_id=?", (stage_id, cat["id"], pilot_id)).fetchone()
        data[cat["id"]] = {
            "category": cat,
            "enabled": bool(reg),
            "group": entry["group_name"] if entry and entry["group_name"] else "",
            "confirmed": bool(entry and entry["status"] == "Confirmado"),
        }
    return data


def session_row(conn, stage_id: int, category_id: int, group_name: str, session_type: str):
    return conn.execute(
        "SELECT * FROM sessions WHERE stage_id=? AND category_id=? AND group_name=? AND session_type=?",
        (stage_id, category_id, group_name, session_type),
    ).fetchone()


def start_session(conn, stage_id: int, category_id: int, group_name: str, session_type: str) -> int:
    stage = stage_row(conn, stage_id)
    if stage["status"] != "Em andamento":
        raise ValueError("Inicie a etapa na aba INÍCIO antes de iniciar uma bateria.")
    if session_type not in ("SUPER_POLE", "RACE1", "RACE2"):
        raise ValueError("Sessão inválida.")
    if not organization_confirmed(conn, stage_id, category_id):
        raise ValueError("Salve os grupos em Organizar baterias antes de iniciar.")
    pilots = group_pilots(conn, stage_id, category_id, group_name)
    if not pilots:
        raise ValueError("Não existem pilotos neste grupo. Monte as baterias na aba ORGANIZAR BATERIAS.")
    sess = session_row(conn, stage_id, category_id, group_name, session_type)
    if sess:
        raise ValueError("Já existe uma bateria com esta mesma categoria, grupo e sessão. Use a bateria existente para evitar duplicidade.")
    with conn:
        sid = conn.execute(
            "INSERT INTO sessions(stage_id,category_id,group_name,session_type,status,weather_forecast,weather_summary,weather_fetched_at,started_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (stage_id, category_id, group_name, session_type, "Em andamento", stage["weather_forecast"], stage["weather_summary"], stage["weather_fetched_at"], local_now()),
        ).lastrowid
        for p in pilots:
            conn.execute("INSERT OR IGNORE INTO results(session_id,pilot_id) VALUES(?,?)", (sid, p["id"]))
        if session_type == 'RACE1' and not session_row(conn,stage_id,category_id,group_name,'SUPER_POLE'):
            started=conn.execute('SELECT started_at FROM sessions WHERE id=?',(sid,)).fetchone()[0]
            pole=conn.execute("INSERT INTO sessions(stage_id,category_id,group_name,session_type,status,started_at) VALUES(?,?,?,'SUPER_POLE','Em andamento',?)",(stage_id,category_id,group_name,started)).lastrowid
            for p in pilots:conn.execute('INSERT INTO results(session_id,pilot_id) VALUES(?,?)',(pole,p['id']))
    return sid


def session_grid_rows(conn, session_id: int):
    return conn.execute(
        """
        SELECT r.*, p.name
        FROM results r JOIN pilots p ON p.id=r.pilot_id
        WHERE r.session_id=?
        ORDER BY p.name COLLATE NOCASE
        """,
        (session_id,),
    ).fetchall()


def save_result_draft(
    conn, session_id: int, pilot_id: int, position: Optional[int], fastest: bool, penalty: bool, dq: bool
) -> None:
    sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not sess or sess["status"] != "Em andamento":
        raise ValueError("A bateria precisa estar em andamento para editar resultados.")
    if fastest:
        conn.execute("UPDATE results SET fastest_manual=0 WHERE session_id=?", (session_id,))
    conn.execute(
        "UPDATE results SET position=?,fastest_manual=?,penalty=?,dq=? WHERE session_id=? AND pilot_id=?",
        (position, int(fastest), int(penalty), int(dq), session_id, pilot_id),
    )
    conn.commit()


def session_status(conn, stage_id: int, category_id: int, group_name: str, session_type: str) -> str:
    row = session_row(conn, stage_id, category_id, group_name, session_type)
    return row["status"] if row else "Aguardando"


def expected_batteries(conn, stage_id: int):
    groups = conn.execute(
        """
        SELECT c.id category_id,c.name category_name,se.group_name,COUNT(*) pilots
        FROM stage_entries se JOIN categories c ON c.id=se.category_id
        WHERE se.stage_id=? AND se.status='Confirmado' AND se.group_name IS NOT NULL AND se.group_name<>''
        GROUP BY c.id,c.name,se.group_name
        ORDER BY CASE c.name WHEN '90 KG' THEN 1 ELSE 2 END,se.group_name
        """,
        (stage_id,),
    ).fetchall()
    out = []
    for g in groups:
        for stype in ("SUPER_POLE", "RACE1", "RACE2"):
            sess = session_row(conn, stage_id, g["category_id"], g["group_name"], stype)
            out.append({
                "category_id": g["category_id"], "category_name": g["category_name"],
                "group_name": g["group_name"], "session_type": stype,
                "pilots": g["pilots"], "status": sess["status"] if sess else "Aguardando",
                "session_id": sess["id"] if sess else None,
            })
    return out


def reopen_session(conn, session_id: int) -> None:
    sess = conn.execute("SELECT s.*,st.status stage_status FROM sessions s JOIN stages st ON st.id=s.stage_id WHERE s.id=?", (session_id,)).fetchone()
    if not sess:
        raise ValueError("Bateria não encontrada.")
    if sess["stage_status"] == "Finalizada":
        raise ValueError("A etapa já foi finalizada e esta bateria não pode ser reaberta nesta versão.")
    conn.execute("UPDATE sessions SET status='Em andamento',completed_at=NULL WHERE id=?", (session_id,))
    conn.commit()


def stage_sessions(conn, stage_id: int):
    return conn.execute(
        """
        SELECT s.*, c.name category_name,
               (SELECT COUNT(*) FROM results r WHERE r.session_id=s.id AND r.position IS NOT NULL) result_count,
               (SELECT COUNT(*) FROM results r WHERE r.session_id=s.id) pilot_count
        FROM sessions s JOIN categories c ON c.id=s.category_id
        WHERE s.stage_id=?
        ORDER BY CASE c.name WHEN '90 KG' THEN 1 ELSE 2 END,s.group_name,
                 CASE s.session_type WHEN 'SUPER_POLE' THEN 1 WHEN 'RACE1' THEN 2 ELSE 3 END
        """,
        (stage_id,),
    ).fetchall()


def classification(conn, category_id: int):
    return conn.execute(
        """
        SELECT p.id pilot_id,p.name,reg.initial_points,
               COALESCE(SUM(st.points),0) stage_points,
               reg.initial_points + COALESCE(SUM(st.points),0) total
        FROM registrations reg
        JOIN pilots p ON p.id=reg.pilot_id
        LEFT JOIN stage_totals st ON st.pilot_id=p.id AND st.category_id=reg.category_id
        WHERE reg.category_id=?
        GROUP BY p.id,p.name,reg.initial_points
        ORDER BY total DESC,p.name COLLATE NOCASE
        """,
        (category_id,),
    ).fetchall()



def pilot_counts(conn):
    total = conn.execute("SELECT COUNT(*) n FROM pilots").fetchone()["n"]
    rows = conn.execute("SELECT c.name,COUNT(DISTINCT r.pilot_id) n FROM categories c LEFT JOIN registrations r ON r.category_id=c.id GROUP BY c.id,c.name").fetchall()
    by_cat = {r["name"]: r["n"] for r in rows}
    return {"total": total, "90 KG": by_cat.get("90 KG", 0), "110 KG": by_cat.get("110 KG", 0)}


def start_stage(conn, stage_id: int, responsible: str) -> str:
    stage = stage_row(conn, stage_id)
    if stage["status"] != "Programada":
        raise ValueError("A etapa só pode ser iniciada quando estiver Programada.")
    responsible = responsible.strip()
    if not responsible:
        raise ValueError("Informe o responsável pela etapa.")
    token = uuid.uuid4().hex
    with conn:
        conn.execute("""UPDATE stages SET status='Em andamento',responsible=?,started_at=?,ended_at=NULL,
            weather_status='Consultando',weather_token=?,weather_forecast=NULL,weather_summary=NULL,
            weather_fetched_at=NULL,rain_forecast=NULL WHERE id=?""",
            (responsible, local_now(), token, stage_id))
    return token


def reset_stage(conn, stage_id: int) -> None:
    if not stage_row(conn, stage_id):
        raise ValueError('Etapa não encontrada.')
    backup_database(conn, "antes_reset")
    note_images=[r['image_path'] for r in developer_notes(conn,stage_id) if r['image_path']]
    with conn:
        conn.execute("DELETE FROM stage_totals WHERE stage_id=?", (stage_id,))
        conn.execute("DELETE FROM sessions WHERE stage_id=?", (stage_id,))
        conn.execute("DELETE FROM schedule WHERE stage_id=?", (stage_id,))
        conn.execute("DELETE FROM developer_notes WHERE stage_id=?", (stage_id,))
        conn.execute("""UPDATE stage_entries SET group_name=NULL,status='Confirmado'
            WHERE stage_id=? AND (group_name IS NULL OR group_name='' OR status<>'Confirmado')""", (stage_id,))
        conn.execute("UPDATE organization_settings SET confirmed_at=NULL WHERE stage_id=?", (stage_id,))
        conn.execute("""UPDATE stages SET status='Programada',responsible=NULL,started_at=NULL,
            ended_at=NULL,rain_forecast=NULL,weather_forecast=NULL,weather_summary=NULL,
            weather_fetched_at=NULL,weather_status='Não consultada',weather_token=NULL,
            organization_revision=0 WHERE id=?""", (stage_id,))
    # Keep image files so database backups retain working attachments.


def stage_group_listing(conn, stage_id: int):
    return conn.execute(
        """
        SELECT c.name category_name,COALESCE(se.group_name,'Sem grupo') group_name,p.name,se.status,se.signup_order
        FROM stage_entries se
        JOIN categories c ON c.id=se.category_id
        JOIN pilots p ON p.id=se.pilot_id
        WHERE se.stage_id=?
        ORDER BY CASE c.name WHEN '90 KG' THEN 1 ELSE 2 END,COALESCE(se.group_name,'Z'),COALESCE(se.signup_order,9999),p.name COLLATE NOCASE
        """,
        (stage_id,),
    ).fetchall()

def add_developer_note(conn, stage_id: int, note: str, image_path: str = "") -> int:
    from datetime import datetime
    note = (note or "").strip()
    if not note and not image_path:
        raise ValueError("Digite uma observação ou anexe uma imagem antes de salvar.")
    created = local_now()
    nid = conn.execute("INSERT INTO developer_notes(stage_id,created_at,note,image_path) VALUES(?,?,?,?)", (stage_id, created, note, image_path)).lastrowid
    conn.commit()
    return nid


def developer_notes(conn, stage_id: int):
    return conn.execute("SELECT * FROM developer_notes WHERE stage_id=? ORDER BY id DESC", (stage_id,)).fetchall()


def clear_developer_notes(conn, stage_id: int) -> None:
    paths=[r['image_path'] for r in developer_notes(conn,stage_id) if r['image_path']]
    conn.execute("DELETE FROM developer_notes WHERE stage_id=?", (stage_id,))
    conn.commit()
    # Keep image files for database backup restoration.


def finalize_stage(conn, stage_id: int) -> None:
    if stage_row(conn, stage_id)["status"] != "Em andamento":
        raise ValueError("A etapa precisa estar em andamento.")
    if conn.execute("SELECT 1 FROM organization_settings WHERE stage_id=? AND confirmed_at IS NULL", (stage_id,)).fetchone():
        raise ValueError("Salve os grupos antes de finalizar a etapa.")
    expected = expected_batteries(conn, stage_id)
    if not expected:
        raise ValueError("Nenhuma bateria esperada foi encontrada. Defina pilotos e grupos primeiro.")
    pending = [b for b in expected if b["status"] != "Concluída"]
    if pending:
        first = pending[0]
        raise ValueError(
            f"Ainda existem {len(pending)} baterias não concluídas. Exemplo: {first['category_name']} - Grupo {first['group_name']}."
        )
    conn.execute("DELETE FROM stage_totals WHERE stage_id=?", (stage_id,))
    rows = conn.execute(
        """
        SELECT s.category_id,r.pilot_id,SUM(r.points) points
        FROM results r JOIN sessions s ON s.id=r.session_id
        WHERE s.stage_id=? AND s.status='Concluída'
        GROUP BY s.category_id,r.pilot_id
        """,
        (stage_id,),
    ).fetchall()
    for row in rows:
        conn.execute(
            "INSERT INTO stage_totals(stage_id,category_id,pilot_id,points) VALUES(?,?,?,?)",
            (stage_id, row["category_id"], row["pilot_id"], row["points"]),
        )
    from datetime import datetime
    ended = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    conn.execute("UPDATE stages SET status='Finalizada',ended_at=? WHERE id=?", (ended, stage_id))
    conn.commit()


# v1.5: stage snapshot, organization confirmation and planned sessions.
def local_now():
    from weather_service import local_time
    return local_time().strftime('%d/%m/%Y %H:%M:%S')


def backup_database(conn, label='manual'):
    folder = data_dir() / 'backups'
    folder.mkdir(exist_ok=True)
    path = folder / f'{label}_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
    with sqlite3.connect(path) as target:
        conn.backup(target)
    return path


def migrate_v15(conn):
    old_version = conn.execute('PRAGMA user_version').fetchone()[0]
    fields = {
        'stages': {'weather_forecast':'TEXT', 'weather_summary':'TEXT', 'weather_fetched_at':'TEXT',
                   'weather_status':"TEXT NOT NULL DEFAULT 'Não consultada'", 'weather_token':'TEXT',
                   'organization_revision':'INTEGER NOT NULL DEFAULT 0'},
        'developer_notes': {'updated_at':'TEXT'},
    }
    for table, columns in fields.items():
        existing = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
        for name, declaration in columns.items():
            if name not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS organization_settings (
            stage_id INTEGER NOT NULL REFERENCES stages(id),
            category_id INTEGER NOT NULL REFERENCES categories(id),
            capacity INTEGER NOT NULL DEFAULT 11 CHECK(capacity>0),
            confirmed_at TEXT, PRIMARY KEY(stage_id,category_id));
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY,
            stage_id INTEGER NOT NULL REFERENCES stages(id),
            category_id INTEGER NOT NULL REFERENCES categories(id),
            group_name TEXT NOT NULL,
            session_type TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            planned_start TEXT,
            duration INTEGER NOT NULL DEFAULT 15 CHECK(duration>0),
            gap INTEGER NOT NULL DEFAULT 5 CHECK(gap>=0),
            UNIQUE(stage_id,category_id,group_name,session_type));
        CREATE TRIGGER IF NOT EXISTS org_dirty_insert AFTER INSERT ON stage_entries BEGIN
            UPDATE organization_settings SET confirmed_at=NULL WHERE stage_id=NEW.stage_id AND category_id=NEW.category_id;
        END;
        CREATE TRIGGER IF NOT EXISTS org_dirty_update AFTER UPDATE OF group_name,status ON stage_entries BEGIN
            UPDATE organization_settings SET confirmed_at=NULL WHERE stage_id=NEW.stage_id AND category_id=NEW.category_id;
        END;
        CREATE TRIGGER IF NOT EXISTS org_dirty_delete AFTER DELETE ON stage_entries BEGIN
            UPDATE organization_settings SET confirmed_at=NULL WHERE stage_id=OLD.stage_id AND category_id=OLD.category_id;
        END;
    ''')
    conn.execute('INSERT OR IGNORE INTO organization_settings(stage_id,category_id) SELECT s.id,c.id FROM stages s CROSS JOIN categories c')
    if old_version < 15:
        # Preserve legacy live races: no invented stage-start forecast and no network calls.
        conn.execute("UPDATE organization_settings SET confirmed_at=? WHERE EXISTS (SELECT 1 FROM sessions s WHERE s.stage_id=organization_settings.stage_id AND s.category_id=organization_settings.category_id)", (local_now(),))
        conn.execute("UPDATE stages SET weather_status='Etapa iniciada na versão anterior; sem consulta no início' WHERE status<>'Programada'")
    else:
        conn.execute("UPDATE stages SET weather_status='Consulta interrompida; sem previsão salva' WHERE weather_status='Consultando'")
    conn.execute('PRAGMA user_version=15')
    conn.commit()


def store_stage_weather(conn, stage_id, token, forecast=None, error=None):
    """Guard by start token: a late worker cannot overwrite a reset/new stage."""
    from weather_service import compact_summary
    with conn:
        return conn.execute('''UPDATE stages SET weather_forecast=?,weather_summary=?,weather_fetched_at=?,weather_status=?
            WHERE id=? AND weather_token=? AND weather_status='Consultando' ''', (
            json.dumps(forecast,ensure_ascii=False) if forecast else None,
            compact_summary(forecast) if forecast else 'Previsão indisponível',
            forecast['fetched_at'] if forecast else local_now(),
            'Salva' if forecast else 'Falha na consulta: ' + str(error or 'sem dados')[:250], stage_id,token)).rowcount


def organization_limit(conn, stage_id, category_id):
    r=conn.execute('SELECT capacity FROM organization_settings WHERE stage_id=? AND category_id=?',(stage_id,category_id)).fetchone()
    return r['capacity'] if r else 11


def organization_confirmed(conn, stage_id, category_id):
    r=conn.execute('SELECT confirmed_at FROM organization_settings WHERE stage_id=? AND category_id=?',(stage_id,category_id)).fetchone()
    return bool(r and r['confirmed_at'])


def set_organization_limit(conn, stage_id, category_id, capacity):
    _ensure_category_editable(conn,stage_id,category_id)
    capacity=int(capacity)
    if not 1 <= capacity <= 99:
        raise ValueError('Use um limite de 1 a 99.')
    summary=organization_summary(conn,stage_id,category_id)
    if max(summary[g] for g in GROUP_NAMES)>capacity:
        raise ValueError('Retire os excedentes dos grupos antes de reduzir o limite.')
    with conn:
        conn.execute('UPDATE organization_settings SET capacity=?,confirmed_at=NULL WHERE stage_id=? AND category_id=?',(capacity,stage_id,category_id))


def confirm_groups(conn, stage_id):
    if stage_row(conn,stage_id)['status']=='Finalizada':
        raise ValueError('A etapa está finalizada.')
    editable=[c for c in categories(conn) if not category_has_started_session(conn,stage_id,c['id'])]
    for c in editable:
        summary=organization_summary(conn,stage_id,c['id'])
        if max(summary[g] for g in GROUP_NAMES)>organization_limit(conn,stage_id,c['id']):
            raise ValueError(f"{c['name']}: há grupo acima do limite. Ajuste a formação ou o limite.")
    if not expected_batteries(conn,stage_id):
        raise ValueError('Coloque pelo menos um piloto em um grupo.')
    with conn:
        for c in editable:
            # Includes legacy pending entries, even inactive pilots: none can block finalization.
            conn.execute("UPDATE stage_entries SET status='Não participa',group_name=NULL WHERE stage_id=? AND category_id=? AND (group_name IS NULL OR group_name='' OR status<>'Confirmado')",(stage_id,c['id']))
            conn.execute("""INSERT OR IGNORE INTO stage_entries(stage_id,category_id,pilot_id,status)
                SELECT ?,r.category_id,r.pilot_id,'Não participa' FROM registrations r WHERE r.category_id=?""",(stage_id,c['id']))
            conn.execute('UPDATE organization_settings SET confirmed_at=? WHERE stage_id=? AND category_id=?',(local_now(),stage_id,c['id']))
        conn.execute('UPDATE stages SET organization_revision=organization_revision+1 WHERE id=?',(stage_id,))
        expected=expected_batteries(conn,stage_id)
        order=conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM schedule WHERE stage_id=?',(stage_id,)).fetchone()[0]
        for b in expected:
            if b['session_type']=='SUPER_POLE':continue
            order+=1
            conn.execute('''INSERT OR IGNORE INTO schedule(stage_id,category_id,group_name,session_type,sort_order,duration)
                VALUES(?,?,?,?,?,?)''',(stage_id,b['category_id'],b['group_name'],b['session_type'],order,5 if b['session_type']=='SUPER_POLE' else 15))


def scheduled_sessions(conn, stage_id):
    return conn.execute('''SELECT q.*,c.name category_name,s.status,s.started_at,s.completed_at,
        (SELECT COUNT(*) FROM stage_entries e WHERE e.stage_id=q.stage_id AND e.category_id=q.category_id
          AND e.group_name=q.group_name AND e.status='Confirmado') pilots
        FROM schedule q JOIN categories c ON c.id=q.category_id
        LEFT JOIN sessions s ON s.stage_id=q.stage_id AND s.category_id=q.category_id
          AND s.group_name=q.group_name AND s.session_type=q.session_type
        WHERE q.stage_id=? ORDER BY q.sort_order,q.id''',(stage_id,)).fetchall()


def save_schedule(conn, stage_id, items):
    if stage_row(conn,stage_id)['status']=='Finalizada':
        raise ValueError('A etapa está finalizada.')
    current={r['id']:dict(r) for r in scheduled_sessions(conn,stage_id)}
    if len(items)!=len(current) or {i['id'] for i in items}!=set(current):
        raise ValueError('A formação mudou. Reabra a programação.')
    intervals=[]
    for i in items:
        old=current[i['id']]
        if old['status'] and any(i[k]!=old[k] for k in ('planned_start','duration','gap','sort_order')):
            raise ValueError('Não altere a programação de uma sessão já iniciada.')
        if not 1<=int(i['duration'])<=600 or not 0<=int(i['gap'])<=600:
            raise ValueError('Duração: 1 a 600 minutos; intervalo: 0 a 600.')
        if i['planned_start']:
            start=datetime.fromisoformat(i['planned_start'])
            intervals.append((start,start+timedelta(minutes=int(i['duration'])+int(i['gap'])),i['id']))
    intervals.sort()
    if any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])):
        raise ValueError('Há sobreposição de horários ou intervalos na pista.')
    with conn:
        for i in items:
            conn.execute('UPDATE schedule SET planned_start=?,duration=?,gap=?,sort_order=? WHERE id=? AND stage_id=?',
                (i['planned_start'],i['duration'],i['gap'],i['sort_order'],i['id'],stage_id))
        conn.execute('UPDATE stages SET organization_revision=organization_revision+1 WHERE id=?',(stage_id,))


def schedule_rest_warnings(conn, stage_id, minimum=15):
    last={}; warnings=[]
    rows=[r for r in scheduled_sessions(conn,stage_id) if r['planned_start']]
    for r in sorted(rows,key=lambda r:r['planned_start']):
        start=datetime.fromisoformat(r['planned_start'])
        for p in group_pilots(conn,stage_id,r['category_id'],r['group_name']):
            prev=last.get(p['id'])
            if prev and prev[1]!=r['category_id'] and (start-prev[0]).total_seconds()<minimum*60:
                warnings.append(f"{p['name']}: menos de {minimum} min entre categorias.")
            last[p['id']]=(start+timedelta(minutes=r['duration']),r['category_id'])
    return list(dict.fromkeys(warnings))


def update_developer_note(conn, stage_id, note_id, note, image_path=None):
    note=note.strip()
    old=conn.execute('SELECT image_path FROM developer_notes WHERE id=? AND stage_id=?',(note_id,stage_id)).fetchone()
    effective_image=(old['image_path'] if old else '') if image_path is None else image_path
    if not note and not effective_image:
        raise ValueError('Digite uma observação ou anexe uma imagem.')
    with conn:
        if not conn.execute('UPDATE developer_notes SET note=?,image_path=?,updated_at=? WHERE id=? AND stage_id=?',(note,effective_image,local_now(),note_id,stage_id)).rowcount:
            raise ValueError('Observação não encontrada.')


def save_result_batch(conn, session_id, rows):
    from scoring import recalculate_session
    sess=conn.execute('SELECT * FROM sessions WHERE id=?',(session_id,)).fetchone()
    if not sess or sess['status']!='Em andamento':raise ValueError('A bateria não está em andamento.')
    ids={r[0] for r in conn.execute('SELECT pilot_id FROM results WHERE session_id=?',(session_id,))}
    if {r['pilot_id'] for r in rows}!=ids:raise ValueError('A lista de resultados mudou. Reabra a bateria.')
    if sum(bool(r['fast']) for r in rows)>1:raise ValueError('Marque somente uma melhor volta.')
    with conn:
        for r in rows:
            conn.execute('UPDATE results SET position=?,fastest_manual=?,penalty=?,dq=? WHERE session_id=? AND pilot_id=?',
                (r['position'],int(r['fast']),int(r['penalty']),int(r['dq']),session_id,r['pilot_id']))
        recalculate_session(conn,session_id,commit=False)


def delete_developer_note(conn, stage_id, note_id):
    row=conn.execute('SELECT image_path FROM developer_notes WHERE stage_id=? AND id=?',(stage_id,note_id)).fetchone()
    with conn:
        if not conn.execute('DELETE FROM developer_notes WHERE stage_id=? AND id=?',(stage_id,note_id)).rowcount:
            raise ValueError('Observação não encontrada nesta etapa.')
    # Keep image files for database backup restoration.


def restore_all_available(conn, stage_id, category_id):
    _ensure_category_editable(conn,stage_id,category_id)
    with conn:
        conn.execute("UPDATE stage_entries SET status='Confirmado',group_name=NULL WHERE stage_id=? AND category_id=? AND status='Não participa'",(stage_id,category_id))


def plan_all_sessions(items, start, duration, gap):
    """Build a new plan; preserve started sessions and leave input unchanged on error."""
    duration=int(duration);gap=int(gap)
    if not 1<=duration<=600 or not 0<=gap<=600:
        raise ValueError('Duração: 1 a 600; intervalo: 0 a 600 minutos.')
    if not items:raise ValueError('Salve os grupos antes de preencher os horários.')
    if not any(not r['status'] for r in items):raise ValueError('Todas as sessões já foram iniciadas.')
    planned=[dict(r) for r in items]
    cursor=start
    # All future sessions start after the last reserved slot of a started session.
    for r in planned:
        if r['status'] and r['planned_start']:
            cursor=max(cursor,datetime.fromisoformat(r['planned_start'])+timedelta(minutes=r['duration']+r['gap']))
    for r in planned:
        if r['status']:continue
        r.update(planned_start=cursor.isoformat(timespec='minutes'),duration=duration,gap=gap)
        cursor+=timedelta(minutes=duration+gap)
    return planned


PROFILE_FIELDS=('number','whatsapp','cpf','city','state','email','birth_date','address','emergency_name','emergency_phone','notes')


def migrate_v17(conn):
    fields={r['name'] for r in conn.execute('PRAGMA table_info(pilots)')}
    if 'whatsapp' not in fields:
        backup_database(conn,'antes_v17')
    with conn:
        for field in PROFILE_FIELDS:
            if field not in fields:
                conn.execute(f"ALTER TABLE pilots ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")


def reset_groups(conn,stage_id,category_id):
    _ensure_category_editable(conn,stage_id,category_id)
    backup_database(conn,'antes_reset_grupos')
    with conn:
        conn.execute("UPDATE stage_entries SET group_name=NULL,status='Confirmado' WHERE stage_id=? AND category_id=?",(stage_id,category_id))
        conn.execute('DELETE FROM schedule WHERE stage_id=? AND category_id=?',(stage_id,category_id))
        conn.execute('UPDATE organization_settings SET confirmed_at=NULL WHERE stage_id=? AND category_id=?',(stage_id,category_id))
        conn.execute('UPDATE stages SET organization_revision=organization_revision+1 WHERE id=?',(stage_id,))


def save_pilot_profile(conn,pilot_id,name,status,profile,memberships,_commit=True):
    import re
    name=name.strip()
    if not name:raise ValueError('Digite o nome do piloto.')
    if status not in ('Ativo','Inativo'):raise ValueError('Status inválido.')
    old=conn.execute('SELECT * FROM pilots WHERE id=?',(pilot_id,)).fetchone() if pilot_id else None
    if pilot_id and not old:raise ValueError('Piloto não encontrado.')
    duplicate=find_pilot_by_name(conn,name)
    if duplicate and duplicate['id']!=pilot_id:raise ValueError('Já existe piloto com esse nome.')
    data={f:str(profile.get(f,old[f] if old else '')).strip() for f in PROFILE_FIELDS}
    if data['cpf']:
        cpf=re.sub(r'[.\-\s]','',data['cpf'])
        if not cpf.isdigit() or len(cpf)!=11 or len(set(cpf))==1:raise ValueError('CPF inválido.')
        for size in (9,10):
            digit=(sum(int(cpf[i])*(size+1-i) for i in range(size))*10)%11%10
            if digit!=int(cpf[size]):raise ValueError('CPF inválido: confira os dígitos.')
        data['cpf']=cpf
        found=conn.execute('SELECT id FROM pilots WHERE cpf=? AND id<>?',(cpf,pilot_id or -1)).fetchone()
        if found:raise ValueError('Este CPF já está cadastrado em outro piloto.')
    if data['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):raise ValueError('E-mail inválido.')
    if data['birth_date']:
        try:datetime.strptime(data['birth_date'],'%d/%m/%Y')
        except ValueError:raise ValueError('Nascimento: use dd/mm/aaaa.')
    data['state']=data['state'].upper()
    if data['state'] and data['state'] not in 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split():raise ValueError('UF inválida.')
    # Preflight every category change before saving any field.
    for cid,enabled in memberships.items():
        if not conn.execute('SELECT 1 FROM categories WHERE id=?',(cid,)).fetchone():raise ValueError('Categoria inválida.')
        reg=conn.execute('SELECT * FROM registrations WHERE pilot_id=? AND category_id=?',(pilot_id,cid)).fetchone()
        if reg and not enabled:
            history=conn.execute('SELECT 1 FROM stage_entries WHERE pilot_id=? AND category_id=? LIMIT 1',(pilot_id,cid)).fetchone()
            totals=conn.execute('SELECT 1 FROM stage_totals WHERE pilot_id=? AND category_id=? LIMIT 1',(pilot_id,cid)).fetchone()
            results=conn.execute('SELECT 1 FROM results r JOIN sessions s ON s.id=r.session_id WHERE r.pilot_id=? AND s.category_id=? LIMIT 1',(pilot_id,cid)).fetchone()
            if reg['initial_points'] or history or totals or results:raise ValueError('A categoria possui histórico e precisa ser preservada.')
    from contextlib import nullcontext
    with (conn if _commit else nullcontext()):
        if pilot_id:conn.execute('UPDATE pilots SET name=?,status=? WHERE id=?',(name,status,pilot_id))
        else:pilot_id=conn.execute('INSERT INTO pilots(name,status) VALUES(?,?)',(name,status)).lastrowid
        conn.execute('UPDATE pilots SET '+','.join(f+'=?' for f in PROFILE_FIELDS)+' WHERE id=?',tuple(data[f] for f in PROFILE_FIELDS)+(pilot_id,))
        for cid,enabled in memberships.items():
            if enabled:conn.execute('INSERT OR IGNORE INTO registrations(pilot_id,category_id) VALUES(?,?)',(pilot_id,cid))
            else:conn.execute('DELETE FROM registrations WHERE pilot_id=? AND category_id=?',(pilot_id,cid))
    return pilot_id


SEQUENCE_MODELS=('Intercalar 110/90 • A até J • por corrida',
                 'Intercalar 90/110 • A até J • por corrida',
                 '110 KG completa, depois 90 KG • por corrida',
                 '90 KG completa, depois 110 KG • por corrida',
                 'Por grupo • Corrida 1 e Corrida 2')


def migrate_v18(conn):
    # Only unstarted stages: never rewrite the program of a live/finished event.
    with conn:
        conn.execute("DELETE FROM schedule WHERE session_type='SUPER_POLE' AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.stage_id=schedule.stage_id)")


def reorder_schedule_items(items, ordered_ids):
    pending=[r for r in items if not r['status']]
    if len(ordered_ids)!=len(pending) or set(ordered_ids)!={r['id'] for r in pending}:
        raise ValueError('Inclua todas as corridas disponíveis uma única vez.')
    by_id={r['id']:r for r in pending};sequence=iter(ordered_ids);result=[]
    for original in items:
        if original['status']:result.append(dict(original));continue
        row=dict(by_id[next(sequence)])
        row['sort_order']=original['sort_order'];row['planned_start']=None
        result.append(row)
    return result


def preset_schedule_items(items,model):
    if model not in SEQUENCE_MODELS:raise ValueError('Modelo de sequência inválido.')
    def key(r):
        race={'SUPER_POLE':0,'RACE1':1,'RACE2':2}[r['session_type']]
        group=GROUP_NAMES.index(r['group_name']);cat=0 if r['category_name']=='110 KG' else 1
        if model==SEQUENCE_MODELS[0]:return race,group,cat
        if model==SEQUENCE_MODELS[1]:return race,group,-cat
        if model==SEQUENCE_MODELS[2]:return race,cat,group
        if model==SEQUENCE_MODELS[3]:return race,-cat,group
        return group,cat,race
    pending=sorted((r for r in items if not r['status']),key=key)
    return reorder_schedule_items(items,[r['id'] for r in pending])



def migrate_v20(conn):
    result_cols={r['name'] for r in conn.execute('PRAGMA table_info(results)')}
    pilot_cols={r['name'] for r in conn.execute('PRAGMA table_info(pilots)')}
    if 'best_lap_ms' not in result_cols:backup_database(conn,'antes_v20')
    with conn:
        if 'best_lap_ms' not in result_cols:conn.execute('ALTER TABLE results ADD COLUMN best_lap_ms INTEGER')
        if 'number' not in pilot_cols:conn.execute("ALTER TABLE pilots ADD COLUMN number TEXT NOT NULL DEFAULT ''")


def migrate_v21(conn):
    columns={r['name'] for r in conn.execute('PRAGMA table_info(developer_notes)')}
    with conn:
        if 'image_path' not in columns:
            conn.execute("ALTER TABLE developer_notes ADD COLUMN image_path TEXT NOT NULL DEFAULT ''")


def prepare_global_schedule(conn,stage_id,counts,start,interval,model):
    """Cria Corrida 1 e 2 das duas categorias, com uma largada a cada intervalo."""
    interval=int(interval)
    if not 1<=interval<=600:
        raise ValueError('O intervalo entre baterias deve ter de 1 a 600 minutos.')
    categories_rows=list(categories(conn))
    normalized={}
    for cat in categories_rows:
        count=int(counts.get(cat['id'],0))
        if not 1<=count<=10:
            raise ValueError(f"{cat['name']}: escolha de 1 a 10 grupos.")
        _ensure_category_editable(conn,stage_id,cat['id'])
        normalized[cat['id']]=count
        allowed=set(GROUP_NAMES[:count])
        occupied={g for g in GROUP_NAMES if group_pilots(conn,stage_id,cat['id'],g)}
        if not occupied<=allowed:
            raise ValueError(f"{cat['name']}: há pilotos em grupo acima da quantidade escolhida.")
    virtual=[];vid=-1
    for cat in categories_rows:
        for race in ('RACE1','RACE2'):
            for group in GROUP_NAMES[:normalized[cat['id']]]:
                virtual.append({'id':vid,'category_id':cat['id'],'category_name':cat['name'],
                                'group_name':group,'session_type':race,'status':None,
                                'sort_order':abs(vid),'planned_start':None,'duration':interval,'gap':0})
                vid-=1
    ordered=preset_schedule_items(virtual,model)
    cursor=start
    for row in ordered:
        row['planned_start']=cursor.isoformat(timespec='minutes')
        cursor+=timedelta(minutes=interval)
    with conn:
        conn.execute('DELETE FROM schedule WHERE stage_id=?',(stage_id,))
        for order,row in enumerate(ordered,1):
            conn.execute('''INSERT INTO schedule(stage_id,category_id,group_name,session_type,sort_order,
                             planned_start,duration,gap) VALUES(?,?,?,?,?,?,?,0)''',
                         (stage_id,row['category_id'],row['group_name'],row['session_type'],order,
                          row['planned_start'],interval))
        conn.execute('UPDATE stages SET organization_revision=organization_revision+1 WHERE id=?',(stage_id,))
    return len(ordered)


def prepare_category_schedule(conn,stage_id,category_id,count,start,duration,gap):
    _ensure_category_editable(conn,stage_id,category_id)
    count=int(count);duration=int(duration);gap=int(gap)
    if not 1<=count<=10:raise ValueError('Escolha de 1 a 10 grupos.')
    if not 1<=duration<=600 or not 0<=gap<=600:raise ValueError('Duração de 1 a 600 min; intervalo de 0 a 600 min.')
    selected=GROUP_NAMES[:count]
    occupied=[g for g in GROUP_NAMES if group_pilots(conn,stage_id,category_id,g)]
    if any(g not in selected for g in occupied):raise ValueError('Há pilotos nos grupos que seriam removidos da programação. Ajuste a quantidade ou os grupos.')
    # Build and check before changing any persisted schedule.
    slots=[];cursor=start
    for race in ('RACE1','RACE2'):
        for g in selected:
            slots.append((g,race,cursor.isoformat(timespec='minutes')))
            cursor+=timedelta(minutes=duration+gap)
    intervals=[(datetime.fromisoformat(r['planned_start']),datetime.fromisoformat(r['planned_start'])+timedelta(minutes=r['duration']+r['gap'])) for r in scheduled_sessions(conn,stage_id) if r['category_id']!=category_id and r['planned_start']]
    intervals += [(datetime.fromisoformat(t),datetime.fromisoformat(t)+timedelta(minutes=duration+gap)) for _,_,t in slots]
    intervals.sort()
    if any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])):raise ValueError('Os horários se sobrepõem a outra categoria. Ajuste o início ou use a organização global.')
    with conn:
        conn.execute('DELETE FROM schedule WHERE stage_id=? AND category_id=?',(stage_id,category_id))
        order=conn.execute('SELECT COALESCE(MAX(sort_order),0) FROM schedule WHERE stage_id=?',(stage_id,)).fetchone()[0]
        for i,(g,race,time) in enumerate(slots,1):
            conn.execute('INSERT INTO schedule(stage_id,category_id,group_name,session_type,sort_order,planned_start,duration,gap) VALUES(?,?,?,?,?,?,?,?)',(stage_id,category_id,g,race,order+i,time,duration,gap))
        conn.execute('UPDATE stages SET organization_revision=organization_revision+1 WHERE id=?',(stage_id,))


def remove_pilot(conn,pilot_id):
    if not conn.execute('SELECT 1 FROM pilots WHERE id=?',(pilot_id,)).fetchone():raise ValueError('Piloto não encontrado.')
    used=conn.execute('SELECT 1 FROM results WHERE pilot_id=? LIMIT 1',(pilot_id,)).fetchone()
    totals=conn.execute('SELECT 1 FROM stage_totals WHERE pilot_id=? LIMIT 1',(pilot_id,)).fetchone()
    initial=conn.execute('SELECT 1 FROM registrations WHERE pilot_id=? AND initial_points<>0 LIMIT 1',(pilot_id,)).fetchone()
    entries=conn.execute("SELECT 1 FROM stage_entries WHERE pilot_id=? AND group_name IS NOT NULL AND status='Confirmado' LIMIT 1",(pilot_id,)).fetchone()
    if used or totals or initial or entries:raise ValueError('Piloto com histórico, pontuação ou grupo. Use Inativo para preservar os dados.')
    with conn:conn.execute('DELETE FROM pilots WHERE id=?',(pilot_id,))


def save_single_result(conn,session_id,pilot_id,position,lap_ms,fastest,penalty,dq):
    session=conn.execute('SELECT * FROM sessions WHERE id=?',(session_id,)).fetchone()
    if not session or session['status']!='Em andamento':raise ValueError('Inicie ou reabra a sessão antes de editar.')
    if position is not None and position<=0:raise ValueError('Posição deve ser positiva.')
    if lap_ms is not None and lap_ms<=0:raise ValueError('Tempo deve ser maior que zero.')
    if not conn.execute('SELECT 1 FROM results WHERE session_id=? AND pilot_id=?',(session_id,pilot_id)).fetchone():raise ValueError('Piloto fora da sessão.')
    from scoring import recalculate_session
    with conn:
        if fastest:conn.execute('UPDATE results SET fastest_manual=0 WHERE session_id=?',(session_id,))
        conn.execute('UPDATE results SET position=?,best_lap_ms=?,fastest_manual=?,penalty=?,dq=? WHERE session_id=? AND pilot_id=?',(position,lap_ms,int(fastest and session['session_type']!='SUPER_POLE'),int(penalty),int(dq),session_id,pilot_id))
        recalculate_session(conn,session_id,commit=False)


def save_stage_details(conn,stage_id,name,date,location):
    datetime.strptime(date,'%d/%m/%Y')
    if not name.strip() or not location.strip():raise ValueError('Informe nome e local.')
    if stage_row(conn,stage_id)['status']!='Programada':raise ValueError('Edite os dados antes de iniciar a etapa.')
    with conn:conn.execute('UPDATE stages SET name=?,date=?,location=? WHERE id=?',(name.strip(),date,location.strip(),stage_id))
