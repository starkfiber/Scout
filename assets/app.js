const $ = id => document.getElementById(id);
const state = {path:new URLSearchParams(location.search).get('path')||'', items:[], selected:null, offset:0, total:0, sort:'name', desc:false, search:'', session:'', busy:false, wasIndexing:false, engine:'python'};
const theme=localStorage.getItem('scout-theme')==='dark'?'dark':'light';document.documentElement.dataset.theme=theme;$('theme-picker').value=theme;$('theme-picker').onchange=e=>{document.documentElement.dataset.theme=e.target.value;localStorage.setItem('scout-theme',e.target.value)};
const places = [
  ['Home',''], ['Downloads','Downloads'], ['Desktop','Desktop'],
  ['Documents','Documents'], ['Applications','Applications'],
  ['Codex','.codex'], ['Library','Library'], ['Android','.android']
];

function human(n){if(n===null||n===undefined)return '—';if(n===0)return '0 B';const units=['B','KiB','MiB','GiB','TiB'];let i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),4);return (n/1024**i).toFixed(i<2?0:1)+' '+units[i]}
function when(ms){return ms?new Date(ms).toLocaleString(undefined,{month:'short',day:'numeric',year:'numeric'}):'—'}
function fullPath(relative){return relative?window.scoutHome+'/'+relative:window.scoutHome}
async function api(url, options){const response=await fetch(url,{cache:'no-store',...options});const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data}
async function post(url, data){return api(url,{method:'POST',headers:{'Content-Type':'application/json','X-Scout-Session':state.session},body:JSON.stringify(data)})}
function notice(text){$('notice').textContent=text}
function setPlaces(){const box=$('places-list');box.replaceChildren();for(const [name,path] of places){const button=document.createElement('button');button.className='place'+(state.path===path?' active':'');button.type='button';button.innerHTML='<i aria-hidden="true"></i>';button.append(document.createTextNode(name));button.onclick=()=>navigate(path);box.append(button)}}
function crumbs(){const box=$('breadcrumbs');box.replaceChildren();const parts=state.path?state.path.split('/'):[];let current='';for(const [i,part] of ['Home',...parts].entries()){if(i){current+=(current?'/':'')+part;const sep=document.createElement('span');sep.className='separator';sep.textContent='›';box.append(sep)}const btn=document.createElement('button');btn.textContent=part;const target=current;btn.onclick=()=>navigate(target);box.append(btn)}}
function select(item){state.selected=item;$('detail-name').textContent=item?item.name:'Choose a file';$('detail-path').textContent=item?fullPath(item.path):'Select an item to see its path and metadata.';$('detail-kind').textContent=item?(item.kind==='folder'?'Folder':item.kind==='link'?'Symbolic link':'File'):'—';$('detail-size').textContent=item?human(item.allocated??item.bytes):'—';$('detail-time').textContent=item?when(item.modified):'—';$('preview-icon').textContent=item?(item.kind==='folder'?'▣':item.kind==='link'?'↗':'◇'):'◇';$('reveal').disabled=!item;$('copy-path').disabled=!item;document.querySelectorAll('.file-row').forEach(row=>row.classList.toggle('selected',item&&row.dataset.path===item.path))}
function addRows(items, reset=false){const tbody=$('files');if(reset)tbody.replaceChildren();for(const item of items){const tr=document.createElement('tr');tr.className='file-row';tr.dataset.path=item.path;tr.dataset.kind=item.kind;tr.tabIndex=0;tr.setAttribute('aria-label',`${item.kind} ${item.name}`);const name=document.createElement('td'),wrap=document.createElement('div'),glyph=document.createElement('span'),label=document.createElement('span');wrap.className='file-name';glyph.className='file-glyph';glyph.textContent=item.kind==='folder'?'▣':item.kind==='link'?'↗':'◇';label.textContent=item.name;wrap.append(glyph,label);name.append(wrap);const size=document.createElement('td');size.textContent=human(item.allocated??item.bytes);if(item.kind==='folder'&&item.allocated===null)size.title='Index this folder to measure its size';const modified=document.createElement('td');modified.textContent=when(item.modified);tr.append(name,size,modified);tr.onclick=()=>select(item);tr.ondblclick=()=>item.kind==='folder'&&navigate(item.path);tr.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();item.kind==='folder'?navigate(item.path):select(item)}};tbody.append(tr)}}
function updateStatus(){const shown=Math.min(state.items.length,state.total);$('list-status').textContent=state.search?`${state.total} indexed matches · coverage may be partial`:`${shown} of ${state.total} items · ${state.path||'Home'} · ${state.engine==='rf2-native-metadata'?'RF² native files + metadata':state.engine==='rf2-native'?'RF² native listing':state.engine==='python-fallback'?'Python fallback':'Python listing'}`;$('more').hidden=shown>=state.total}
function renderMosaic(){
  const box=$('mosaic');box.replaceChildren();
  const measured=state.items.filter(item=>Number.isFinite(item.allocated)&&item.allocated>0).sort((a,b)=>b.allocated-a.allocated);
  const missing=state.items.filter(item=>item.allocated===null).length;
  const partial=state.items.length<state.total;
  if(!measured.length){const empty=document.createElement('div');empty.className='map-empty';empty.textContent='No measured sizes here yet. Index this folder to reveal its capacity map.';box.append(empty);$('map-description').textContent='Index a folder to measure its contents. The map draws only entries with known allocated sizes.';return}
  const visible=measured.slice(0,12).map(item=>({item,size:item.allocated}));
  if(measured.length>12)visible.push({item:null,size:measured.slice(12).reduce((sum,item)=>sum+item.allocated,0),name:`${measured.length-12} more`});
  const colors=[['#3e7892','#25495f'],['#6668a4','#343d71'],['#8b728e','#514765'],['#558785','#2b595c'],['#967b5d','#5d513e']];
  function draw(entries,x,y,w,h,depth=0){
    if(!entries.length)return;
    if(entries.length===1){const entry=entries[0],item=entry.item;const tile=document.createElement(item?'button':'div');tile.className='map-tile'+(item?'':' other');if(item)tile.type='button';tile.style.left=x+'%';tile.style.top=y+'%';tile.style.width=w+'%';tile.style.height=h+'%';const color=colors[depth%colors.length];tile.style.setProperty('--tile-top',color[0]);tile.style.setProperty('--tile-bottom',color[1]);const name=document.createElement('strong'),size=document.createElement('small');name.textContent=item?item.name:entry.name;size.textContent=human(entry.size);tile.append(name,size);if(item){tile.title=`${item.name} · ${human(entry.size)} · ${item.kind==='folder'?'Open folder':'Inspect file'}`;tile.onclick=()=>item.kind==='folder'?navigate(item.path):(select(item),$('explorer').scrollIntoView({behavior:'smooth'}))}box.append(tile);return}
    const total=entries.reduce((sum,entry)=>sum+entry.size,0);let split=0,first=0;while(split<entries.length-1&&(first<total/2||split===0)){first+=entries[split].size;split++}const ratio=first/total;
    if(w>=h){draw(entries.slice(0,split),x,y,w*ratio,h,depth+1);draw(entries.slice(split),x+w*ratio,y,w*(1-ratio),h,depth+1)}
    else{draw(entries.slice(0,split),x,y,w,h*ratio,depth+1);draw(entries.slice(split),x,y+h*ratio,w,h*(1-ratio),depth+1)}
  }
  draw(visible,0,0,100,100);
  const caveat=[missing?`${missing} unmeasured entries excluded`:null,partial?`showing ${state.items.length} of ${state.total} loaded entries`:null].filter(Boolean).join(' · ');
  $('map-description').textContent=`${measured.length} measured ${measured.length===1?'entry':'entries'} in ${state.path||'Home'}. Tile area follows allocated size${caveat?'; '+caveat:''}. Select a tile to explore.`;
}
async function list(reset=true){try{if(reset){state.offset=0;state.items=[];select(null);$('files').replaceChildren()}notice('Reading folder…');const q=new URLSearchParams({path:state.path,offset:String(state.offset),limit:'120',sort:state.sort,desc:state.desc?'1':'0',kind:$('kind').value,hidden:$('hidden').checked?'1':'0'});const data=await api('/api/list?'+q);state.items.push(...data.entries);state.total=data.total;state.engine=data.engine;addRows(data.entries,reset);notice(data.engineError?`Native listing unavailable: ${data.engineError}. Python fallback active.`:data.total?'Double-click a folder to explore · Enter also works':'No items match these filters');updateStatus();setPlaces();crumbs();renderMosaic()}catch(e){notice(e.message);$('list-status').textContent='Folder unavailable'}}
async function navigate(path){state.path=path;state.search='';$('search').value='';await list(true);history.replaceState(null,'','#explorer')}
async function search(){const q=$('search').value.trim();state.search=q;if(q.length<2){list(true);return}try{notice('Searching local index…');const data=await api('/api/search?'+new URLSearchParams({q}));state.items=data.results;state.total=data.results.length;state.offset=0;select(null);$('files').replaceChildren();addRows(data.results,true);notice(data.coverage.running?`Indexing ${data.coverage.scope||'Home'}: ${data.coverage.seen} paths scanned. Results may grow.`:data.results.length?'Indexed results. Double-click folders to navigate.':'No indexed matches. Index a folder to make it searchable.');$('more').hidden=true;updateStatus()}catch(e){notice(e.message)}}
let searchTimer; $('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(search,160)});
for(const id of ['kind','hidden'])$(id).addEventListener('change',()=>state.search?search():list(true));
document.querySelectorAll('.sort').forEach(button=>button.onclick=()=>{const next=button.dataset.sort;state.desc=state.sort===next?!state.desc:next!=='name';state.sort=next;state.search?search():list(true)});
$('more').onclick=()=>{state.offset+=120;list(false)};
$('refresh').onclick=()=>{state.search?search():list(true);overview()};
$('index-button').onclick=async()=>{try{const result=await post('/api/index',{path:state.path});notice(result.running?`Indexing ${result.scope||'Home'} in the background…`:'Index starting…');$('index-button').disabled=true}catch(e){notice(e.message)}};
$('reveal').onclick=async()=>{if(!state.selected)return;try{await post('/api/reveal',{path:state.selected.path});notice('Revealed in Finder')}catch(e){notice(e.message)}};
$('copy-path').onclick=async()=>{if(!state.selected)return;try{await navigator.clipboard.writeText(fullPath(state.selected.path));notice('Path copied')}catch(e){notice('Clipboard permission unavailable')}};
$('explode-control').onclick=()=>{const on=$('board-stage').classList.toggle('exploded');$('explode-control').setAttribute('aria-pressed',String(on));$('explode-control').textContent=on?'↙ Reassemble':'↗ Separate layers'};
$('handles-button').onclick=async()=>{const box=$('handles-list');box.textContent='Inspecting open handles…';try{const data=await api('/api/handles');box.replaceChildren();if(!data.entries.length){box.innerHTML='<div class="empty">No matching open home files at this instant.</div>';return}for(const row of data.entries){const div=document.createElement('div'),path=document.createElement('span'),proc=document.createElement('span');div.className='handle';path.textContent=row.path;path.title=fullPath(row.path);proc.textContent=row.process;div.append(path,proc);box.append(div)}const small=document.createElement('p');small.className='fine';small.textContent=`Showing ${data.entries.length} of ${data.count} handles at ${new Date(data.at).toLocaleTimeString()}.`;box.prepend(small)}catch(e){box.textContent=e.message}};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('search').focus();$('search').select()}else if(e.key==='Escape'&&document.activeElement===$('search')){$('search').value='';list(true);$('search').blur()}else if(e.key==='Backspace'&&document.activeElement?.tagName!=='INPUT'&&document.activeElement?.tagName!=='TEXTAREA'){e.preventDefault();const parts=state.path.split('/');parts.pop();navigate(parts.join('/'))}});

async function overview(){
  try{
    const data=await api('/api/overview');
    state.session=data.session;window.scoutHome=data.home;
    const cap=data.capacity;
    $('total').textContent=human(cap.total);$('used').textContent=human(cap.used);
    $('free').textContent=human(cap.free);$('free-stat').textContent=human(cap.free);
    $('used-fill').style.width=100*cap.used/cap.total+'%';
    $('capacity-note').textContent='APFS volume · '+Math.round(100*cap.used/cap.total)+'% occupied';
    $('indexed').textContent=data.index.indexed.toLocaleString();
    const engine=data.index.engine||data.index.lastScan?.engine;
    const engineName=engine==='rf2-native-metadata'?'RF² native metadata':engine==='python-fallback'?'Python fallback':engine==='python'?'Python metadata':'engine unrecorded';
    const last=data.index.lastScan?` · last scan ${new Date(data.index.lastScan.ended).toLocaleString()}`:'';
    $('index-progress').textContent=data.index.running?`Scanning ${data.index.scope||'Home'} · ${data.index.seen.toLocaleString()} seen · ${engineName}`:data.index.error?'Index issue: '+data.index.error:data.index.indexed?`Local metadata index · ${engineName}${last} · coverage partial`:'Choose a folder to build the index';
    $('index-progress').title=data.index.engineError||'';
    $('index-button').disabled=data.index.running;
    if(state.wasIndexing&&!data.index.running&&!state.search)list(true);
    state.wasIndexing=data.index.running;
  }catch(e){$('capacity-note').textContent='Local service unavailable';notice(e.message)}
}
async function activity(){try{const data=await api('/api/activity');const samples=data.samples.filter(s=>typeof s.mbps==='number');if(!samples.length)return;const latest=samples.at(-1);$('mbps').textContent=latest.mbps.toFixed(1);$('board-rate').textContent=latest.mbps.toFixed(1)+' MB/s';$('board-stage').classList.toggle('active',latest.mbps>=1);$('board-stage').style.setProperty('--io-intensity',String(Math.min(1,latest.mbps/80)));const peak=Math.max(1,...samples.map(s=>s.mbps));$('chart-peak').textContent='PEAK '+peak.toFixed(1)+' MB/S';const W=900,H=160,pts=samples.map((s,i)=>[i*W/Math.max(samples.length-1,1),H-Math.min(1,s.mbps/(peak*1.08))*H]);const line=pts.map(p=>p.map(v=>v.toFixed(1)).join(' ')).join(' L');$('chart-line').setAttribute('d','M'+line);$('chart-area').setAttribute('d','M0 '+H+' L'+line+' L'+W+' '+H+' Z')}catch(_e){$('mbps').textContent='—'}}

overview().then(()=>list(true));activity();setInterval(overview,5000);setInterval(activity,3000);
