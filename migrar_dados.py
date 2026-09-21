from __future__ import annotations
from pathlib import Path
import shutil
from datetime import datetime
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox

ROOT = Path(__file__).resolve().parent
TARGET_DIR = ROOT / 'data'
TARGET = TARGET_DIR / 'apresentacao_v12.db'


def valid_sqlite(path: Path) -> bool:
    try:
        with sqlite3.connect(path) as conn:
            return conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    except Exception:
        return False


def main():
    root = tk.Tk(); root.withdraw()
    src = filedialog.askopenfilename(
        title='Selecione o banco do CineCafe atual',
        filetypes=[('Banco CineCafe', '*.db'), ('Todos os arquivos', '*.*')],
    )
    if not src:
        root.destroy(); return
    src = Path(src)
    if not valid_sqlite(src):
        messagebox.showerror('CineCafe Web', 'O arquivo escolhido não é um banco SQLite válido.', parent=root)
        root.destroy(); return
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        backup = TARGET_DIR / f'antes_migracao_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
        with sqlite3.connect(TARGET) as source, sqlite3.connect(backup) as dest: source.backup(dest)
    if src.resolve() == TARGET.resolve():
        messagebox.showinfo('CineCafe', 'Este já é o banco atual.', parent=root);root.destroy();return
    with sqlite3.connect(src) as source, sqlite3.connect(TARGET) as dest: source.backup(dest)
    messagebox.showinfo('CineCafe Web', 'Banco copiado com sucesso. Abra o CineCafe Web normalmente.', parent=root)
    root.destroy()


if __name__ == '__main__':
    main()
