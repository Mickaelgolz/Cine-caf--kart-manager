from __future__ import annotations

SUPER_POLE_POINTS = {1: 11, 2: 10, 3: 9, 4: 8, 5: 7, 6: 6, 7: 5, 8: 4, 9: 3, 10: 2, 11: 1}
RACE_POINTS = {1: 18, 2: 15, 3: 13, 4: 11, 5: 9, 6: 7, 7: 5, 8: 4, 9: 3, 10: 2, 11: 1}
PENALTY_POINTS = 3


def _base_points(session_type: str, position) -> float:
    if position is None:
        return 0.0
    table = SUPER_POLE_POINTS if session_type == "SUPER_POLE" else RACE_POINTS
    return float(table.get(int(position), 0))


def recalculate_session(conn, session_id: int, commit=True) -> None:
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        return
    rows = conn.execute("SELECT * FROM results WHERE session_id=?", (session_id,)).fetchall()
    fastest_ids = [r["id"] for r in rows if r["fastest_manual"]]
    fastest_id = fastest_ids[0] if fastest_ids and session["session_type"] in ("RACE1", "RACE2") else None
    for r in rows:
        if r["dq"]:
            bonus = 0.0
            points = 0.0
        else:
            bonus = 1.0 if r["id"] == fastest_id else 0.0
            points = _base_points(session["session_type"], r["position"])
            if r["penalty"]:
                points -= PENALTY_POINTS
            points += bonus
        conn.execute("UPDATE results SET fastest_bonus=?,points=? WHERE id=?", (bonus, points, r["id"]))
    if commit:
        conn.commit()


def validate_and_finalize_session(conn, session_id: int) -> None:
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        raise ValueError("Bateria não encontrada.")
    if session["status"] != "Em andamento":
        raise ValueError("A bateria precisa estar em andamento.")
    rows = conn.execute("SELECT * FROM results WHERE session_id=?", (session_id,)).fetchall()
    if not rows:
        raise ValueError("A bateria não possui pilotos.")
    missing = [r for r in rows if r["position"] is None or int(r["position"]) <= 0]
    if missing:
        raise ValueError(f"A posição é obrigatória. Faltam {len(missing)} piloto(s).")
    positions = [int(r["position"]) for r in rows]
    if len(set(positions)) != len(positions):
        raise ValueError("Existem posições repetidas. Cada piloto deve possuir uma posição diferente.")
    fastest = [r for r in rows if r["fastest_manual"]]
    if len(fastest) > 1:
        raise ValueError("Somente um piloto pode ser marcado como melhor volta.")
    recalculate_session(conn, session_id)
    from database import local_now
    conn.execute("UPDATE sessions SET status='Concluída',completed_at=? WHERE id=?", (local_now(),session_id))
    conn.commit()
