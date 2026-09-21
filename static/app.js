const state = {
  boot: null,
  view: 'dashboard',
  heatRows: [],
  editingIndex: null,
  pilots: [],
  history: [],
  notes: [],
  activeStanding: null,
};

const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = (v='') => String(v).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

const raceLabels = {RACE1:'Corrida 1', RACE2:'Corrida 2', SUPER_POLE:'Super Pole'};
const statusLabels = {FINISHED:'Concluiu', DNF:'DNF', DNS:'DNS', DSQ:'DSQ'};

async function api(url, options={}) {
  const opts = {...options};
  opts.headers = {...(opts.headers||{})};
  if (opts.body && !(opts.body instanceof FormData)) opts.headers['Content-Type'] = 'application/json';
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = `Erro ${res.status}`;
    try { const data = await res.json(); msg = Array.isArray(data.detail)?'Confira os campos informados.':data.detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  const type = res.headers.get('content-type') || '';
  if (type.includes('application/json')) return res.json();
  return res;
}

function toast(message, error=false) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.toggle('error', error);
  el.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('show'), 3200);
}

function openModal(id){ $('#'+id).classList.add('open'); }
function closeModal(id){ $('#'+id).classList.remove('open'); }

function setView(view) {
  state.view = view;
  $$('.view').forEach(v => v.classList.toggle('active', v.id === `view-${view}`));
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  $$('.mobile-nav-item[data-go]').forEach(b => b.classList.toggle('active', b.dataset.go === view));
  const titles = {dashboard:'Dashboard', groups:'Grupos', calculator:'Baterias', pilots:'Pilotos', history:'Resultados', notes:'Notas do desenvolvedor', settings:'Configurações'};
  $('#pageTitle').textContent = titles[view] || 'CineCafe';
  $('#sidebar').classList.remove('open');
  document.body.classList.remove('menu-open');
  window.scrollTo({top:0,behavior:'smooth'});
  if (view === 'pilots') loadAllPilots();
  if (view === 'history') loadHistory();
  if (view === 'notes') loadNotes();
}

function initNav(){
  $$('.nav-item').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
  $$('[data-go]').forEach(b => b.addEventListener('click', () => setView(b.dataset.go)));
  $$('[data-close]').forEach(b => b.addEventListener('click', () => closeModal(b.dataset.close)));
  $$('.modal-backdrop').forEach(m => m.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); }));
  const toggleMenu = () => {
    const opening = !$('#sidebar').classList.contains('open');
    $('#sidebar').classList.toggle('open', opening);
    document.body.classList.toggle('menu-open', opening);
  };
  $('#mobileMenu').addEventListener('click', toggleMenu);
  $('#mobileMore')?.addEventListener('click', toggleMenu);
  $('#sidebarOverlay')?.addEventListener('click', () => { $('#sidebar').classList.remove('open'); document.body.classList.remove('menu-open'); });
}

async function loadBootstrap(){
  state.boot = await api('/api/bootstrap');
  const b = state.boot;
  $('#topStage').textContent = `${b.stage.name} • ${b.stage.date || 'sem data'}`;
  $('#heroStage').textContent = `${b.stage.name} • ${b.championship.name}`;
  $('#heroMeta').textContent = `${b.stage.location || 'Local não definido'} • ${b.stage.date || 'Data não definida'} • ${b.stage.status}`;
  $('#statPilots').textContent = b.counts.total;
  $('#statResults').textContent = b.history_count;
  $('#statCategories').textContent = b.categories.length;
  $('#statStatus').textContent = b.stage.status;
  $('#dataDir').textContent = b.data_dir;
  $('#stageName').value = b.stage.name || '';
  $('#stageDate').value = b.stage.date || '';
  $('#stageLocation').value = b.stage.location || '';

  fillSelect($('#heatCategory'), b.categories.map(c=>[c.name,c.name]));
  fillSelect($('#pilotCategoryFilter'), [['','Todas as categorias'], ...b.categories.map(c=>[c.name,c.name])]);
  fillSelect($('#heatGroup'), [...'ABCDEFGHIJ'].map(g=>[g,g]));
  fillSelect($('#heatEvent'), b.events.map(e=>[e,e]));
  fillSelect($('#historyEvent'), [['','Todos os eventos'], ...b.events.map(e=>[e,e])]);

  if (b.categories.length) {
    state.activeStanding = state.activeStanding || b.categories[0].name;
  }
  renderStandingTabs();
  renderStandings();
  renderSchedule();
  autoTitle();
  if(state.user?.role==='admin') await loadPilotPicker();
}

function fillSelect(select, entries){
  const current = select.value;
  select.innerHTML = entries.map(([v,l])=>`<option value="${esc(v)}">${esc(l)}</option>`).join('');
  if ([...select.options].some(o=>o.value===current)) select.value=current;
}

function renderStandingTabs(){
  const el = $('#standingsTabs');
  el.innerHTML = state.boot.categories.map(c=>`<button class="${c.name===state.activeStanding?'active':''}" data-cat="${esc(c.name)}">${esc(c.name)}</button>`).join('');
  $$('button', el).forEach(b=>b.addEventListener('click',()=>{state.activeStanding=b.dataset.cat;renderStandingTabs();renderStandings();}));
}

function renderStandings(){
  const rows = state.boot.standings[state.activeStanding] || [];
  $('#standingsBody').innerHTML = rows.length ? rows.map((r,i)=>`<tr><td data-label="Posição"><span class="rank ${i<3?'top':''}">${i+1}</span></td><td data-label="Piloto" class="pilot-name-cell">${esc(r.name)}</td><td data-label="Pontos" class="num points">${Number(r.total).toFixed(Number(r.total)%1?1:0)}</td></tr>`).join('') : `<tr><td colspan="3" class="muted">Sem classificação.</td></tr>`;
}

function renderSchedule(){
  const rows = state.boot.scheduled || [];
  $('#scheduleCount').textContent = `${rows.length} ${rows.length===1?'sessão':'sessões'}`;
  const root = $('#scheduleList');
  if (!rows.length) {
    root.innerHTML = `<div class="schedule-row"><div class="schedule-time">—</div><div class="schedule-name"><strong>Programação ainda não definida</strong><small>Organize os participantes em Grupos.</small></div><span class="schedule-status">Aguardando</span></div>`;
    return;
  }
  root.innerHTML = rows.map(r=>{
    let time='A definir';
    if(r.planned_start){ try{ time = new Date(r.planned_start).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}); }catch(_){} }
    return `<div class="schedule-row"><div class="schedule-time">${esc(time)}</div><div class="schedule-name"><strong>${esc(r.category_name)} • Grupo ${esc(r.group_name)}</strong><small>${esc(raceLabels[r.session_type]||r.session_type)}</small></div><span class="schedule-status">${esc(r.status||'Programada')}</span></div>`;
  }).join('');
}

function autoTitle(){
  const cat=$('#heatCategory').value, group=$('#heatGroup').value, race=raceLabels[$('#heatRace').value];
  $('#heatTitle').value = `${cat} • ${group} • ${race}`;
  $('#heatHeading').textContent = `${cat} • Grupo ${group} • ${race}`;
}

async function loadPilotPicker(){
  const q = encodeURIComponent($('#pilotSearch').value.trim());
  const category = encodeURIComponent($('#heatCategory').value);
  state.pilots = await api(`/api/pilots?q=${q}&category=${category}`);
  renderPilotPicker();
}

function renderPilotPicker(){
  const selected = new Set(state.heatRows.map(r=>r.pilot_id));
  const available = state.pilots.filter(p=>!selected.has(p.id));
  $('#availableCount').textContent = available.length;
  $('#pilotList').innerHTML = available.length ? available.map(p=>`<div class="pilot-item" data-pilot="${p.id}"><span>${esc(p.name)}</span><button title="Incluir">+</button></div>`).join('') : `<div class="muted" style="padding:15px 8px">Nenhum piloto disponível.</div>`;
  $$('.pilot-item').forEach(el=>el.addEventListener('click',()=>addPilotToHeat(Number(el.dataset.pilot))));
}

function addPilotToHeat(id){
  const p = state.pilots.find(x=>x.id===id);
  if(!p || state.heatRows.some(r=>r.pilot_id===id)) return;
  const usedPositions = state.heatRows.map(r=>Number(r.position)||0);
  state.heatRows.push({pilot_id:p.id,name:p.name,position:Math.max(0,...usedPositions)+1,status:'FINISHED',fast:false,penalty:false,dq:false,points:null});
  state.dirty=true;renderHeat(); renderPilotPicker();
}

function renderHeat(){
  const body=$('#heatBody');
  $('#heatEmpty').classList.toggle('hidden', state.heatRows.length>0);
  body.innerHTML = state.heatRows.map((r,i)=>{
    const st=(r.status||'FINISHED').toLowerCase();
    const points = r.points===null || r.points===undefined ? '—' : r.points;
    return `<tr>
      <td data-label="Posição"><span class="rank ${i<3?'top':''}">${r.position||'—'}</span></td>
      <td data-label="Piloto" class="pilot-name-cell mobile-primary">${esc(r.name)}</td>
      <td data-label="Situação"><span class="status-text ${st}">${esc(statusLabels[r.status]||r.status)}</span></td>
      <td data-label="Melhor volta">${r.fast?'<span class="yes-chip">+1</span>':'—'}</td>
      <td data-label="Punição">${r.penalty?'<span style="color:#ff7773;font-weight:900">−3</span>':'—'}</td>
      <td data-label="Pontos" class="num points">${esc(points)}</td>
      <td class="mobile-actions"><div class="row-actions"><button class="row-icon edit-row" data-i="${i}" title="Editar" aria-label="Editar ${esc(r.name)}">✎</button><button class="row-icon danger remove-row" data-i="${i}" title="Retirar" aria-label="Retirar ${esc(r.name)}">×</button></div></td>
    </tr>`;
  }).join('');
  $$('.edit-row').forEach(b=>b.addEventListener('click',()=>openResultEditor(Number(b.dataset.i))));
  $$('.remove-row').forEach(b=>b.addEventListener('click',()=>removeHeatRow(Number(b.dataset.i))));
}

function removeHeatRow(i){ state.dirty=true; state.heatRows.splice(i,1); normalizePositions(); renderHeat(); renderPilotPicker(); }
function normalizePositions(){ state.heatRows.forEach((r,i)=>{ if(r.status==='FINISHED') r.position=i+1; r.points=null; }); }

function openResultEditor(i){
  const r=state.heatRows[i]; state.editingIndex=i;
  $('#modalPilotName').textContent=r.name;
  $('#modalStatus').value=r.status||'FINISHED';
  $('#modalPosition').value=r.position??'';
  $('#modalFast').checked=!!r.fast;
  $('#modalPenalty').checked=!!r.penalty;
  $('#modalLap').value=r.best_lap_ms? (r.best_lap_ms/1000).toFixed(3):'';
  $('#modalSeconds').value=r.penalty_seconds||0;
  $('#modalDecision').value=r.decision||'';
  openModal('resultModal');
}

function confirmResult(){
  const i=state.editingIndex; if(i===null) return;
  const r=state.heatRows[i];
  const status=$('#modalStatus').value;
  const pos=$('#modalPosition').value.trim();
  r.status=status; r.position=pos?Number(pos):null; r.dq=status==='DSQ'; r.fast=$('#modalFast').checked && !['DNS','DSQ'].includes(status); r.penalty=$('#modalPenalty').checked; r.points=null;
  r.best_lap_ms=$('#modalLap').value?Math.round(Number($('#modalLap').value)*1000):null;
  r.penalty_seconds=Number($('#modalSeconds').value)||0;r.decision=$('#modalDecision').value.trim();state.dirty=true;
  closeModal('resultModal'); renderHeat();
}

function apiRows(){
  const dnfPoints=$('#dnfRule').value==='Pontuar posição';
  return state.heatRows.map(r=>({...r,dnf_points:dnfPoints,dq:r.status==='DSQ'}));
}

async function calculateHeat(showToast=true){
  const rows = await api('/api/calculate',{method:'POST',body:JSON.stringify({session_type:$('#heatRace').value,rows:apiRows()})});
  state.heatRows=rows; state.dirty=true;
  renderHeat();
  if(showToast) toast('Pontuação calculada com sucesso.');
  return rows;
}

async function saveHeat(){
  await calculateHeat(false);
  const payload=heatPayload();
  const result=await api('/api/save',{method:'POST',body:JSON.stringify(payload)});
  state.recordId=result.id; state.recordVersion=result.version; state.dirty=false;
  toast(`Resultado salvo • registro #${result.id}`);
  await loadBootstrap();
}

function heatPayload(){
  return {record_id:state.recordId||null,expected_version:state.recordVersion||null,title:$('#heatTitle').value.trim(),category:$('#heatCategory').value,group:$('#heatGroup').value,session_type:$('#heatRace').value,dnf_rule:$('#dnfRule').value,event_name:$('#heatEvent').value,rows:apiRows()};
}

function clearHeat(){
  if(state.heatRows.length && !confirm('Limpar os lançamentos atuais desta bateria?')) return;
  state.recordId=null;state.recordVersion=null;state.dirty=false;state.heatRows=[]; renderHeat(); loadPilotPicker();
}

async function pdfHeat(){
  await calculateHeat(false);
  const res=await fetch('/api/export/pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(heatPayload())});
  if(!res.ok){ let msg='Não foi possível gerar o PDF.'; try{msg=(await res.json()).detail||msg}catch(_){} throw new Error(msg); }
  const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a');a.href=url;a.download='resultado_bateria.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('PDF gerado.');
}

async function csvHeat(){
  await calculateHeat(false);
  const rows=[['Bateria','Categoria','Grupo','Corrida','Piloto','Posição','Situação','Melhor volta','Punição','Pontos']];
  state.heatRows.forEach(r=>rows.push([$('#heatTitle').value,$('#heatCategory').value,$('#heatGroup').value,raceLabels[$('#heatRace').value],r.name,r.position??'',statusLabels[r.status],r.fast?'Sim':'Não',r.penalty?'-3':'',r.points??'']));
  const csv='\ufeff'+rows.map(row=>row.map(v=>`"${String(v).replaceAll('"','""')}"`).join(';')).join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='resultado_bateria.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('CSV exportado.');
}

async function loadAllPilots(){
  const q=encodeURIComponent($('#allPilotSearch').value.trim()); const cat=encodeURIComponent($('#pilotCategoryFilter').value);
  const rows=await api(`/api/pilots?q=${q}&category=${cat}`);
  $('#allPilotsBody').innerHTML=rows.length?rows.map(p=>`<tr><td data-label="Piloto" class="pilot-name-cell mobile-primary">${esc(p.name)}</td><td data-label="Categorias"><div class="cat-tags">${(p.categories||[]).map(c=>`<span class="cat-tag">${esc(c)}</span>`).join('')||'—'}</div></td><td data-label="Status"><span class="badge ${p.status==='Ativo'?'active':'inactive'}">${esc(p.status)}</span></td></tr>`).join(''):`<tr><td colspan="3" class="muted">Nenhum piloto encontrado.</td></tr>`;
}

function openPilotModal(){ $('#newPilotName').value=''; openModal('pilotModal'); setTimeout(()=>$('#newPilotName').focus(),50); }
async function createPilot(){
  const name=$('#newPilotName').value.trim(); if(!name){toast('Informe o nome do piloto.',true);return;}
  await api('/api/pilots',{method:'POST',body:JSON.stringify({name,status:'Ativo'})}); closeModal('pilotModal'); toast('Piloto cadastrado.'); await loadBootstrap(); await loadAllPilots();
}

async function loadHistory(){
  const ev=encodeURIComponent($('#historyEvent').value||'');
  state.history=await api(`/api/history?event=${ev}`);
  $('#historySummary').textContent=`${state.history.length} ${state.history.length===1?'registro':'registros'}`;
  $('#historyBody').innerHTML=state.history.length?state.history.map(r=>`<tr><td data-label="Bateria" class="pilot-name-cell mobile-primary">${esc(r.title)}</td><td data-label="Categoria">${esc(r.category||'—')}</td><td data-label="Grupo">${esc(r.group_name||'—')}</td><td data-label="Sessão">${esc(raceLabels[r.session_type]||r.session_type)}</td><td data-label="Pilotos">${r.pilots}</td><td data-label="Salvo em">${esc(r.created_at)}</td><td class="mobile-actions"><button class="table-action open-history" data-id="${r.id}">Abrir</button> <button class="table-action danger delete-history" data-id="${r.id}">Excluir</button></td></tr>`).join(''):`<tr><td colspan="7" class="muted">Nenhum resultado salvo.</td></tr>`;
  $$('.open-history').forEach(b=>b.addEventListener('click',()=>openHistory(Number(b.dataset.id))));
  $$('.delete-history').forEach(b=>b.addEventListener('click',()=>deleteHistory(Number(b.dataset.id))));
}

async function openHistory(id){
  const r=await api(`/api/history/${id}`);
  state.recordId=r.id;state.recordVersion=r.version;state.dirty=false;
  $('#heatCategory').value=r.category||state.boot.categories[0]?.name||'';
  $('#heatGroup').value=r.group_name||'A';
  $('#heatRace').value=r.session_type;
  if([...$('#heatEvent').options].some(o=>o.value===(r.event_name||''))) $('#heatEvent').value=r.event_name;
  $('#heatTitle').value=r.title;
  $('#dnfRule').value=r.dnf_rule||'Zero pontos';
  state.heatRows=r.payload.map(x=>({...x,points:x.points??null}));
  $('#heatHeading').textContent=`${$('#heatCategory').value} • Grupo ${$('#heatGroup').value} • ${raceLabels[$('#heatRace').value]}`;
  await loadPilotPicker(); renderHeat(); setView('calculator'); toast('Resultado carregado para revisão.');
}

async function deleteHistory(id){
  if(!confirm('Excluir este resultado salvo? Um backup do banco será criado antes.')) return;
  await api(`/api/history/${id}`,{method:'DELETE'}); toast('Resultado excluído.'); await loadHistory(); await loadBootstrap();
}

async function loadNotes(){
  state.notes=await api('/api/notes');
  $('#notesList').innerHTML=state.notes.length?state.notes.map(n=>`<div class="note-row"><div><p>${esc(n.note).replaceAll('\n','<br>')}</p><small>${esc(n.created_at)}</small></div><button class="table-action danger note-delete" data-id="${n.id}">Excluir</button></div>`).join(''):`<div class="muted" style="padding:18px 2px">Nenhuma observação registrada.</div>`;
  $$('.note-delete').forEach(b=>b.addEventListener('click',()=>deleteNote(Number(b.dataset.id))));
}

async function saveNote(){
  const note=$('#noteText').value.trim(); if(!note){toast('Escreva a observação.',true);return;}
  await api('/api/notes',{method:'POST',body:JSON.stringify({note})}); $('#noteText').value='';toast('Observação salva.');await loadNotes();
}
async function deleteNote(id){ if(!confirm('Excluir esta observação?'))return; await api(`/api/notes/${id}`,{method:'DELETE'});toast('Observação excluída.');await loadNotes(); }

async function saveStage(){
  await api('/api/stage',{method:'PUT',body:JSON.stringify({name:$('#stageName').value.trim(),date:$('#stageDate').value.trim(),location:$('#stageLocation').value.trim()})}); toast('Dados da etapa atualizados.'); await loadBootstrap();
}

function bindEvents(){
  ['heatCategory','heatGroup','heatRace','heatEvent'].forEach(id=>$('#'+id).addEventListener('change',()=>loadGroupHeat().catch(e=>toast(e.message,true))));
  $('#pilotSearch').addEventListener('input',debounce(loadPilotPicker,180));
  $('#allPilotSearch').addEventListener('input',debounce(loadAllPilots,180));
  $('#pilotCategoryFilter').addEventListener('change',loadAllPilots);
  $('#historyEvent').addEventListener('change',loadHistory);
  $('#calcHeat').addEventListener('click',()=>calculateHeat().catch(e=>toast(e.message,true)));
  $('#saveHeat').addEventListener('click',()=>saveHeat().catch(e=>toast(e.message,true)));
  $('#clearHeat').addEventListener('click',clearHeat);
  $('#confirmResult').addEventListener('click',confirmResult);
  $('#pdfHeat').addEventListener('click',()=>pdfHeat().catch(e=>toast(e.message,true)));
  $('#csvHeat').addEventListener('click',()=>csvHeat().catch(e=>toast(e.message,true)));
  $('#newPilotBtn').addEventListener('click',openPilotModal);$('#addPilotTop').addEventListener('click',openPilotModal);$('#createPilot').addEventListener('click',()=>createPilot().catch(e=>toast(e.message,true)));
  $('#saveNote').addEventListener('click',()=>saveNote().catch(e=>toast(e.message,true)));
  $('#saveStage').addEventListener('click',()=>saveStage().catch(e=>toast(e.message,true)));
  $('#newPilotName').addEventListener('keydown',e=>{if(e.key==='Enter')createPilot().catch(err=>toast(err.message,true));});
}

function debounce(fn,ms){let t;return (...args)=>{clearTimeout(t);t=setTimeout(()=>Promise.resolve(fn(...args)).catch(e=>toast(e.message,true)),ms)}}

async function init(){
  initNav(); bindEvents();
  try{
    await loadBootstrap(); renderHeat();
  }catch(e){ toast(`Falha ao carregar: ${e.message}`,true); }
}


