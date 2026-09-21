"""Temporary public HTTPS tunnel; requires the local server to be running."""
from pathlib import Path
import os,re,sys,urllib.request,subprocess,platform
ROOT=Path(__file__).resolve().parent

def main():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=3) as r:
            if r.status!=200:raise OSError('Servidor indisponivel')
    except Exception:
        print('Abra INICIAR_WEB.bat primeiro e aguarde o site carregar.');return 1
    if os.name!='nt' or platform.machine().lower() not in ('amd64','x86_64'):
        print('Este atalho de compartilhamento foi preparado para Windows x64.');return 1
    tool=ROOT/'tools/cloudflared.exe';tool.parent.mkdir(exist_ok=True)
    if not tool.exists():
        print('Baixando Cloudflare Tunnel do repositorio oficial...')
        part=tool.with_suffix('.download')
        try:
            with urllib.request.urlopen('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe',timeout=120) as response,part.open('wb') as f:
                while chunk:=response.read(1024*1024):f.write(chunk)
            if part.stat().st_size<1000000:raise OSError('Download incompleto')
            part.replace(tool)
        except Exception as e:
            part.unlink(missing_ok=True)
            print('Nao foi possivel baixar o compartilhador. Confira a internet. Detalhe:',e);return 1
    linkfile=ROOT/'LINK_PARA_COMPARTILHAR.txt'
    linkfile.write_text('Aguardando geracao do novo link.\n',encoding='utf-8')
    print('Mantenha esta janela e a janela do servidor abertas. Ctrl+C encerra o acesso externo.')
    process=subprocess.Popen([str(tool),'tunnel','--url','http://127.0.0.1:8765','--no-autoupdate'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    try:
        for line in process.stdout:
            print(line.rstrip())
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
            if match:
                link=match.group(0);linkfile.write_text(link+'\n',encoding='utf-8')
                print('\nLINK PARA COMPARTILHAR: '+link+'\nSalvo em LINK_PARA_COMPARTILHAR.txt\n')
        return process.wait()
    except KeyboardInterrupt:
        process.terminate();process.wait(timeout=15);return 0
    finally:
        if process.poll() is None:process.terminate()
        linkfile.write_text('Compartilhamento encerrado. Execute COMPARTILHAR.bat para gerar um novo link.\n',encoding='utf-8')

if __name__=='__main__':sys.exit(main())
