const guarded=fn=>(...args)=>Promise.resolve(fn(...args)).catch(e=>toast(e.message,true));
window.addEventListener('unhandledrejection',e=>{e.preventDefault();toast(e.reason?.message||'Não foi possível concluir a operação.',true)});
window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});
const originalView=setView;
setView=function(view){originalView(view);$('#summaryBox').hidden=true;if(view==='groups'){ $('#pageTitle').textContent='Grupos';loadGroups().catch(e=>toast(e.message,true));}};
const originalBootstrap=loadBootstrap;
loadBootstrap=async function(){await originalBootstrap();const b=state.boot;fillSelect($('#groupEvent'),b.events.map(e=>[e,e]));fillSelect($('#groupCategory'),b.categories.map(c=>[c.name,c.name]));fillSelect($('#groupName'),[...'ABCDEFGHIJ'].map(g=>[g,'Grupo '+g]));};
async function loadGroups(){
 const event=$('#groupEvent').value,cat=$('#groupCategory').value,g=$('#groupName').value;
 const [pilots,groups]=await Promise.all([api('/api/pilots'),api(`/api/groups?event=${encodeURIComponent(event)}&category=${encodeURIComponent(cat)}`)]);
 $('#groupCount').textContent=state.boot.categories.find(c=>c.name===cat)?.name+' • '+groups.filter(x=>x.group_name===g).length+' pilotos neste grupo';
 $('#groupPicker').innerHTML=pilots.map(p=>{const m=groups.find(x=>x.pilot_id===p.id);return `<label><input type="checkbox" value="${p.id}" ${m?.group_name===g?'checked':''}><span>${esc(p.name)}<small>${m?'Grupo '+esc(m.group_name):'Disponível'}</small></span></label>`}).join('');
}
async function saveGroup(){await api('/api/groups',{method:'PUT',body:JSON.stringify({event:$('#groupEvent').value,category:$('#groupCategory').value,group:$('#groupName').value,pilot_ids:$$('#groupPicker input:checked').map(x=>Number(x.value))})});toast('Grupo salvo.');await loadGroups();}
async function loadGroupHeat(){
 if(state.dirty && !confirm('Substituir os lançamentos não salvos pela seleção atual?')){if(state.previousSelection)Object.entries(state.previousSelection).forEach(([id,v])=>$('#'+id).value=v);return;}
 state.recordId=null;state.recordVersion=null;state.dirty=false;autoTitle();
 const event=$('#heatEvent').value,cat=$('#heatCategory').value,g=$('#heatGroup').value,race=$('#heatRace').value;
 const records=await api(`/api/history?event=${encodeURIComponent(event)}`);
 const existing=records.find(r=>r.category===cat&&r.group_name===g&&r.session_type===race);
 if(existing){await openHistory(existing.id);return;}
 const members=await api(`/api/groups?event=${encodeURIComponent(event)}&category=${encodeURIComponent(cat)}`);
 state.heatRows=members.filter(p=>p.group_name===g).map((p,i)=>({pilot_id:p.pilot_id,name:p.name,position:i+1,status:'FINISHED',fast:false,penalty:false,points:null}));
 await loadPilotPicker();renderHeat();
}
loadAllPilots=async function(){
 const rows=await api(`/api/pilots?include_inactive=true&q=${encodeURIComponent($('#allPilotSearch').value)}&category=${encodeURIComponent($('#pilotCategoryFilter').value)}`);
 state.allPilots=rows;
 $('#allPilotsBody').innerHTML=rows.map(p=>`<tr data-id="${p.id}" title="Dois cliques para editar"><td data-label="Piloto" class="pilot-name-cell mobile-primary"><span>${esc(p.name)}</span> <button class="table-action edit-pilot" data-id="${p.id}">Editar</button></td><td data-label="Categorias"><div class="cat-tags">${(p.categories||[]).map(c=>`<span class="cat-tag">${esc(c)}</span>`).join('')||'—'}</div></td><td data-label="Status"><button class="badge ${p.status==='Ativo'?'active':'inactive'} toggle-pilot" data-id="${p.id}">${esc(p.status)}</button></td></tr>`).join('');
 $$('#allPilotsBody tr').forEach(el=>el.addEventListener('dblclick',()=>editPilot(Number(el.dataset.id))));
 $$('.edit-pilot').forEach(el=>el.addEventListener('click',()=>editPilot(Number(el.dataset.id))));
 $$('.toggle-pilot').forEach(el=>el.addEventListener('click',guarded(async()=>{const p=rows.find(x=>x.id===Number(el.dataset.id));await api('/api/pilots/'+p.id,{method:'PUT',body:JSON.stringify({...p,status:p.status==='Ativo'?'Inativo':'Ativo'})});await loadAllPilots();await loadPilotPicker();})));
};
openPilotModal=function(){state.editPilot=null;$('#pilotModal h3').textContent='Novo piloto';$('#createPilot').textContent='Cadastrar';$('#newPilotName').value='';['Number','Whatsapp','City','Cpf','State','Email','Birth_date','Address','Emergency_name','Emergency_phone','Notes'].forEach(k=>$('#pilot'+k).value='');$('#pilot90').checked=false;$('#pilot110').checked=false;openModal('pilotModal');$('#newPilotName').focus();};
function editPilot(id){const p=state.allPilots.find(x=>x.id===id);openPilotModal();state.editPilot=p;$('#pilotModal h3').textContent='Editar piloto';$('#createPilot').textContent='Salvar';$('#newPilotName').value=p.name;['Number','Whatsapp','City','Cpf','State','Email','Birth_date','Address','Emergency_name','Emergency_phone','Notes'].forEach(k=>$('#pilot'+k).value=p[k.toLowerCase()]||'');$('#pilot90').checked=p.categories.includes('90 KG');$('#pilot110').checked=p.categories.includes('110 KG');}
createPilot=async function(){const p={name:$('#newPilotName').value.trim(),status:state.editPilot?.status||'Ativo',categories:[]};['Number','Whatsapp','City','Cpf','State','Email','Birth_date','Address','Emergency_name','Emergency_phone','Notes'].forEach(k=>p[k.toLowerCase()]=$('#pilot'+k).value.trim());if($('#pilot90').checked)p.categories.push('90 KG');if($('#pilot110').checked)p.categories.push('110 KG');await api('/api/pilots'+(state.editPilot?'/'+state.editPilot.id:''),{method:state.editPilot?'PUT':'POST',body:JSON.stringify(p)});closeModal('pilotModal');await loadBootstrap();await loadAllPilots();toast('Cadastro salvo.');};
async function refreshWeather(){
 $('#weather').textContent='Consultando condições…';
 try{const w=await api('/api/weather');if(!w.available){$('#weather').textContent=w.message;return;}const c=w.current;$('#weather').innerHTML=`<div class="weather-temp">${esc(c.temperature_2m)}°C</div><strong>${esc(w.condition)}</strong><div class="weather-metrics"><div><small>Sensação térmica</small>${esc(c.apparent_temperature)}°C</div><div><small>Probabilidade de chuva</small>${esc(w.rain_probability)}%</div><div><small>Precipitação</small>${esc(c.precipitation)} mm</div><div><small>Vento / rajadas</small>${esc(c.wind_speed_10m)} / ${esc(c.wind_gusts_10m)} km/h</div></div><small>Atualização: ${esc(w.updated.replace('T',' '))} · Open-Meteo</small>`;}catch(e){$('#weather').textContent='Previsão meteorológica indisponível.';}
}
async function consolidate(){
 const event=$('#historyEvent').value;
 if(!event)throw Error('Selecione um único evento para consolidar.');
 const s=await api('/api/summary?event='+encodeURIComponent(event));
 const box=$('#summaryBox');box.hidden=false;
 box.innerHTML=`<span class="section-label gold">${s.official?'ETAPA COMPLETA':'RESULTADO PARCIAL'}</span><h2>${esc(s.event)}</h2>${s.missing.length?`<p class="notice">${s.missing.map(esc).join('<br>')}</p>`:''}<div class="table-wrap"><table class="summary-table"><thead><tr><th>Pos.</th><th>Categoria</th><th>Piloto</th><th>Super Pole</th><th>C1</th><th>C2</th><th>Total</th><th>Melhor volta</th></tr></thead><tbody>${s.rows.map(r=>`<tr><td data-label="Posição">${r.rank}</td><td data-label="Categoria">${esc(r.category)}</td><td data-label="Piloto" class="mobile-primary">${esc(r.name)}</td><td data-label="Super Pole">${r.SUPER_POLE}</td><td data-label="Corrida 1">${r.RACE1}</td><td data-label="Corrida 2">${r.RACE2}</td><td data-label="Total">${r.total}</td><td data-label="Melhor volta">${r.best_lap_ms?(r.best_lap_ms/1000).toFixed(3)+' s':'—'}</td></tr>`).join('')}</tbody></table></div>${s.official?`<a class="btn primary" href="/api/final/pdf?event=${encodeURIComponent(event)}" target="_blank">Baixar resultado final em PDF</a>`:'<p>Resolva as pendências para liberar o PDF final.</p>'}`;
 box.scrollIntoView({behavior:'smooth',block:'start'});
}
loadNotes=async function(){state.notes=await api('/api/notes');$('#notesList').innerHTML=state.notes.map(n=>`<div class="note-row ${n.resolved?'resolved':''}"><div><p>${esc(n.note).replaceAll('\n','<br>')}</p><small>${esc(n.created_at)} · ${n.resolved?'Resolvido':'Pendente'}</small></div><button class="table-action resolve-note" data-id="${n.id}">${n.resolved?'Reabrir':'Resolver'}</button></div>`).join('')||'<p class="muted">Nenhuma nota registrada.</p>';$$('.resolve-note').forEach(b=>b.addEventListener('click',guarded(async()=>{const n=state.notes.find(n=>n.id===Number(b.dataset.id));await api('/api/notes/'+n.id,{method:'PUT',body:JSON.stringify({resolved:!n.resolved})});await loadNotes();})));};
async function enter(user){
 state.user=user;document.body.classList.toggle('visitor',user.role!=='admin');$('#accessScreen').hidden=true;$('#userAvatar').textContent=user.name.slice(0,2).toUpperCase();$('#userAvatar').title=user.name;
 if(!state.initialized){await init();state.initialized=true;}else await loadBootstrap();
 refreshWeather();
}
document.addEventListener('DOMContentLoaded',async()=>{
 $('#accessForm').addEventListener('submit',async e=>{e.preventDefault();const button=$('button[type=submit]',e.target);button.disabled=true;try{const u=await api('/api/access',{method:'POST',body:JSON.stringify({name:$('#accessName').value,key:$('#accessKey').value})});await enter(u);}catch(err){$('#accessError').textContent=err.message;}finally{button.disabled=false;}});
 $('#logout').addEventListener('click',guarded(async()=>{if(state.dirty&&!confirm('Sair sem salvar a bateria?'))return;await api('/api/access',{method:'DELETE'});state.dirty=false;location.reload();}));
 ['heatCategory','heatGroup','heatRace','heatEvent'].forEach(id=>$('#'+id).addEventListener('focus',()=>{state.previousSelection=Object.fromEntries(['heatCategory','heatGroup','heatRace','heatEvent'].map(k=>[k,$('#'+k).value]));}));
 $('#newStage').addEventListener('click',guarded(async()=>{if(!confirm('Criar uma nova etapa com estes dados? A etapa anterior continuará no histórico.'))return;await api('/api/stages',{method:'POST',body:JSON.stringify({name:$('#stageName').value.trim(),date:$('#stageDate').value.trim(),location:$('#stageLocation').value.trim()})});state.recordId=null;state.recordVersion=null;state.heatRows=[];state.dirty=false;await loadBootstrap();['heatEvent','groupEvent','historyEvent'].forEach(id=>$('#'+id).value=state.boot.events[0]);renderHeat();toast('Nova etapa criada.');}));
 $('#saveGroup').addEventListener('click',guarded(saveGroup));['groupEvent','groupCategory','groupName'].forEach(id=>$('#'+id).addEventListener('change',guarded(loadGroups)));
 $('#refreshWeather').addEventListener('click',refreshWeather);$('#consolidate').addEventListener('click',guarded(consolidate));
 $('#saveLocation').addEventListener('click',guarded(async()=>{if(!$('#latitude').value||!$('#longitude').value)throw Error('Informe latitude e longitude.');await api('/api/weather/location',{method:'PUT',body:JSON.stringify({latitude:Number($('#latitude').value),longitude:Number($('#longitude').value)})});toast('Localização salva.');refreshWeather();}));
 $('#backup').addEventListener('click',guarded(async()=>{const res=await api('/api/backup',{method:'POST'});const url=URL.createObjectURL(await res.blob());const a=document.createElement('a');a.href=url;a.download='backup_cinecafe.db';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape')$$('.modal-backdrop.open').forEach(x=>x.classList.remove('open'));if(e.ctrlKey&&e.key==='s'&&state.user?.role==='admin'&&state.view==='calculator'){e.preventDefault();guarded(saveHeat)();}});
 try{const user=await api('/api/access');if(user.role)await enter(user);}catch(e){$('#accessError').textContent='Servidor indisponível. Tente novamente.';}
});
