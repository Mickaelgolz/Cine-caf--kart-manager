from pathlib import Path
import shutil, datetime, os, sys
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
CORE=ROOT/'core'
os.environ['CINECAFE_DATA_DIR']=str(DATA)
os.environ['CINECAFE_RELEASE_DIR']=str(CORE)
sys.path.insert(0,str(CORE))
import database as db
path=DATA/'apresentacao_v12.db'
if path.exists():
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=DATA/f'apresentacao_v12_backup_reparo_{stamp}.db'
    shutil.copy2(path,backup)
    print('Backup criado:', backup)
try:
    db.initialize_database()
    print('Banco verificado/reparado com sucesso.')
except Exception as exc:
    print('Falha no reparo:', type(exc).__name__, exc)
    print('O backup original foi preservado.')
