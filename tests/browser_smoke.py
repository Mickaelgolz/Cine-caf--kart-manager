import os,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
data=tempfile.mkdtemp(prefix='cinecafe-browser-')
env={**os.environ,'CINECAFE_DATA_DIR':data}
server=subprocess.Popen(['python','-m','uvicorn','main:app','--port','8876','--host','127.0.0.1'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(50):
  try:urllib.request.urlopen('http://127.0.0.1:8876/api/health');break
  except:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CINECAFE_BROWSER'),headless=True,args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],env=os.environ.copy())
  page=browser.new_page(viewport={'width':1440,'height':1100})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8876');page.locator('#accessName').fill('Mickael')
  page.locator('summary').click();page.locator('#accessKey').fill((Path(data)/'CHAVE_ORGANIZADOR.txt').read_text().strip());page.locator('#accessForm button').click()
  page.locator('#heroStage').filter(has_text='3ª').wait_for()
  page.screenshot(path=str(root/'docs/dashboard.png'),full_page=True)
  page.locator('[data-view=pilots]').click();page.locator('#allPilotsBody tr').first.wait_for()
  page.locator('#addPilotTop').click();page.locator('#newPilotName').fill('Piloto Navegador');page.locator('#pilot90').check();page.locator('#createPilot').click()
  page.locator('#allPilotSearch').fill('Piloto Navegador');page.locator('#allPilotsBody tr').filter(has_text='Piloto Navegador').wait_for()
  page.locator('.edit-pilot').click();page.locator('#newPilotName').fill('Piloto Navegador Editado');page.locator('#createPilot').click()
  page.locator('#pilotModal').wait_for(state='hidden')
  page.locator('[data-view=groups]').click();page.locator('#groupPicker label').filter(has_text='Piloto Navegador Editado').wait_for()
  page.locator('#groupName').select_option('J');page.wait_for_timeout(200)
  page.locator('#groupPicker label').filter(has_text='Piloto Navegador Editado').locator('input').check();page.locator('#saveGroup').click();page.wait_for_timeout(250)
  page.locator('[data-view=calculator]').click();page.locator('#heatGroup').select_option('J');page.locator('#heatBody').get_by_text('Piloto Navegador Editado',exact=True).wait_for()
  page.locator('#calcHeat').click();page.locator('#heatBody .points').filter(has_text='18').wait_for();page.locator('#saveHeat').click();page.wait_for_timeout(300)
  page.locator('[data-view=history]').click();page.locator('#historyBody tr').filter(has_text='J').wait_for();page.locator('.open-history').first.click();page.locator('#heatBody .points').filter(has_text='18').wait_for()
  page.locator('[data-view=dashboard]').click();page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500);page.screenshot(path=str(root/'docs/mobile.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow'
  assert not errors,errors
  # Independent viewer can access dashboard, cannot see editing controls.
  context=browser.new_context(viewport={'width':1280,'height':900});visitor=context.new_page();visitor.goto('http://127.0.0.1:8876');visitor.locator('#accessName').fill('Convidado Teste');visitor.locator('#accessForm button').click();visitor.locator('#heroStage').filter(has_text='3ª').wait_for();assert not visitor.locator('[data-view=pilots]').is_visible()
  print(json.dumps({'browser':'Chromium 153','errors':errors,'flows':['admin login','create pilot','edit pilot','group','calculate','save','reopen','mobile no overflow','visitor read only']}))
  browser.close()
finally:server.terminate();server.wait()
