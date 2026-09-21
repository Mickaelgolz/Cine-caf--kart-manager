from pathlib import Path
import threading,time,urllib.request,webbrowser,os,subprocess
import uvicorn
ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8765'
def open_browser():
    for _ in range(100):
        try:
            with urllib.request.urlopen(URL+'/api/health',timeout=1) as r:
                if r.status==200:break
        except Exception:time.sleep(.2)
    else:
        print('Servidor indisponivel. Veja data/cinecafe.log.');return
    candidates=[Path(os.environ.get(v,''))/r'Google/Chrome/Application/chrome.exe' for v in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA')]
    chrome=next((p for p in candidates if p.is_file()),None)
    if chrome:subprocess.Popen([str(chrome),URL])
    else:webbrowser.open(URL)
    key=ROOT/'data/CHAVE_ORGANIZADOR.txt'
    if os.name=='nt' and key.exists():os.startfile(key)
if __name__=='__main__':
    os.chdir(ROOT)
    threading.Thread(target=open_browser,daemon=True).start()
    print('CineCafe Kart Manager 3.2 Mobile | '+URL)
    print('Mantenha esta janela aberta. Para compartilhar, execute COMPARTILHAR.bat.')
    uvicorn.run('main:app',host='127.0.0.1',port=8765,proxy_headers=False,access_log=False)
