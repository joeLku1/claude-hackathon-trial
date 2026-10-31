'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const TYPES = [['bar','▥','Bar'],['line','⌁','Line'],['area','◩','Area'],['horizontal','▤','Horizontal'],['stacked','▦','Stacked'],['scatter','⠭','Scatter'],['donut','◉','Donut']];
const THEMES = [
  {name:'Studio', bg:'#ffffff', fg:'#263348', grid:'#e7eaf0', colors:['#6260de','#19a894','#f0ad50','#e47492','#479ed1','#a778c4']},
  {name:'After hours', bg:'#192435', fg:'#e8edf5', grid:'#344257', colors:['#a39aff','#5cd6bd','#f2bd72','#f794b1','#7ec8ee','#d4a8ff']},
  {name:'Editorial', bg:'#faf5e9', fg:'#343c32', grid:'#e3ddce', colors:['#4f7462','#c98358','#a6ab79','#b297b4','#6e9699','#cfb977']},
  {name:'Candy shop', bg:'#fff8fb', fg:'#523957', grid:'#f1e0ec', colors:['#db73a4','#8b83d6','#65b9b5','#e9b16a','#9ab76b','#bc85c0']}
];
let project, values=[], errors={}, selected=[0,1], selectedNote=-1, history=[], future=[], timer, revision=0, imageUrl, drag=null;
const KEY='plotcraft.project.v1';
const copy = obj => JSON.parse(JSON.stringify(obj));
const ref = (r,c) => String.fromCharCode(65+c)+(r+1);
function notice(message=''){ $('notice').hidden=!message; $('notice').textContent=message; }
async function api(path, data){
  const response=await fetch(path, data===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(!response.ok){const error=await response.json();throw Error(error.error||'Request failed');}
  return response.json();
}
function checkpoint(){history.push(JSON.stringify(project));if(history.length>80)history.shift();future=[];updateUndo();}
function updateUndo(){$('undo').disabled=!history.length;$('redo').disabled=!future.length;}
function autosave(){try{localStorage.setItem(KEY,JSON.stringify(project));$('saveStatus').textContent='Saved in this browser';}catch{$('saveStatus').textContent='Save project to keep edits';}}
function changed({table=false,controls=false}={}){
  revision++;autosave();if(table)buildTable();if(controls)buildControls();syncTop();drawOverlays();
  $('renderStatus').textContent='Updating…';clearTimeout(timer);timer=setTimeout(renderChart,220);
}
function syncTop(){
  $('projectName').value=project.name;$('canvas').style.aspectRatio=`${project.chart.width}/${project.chart.height}`;
  $('canvasSize').value=`${project.chart.width},${project.chart.height}`;
  document.querySelectorAll('.chartType').forEach(b=>b.classList.toggle('active',b.dataset.type===project.chart.type));
  $('dataCount').textContent=`${project.cells.length} rows · ${project.headers.length-1} series`;
}
async function renderChart(){
  const mine=revision, start=performance.now();
  try{
    const result=await api('/api/render',{project});
    if(mine!==revision)return;
    values=result.values;errors=result.errors;refreshCells();
    if(Object.keys(errors).length){
      notice(Object.entries(errors).slice(0,6).map(([key,error])=>`${key}: ${error}`).join('\n'));
      $('renderStatus').textContent='Fix data errors · preview paused';$('export').disabled=true;return;
    }
    notice();$('export').disabled=false;
    const url=URL.createObjectURL(new Blob([result.svg],{type:'image/svg+xml'}));
    $('chartImage').src=url;if(imageUrl)URL.revokeObjectURL(imageUrl);imageUrl=url;
    $('emptyPreview').hidden=true;
    $('renderStatus').textContent=`Up to date · ${Math.round(performance.now()-start)} ms`;
    drawOverlays();
  }catch(error){if(mine===revision){notice(error.message);$('renderStatus').textContent='Preview paused';$('export').disabled=true;}}
}
function displayCell(r,c){
  const raw=project.cells[r][c], value=values[r]?.[c];
  if(errors[ref(r,c)])return '#ERROR';
  if(typeof value!=='number')return raw.startsWith('=') ? (value??raw) : raw;
  const style=project.cellStyles[ref(r,c)]?.format||'number';
  return new Intl.NumberFormat('en-US',style==='currency'?{style:'currency',currency:'USD'}:style==='percent'?{style:'percent',maximumFractionDigits:2}:style==='compact'?{notation:'compact',maximumFractionDigits:2}:{maximumFractionDigits:4}).format(value);
}
function buildTable(){
  const [r,c]=selected;selected=[Math.min(r,project.cells.length-1),Math.min(c,project.headers.length-1)];
  $('dataTable').innerHTML=`<thead><tr><th class="rowNumber">#</th>${project.headers.map((h,c)=>`<th><div class="headCell"><span class="letter">${String.fromCharCode(65+c)}</span><input data-header="${c}" aria-label="Column ${String.fromCharCode(65+c)} name" value="${esc(h)}" maxlength="60">${c>0&&project.headers.length>2?`<button data-delete-col="${c}" aria-label="Delete column ${String.fromCharCode(65+c)}">×</button>`:''}</div></th>`).join('')}</tr></thead><tbody>${project.cells.map((row,r)=>`<tr><td class="rowNumber">${r+1}${project.cells.length>1?`<button data-delete-row="${r}" aria-label="Delete row ${r+1}">×</button>`:''}</td>${row.map((v,c)=>`<td><input data-r="${r}" data-c="${c}" aria-label="Cell ${ref(r,c)}" maxlength="500"></td>`).join('')}</tr>`).join('')}</tbody>`;
  refreshCells();syncFormula();
}
function refreshCells(){
  document.querySelectorAll('#dataTable input[data-r]').forEach(input=>{
    const r=+input.dataset.r,c=+input.dataset.c,style=project.cellStyles[ref(r,c)]||{};
    if(document.activeElement!==input)input.value=displayCell(r,c);
    input.style.fontWeight=style.bold?'700':'400';input.parentElement.style.background=style.background||'';
    input.parentElement.classList.toggle('selected',r===selected[0]&&c===selected[1]);
    input.parentElement.classList.toggle('error',!!errors[ref(r,c)]);input.title=errors[ref(r,c)]||project.cells[r][c];
  });
}
function syncFormula(){
  const [r,c]=selected,style=project.cellStyles[ref(r,c)]||{};
  $('cellAddress').textContent=ref(r,c);$('formulaInput').value=project.cells[r][c];
  $('cellFormat').value=style.format||'number';$('cellBackground').value=style.background||'#ffffff';
  $('cellBold').style.background=style.bold?'#e6e3fb':'';
}
function setCell(r,c,value){if(project.cells[r][c]===value)return;checkpoint();project.cells[r][c]=value;errors={};changed();syncFormula();}
function cellStyle(key,value){checkpoint();const address=ref(...selected);project.cellStyles[address]={...(project.cellStyles[address]||{}),[key]:value};changed();refreshCells();syncFormula();}
function field(label,key,type='text',extra=''){
  const v=project.chart[key];
  if(type==='checkbox')return `<label class="field inline">${label}<input data-chart="${key}" type="checkbox" ${v?'checked':''}></label>`;
  if(type==='color')return `<label class="field inline">${label}<input data-chart="${key}" type="color" value="${v}"></label>`;
  return `<label class="field">${label}${type==='range'?`<span class="rangeValue">${v}</span>`:''}<input data-chart="${key}" type="${type}" value="${esc(v)}" ${extra}></label>`;
}
function selectField(label,key,items){return `<label class="field">${label}<select data-chart="${key}">${items.map(([v,l])=>`<option value="${v}" ${project.chart[key]===v?'selected':''}>${l}</option>`).join('')}</select></label>`;}
function section(title,body){return `<section class="controlSection"><h4>${title}</h4>${body}</section>`;}
function buildControls(){
  const c=project.chart;
  $('controls').innerHTML=
    section('The story',field('Title','title','text','maxlength="250"')+field('Subtitle','subtitle','text','maxlength="250"'))+
    section('Palette & paper',`<div class="swatches">${c.colors.map((color,i)=>`<input type="color" data-color="${i}" value="${color}" aria-label="Palette color ${i+1}">`).join('')}</div><br>`+field('Canvas','background','color')+field('Text & axes','foreground','color')+field('Grid lines','gridColor','color'))+
    section('Typography',selectField('Font family','font',[['DejaVu Sans','Modern sans'],['DejaVu Serif','Editorial serif'],['DejaVu Sans Mono','Technical mono']])+`<div class="controlGrid">${field('Title size','titleSize','number','min="12" max="44"')}${field('Text size','fontSize','number','min="8" max="24"')}</div>`)+
    section('Chart styling',field('Data labels','labels','checkbox')+field('Legend','legend','checkbox')+field('Grid','grid','checkbox')+field('Bar width','barWidth','range','min="0.1" max="0.95" step="0.05"')+field('Line weight','lineWidth','range','min="0.5" max="8" step="0.5"')+field('Point size','markerSize','range','min="0" max="16" step="1"')+field('Opacity','opacity','range','min="0.1" max="1" step="0.05"'))+
    section('Axes & numbers',field('X axis label','xlabel')+field('Y axis label','ylabel')+selectField('Number format','numberFormat',[['number','Number'],['currency','Currency ($)'],['percent','Percent'],['compact','Compact (1k)']])+field('Decimal places','decimals','number','min="0" max="4" step="1"')+field('Category rotation','rotation','range','min="-90" max="90" step="15"')+`<div class="controlGrid">${field('Value minimum','ymin','number','placeholder="Auto"')}${field('Value maximum','ymax','number','placeholder="Auto"')}</div>`)+
    section('Visible series',project.headers.slice(1).map((h,i)=>`<label class="field inline">${esc(h)}<input type="checkbox" data-series="${i+1}" ${c.series.includes(i+1)?'checked':''}></label>`).join('')+(c.type==='donut'?'<p class="muted">Donut uses the first selected series.</p>':''))+
    section('Plot position & size',field('Left','plotX','range','min="0.05" max="0.4" step="0.01"')+field('Top','plotY','range','min="0.18" max="0.4" step="0.01"')+field('Width','plotWidth','range','min="0.3" max="0.9" step="0.01"')+field('Height','plotHeight','range','min="0.2" max="0.65" step="0.01"'));
  buildNotes();
}
function buildNotes(){
  $('noteControls').innerHTML=project.annotations.length?project.annotations.map((n,i)=>`<div class="noteCard"><textarea data-note="${i}" data-key="text" aria-label="Annotation ${i+1} text" maxlength="200">${esc(n.text)}</textarea><div class="noteRow"><input type="color" data-note="${i}" data-key="color" value="${n.color}" aria-label="Annotation ${i+1} color"><input type="number" min="8" max="48" data-note="${i}" data-key="size" value="${n.size}" aria-label="Annotation ${i+1} size"><button data-bold-note="${i}" aria-pressed="${n.bold}" title="Bold annotation"><strong>B</strong></button><button data-remove-note="${i}" aria-label="Delete annotation ${i+1}">×</button></div></div>`).join(''):'<p class="muted">Add a note to tell the story behind the numbers.</p>';
}
function drawOverlays(){
  const scale=$('canvas').clientWidth/project.chart.width;
  $('overlays').innerHTML=project.annotations.map((n,i)=>`<button class="noteHandle ${selectedNote===i?'selected':''}" data-drag-note="${i}" aria-label="Move annotation ${i+1}: ${esc(n.text)}" style="left:${n.x*100}%;top:${n.y*100}%;font-size:${n.size*100/72*scale}px;font-family:${esc(project.chart.font)};font-weight:${n.bold?700:400}">${esc(n.text)||'Text'}</button>`).join('');
}
function restore(snapshot){project=JSON.parse(snapshot);values=[];errors={};selectedNote=-1;changed({table:true,controls:true});updateUndo();}
function undo(){if(history.length){future.push(JSON.stringify(project));restore(history.pop());}}
function redo(){if(future.length){history.push(JSON.stringify(project));restore(future.pop());}}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function safeName(){return project.name.replace(/[^a-z0-9_-]+/gi,'-').replace(/^-|-$/g,'')||'plotcraft';}
function saveProject(){download(new Blob([JSON.stringify(project,null,2)],{type:'application/json'}),safeName()+'.plotcraft.json');}
function wire(){
  $('chartTypes').innerHTML=TYPES.map(([type,icon,label])=>`<button class="chartType" data-type="${type}"><span>${icon}</span>${label}</button>`).join('');
  $('themes').innerHTML=THEMES.map((t,i)=>`<button class="theme" data-theme="${i}"><span>${t.name}</span>${t.colors.slice(0,4).map(c=>`<i style="background:${c}"></i>`).join('')}</button>`).join('');
  $('chartTypes').onclick=e=>{const b=e.target.closest('[data-type]');if(!b)return;checkpoint();project.chart.type=b.dataset.type;changed({controls:true});};
  $('themes').onclick=e=>{const b=e.target.closest('[data-theme]');if(!b)return;checkpoint();const t=THEMES[+b.dataset.theme];Object.assign(project.chart,{background:t.bg,foreground:t.fg,gridColor:t.grid,colors:[...t.colors]});project.annotations.forEach(n=>n.color=t.fg);changed({controls:true});};
  $('projectName').onchange=e=>{checkpoint();project.name=e.target.value;changed();};
  $('canvasSize').onchange=e=>{checkpoint();[project.chart.width,project.chart.height]=e.target.value.split(',').map(Number);changed();};
  $('controls').addEventListener('input',e=>{
    const key=e.target.dataset.chart;if(e.target.type==='range'&&key)e.target.previousElementSibling.textContent=e.target.value;
  });
  $('controls').addEventListener('change',e=>{
    const input=e.target,key=input.dataset.chart;
    if(key){
      if(!input.checkValidity()){input.reportValidity();return;}
      checkpoint();project.chart[key]=input.type==='checkbox'?input.checked:['number','range'].includes(input.type)?(input.value===''?'':Number(input.value)):input.value;
      const c=project.chart;
      if(key==='plotX'||key==='plotWidth'){c.plotWidth=Math.min(c.plotWidth,+(0.97-c.plotX).toFixed(2));}
      if(key==='plotY'||key==='plotHeight'){c.plotHeight=Math.min(c.plotHeight,+(0.88-c.plotY).toFixed(2));}
      changed({controls:key.startsWith('plot')});
    }else if(input.dataset.color!==undefined){checkpoint();project.chart.colors[+input.dataset.color]=input.value;changed();}
    else if(input.dataset.series!==undefined){
      const col=+input.dataset.series;
      if(!input.checked&&project.chart.series.length===1){input.checked=true;notice('Keep at least one visible series.');return;}
      checkpoint();project.chart.series=input.checked?[...project.chart.series,col].sort((a,b)=>a-b):project.chart.series.filter(x=>x!==col);changed();
    }
  });
  $('dataTable').addEventListener('focusin',e=>{const input=e.target;if(input.dataset.r!==undefined){selected=[+input.dataset.r,+input.dataset.c];input.value=project.cells[selected[0]][selected[1]];syncFormula();refreshCells();}});
  $('dataTable').addEventListener('focusout',()=>setTimeout(refreshCells,0));
  $('dataTable').addEventListener('change',e=>{const input=e.target;if(input.dataset.r!==undefined)setCell(+input.dataset.r,+input.dataset.c,input.value);else if(input.dataset.header!==undefined){checkpoint();project.headers[+input.dataset.header]=input.value;changed({controls:true});}});
  $('dataTable').addEventListener('click',e=>{
    const row=e.target.dataset.deleteRow,col=e.target.dataset.deleteCol;
    if(row!==undefined){if(!confirm('Delete this row? Formula references stay unchanged. You can undo this.'))return;checkpoint();project.cells.splice(+row,1);remapStyles('row',+row);values=[];errors={};changed({table:true});}
    if(col!==undefined){if(!confirm('Delete this series? Formula references stay unchanged. You can undo this.'))return;checkpoint();project.headers.splice(+col,1);project.cells.forEach(r=>r.splice(+col,1));remapStyles('col',+col);project.chart.series=project.chart.series.filter(c=>c!==+col).map(c=>c>+col?c-1:c);if(!project.chart.series.length)project.chart.series=[1];values=[];errors={};changed({table:true,controls:true});}
  });
  $('dataTable').addEventListener('paste',e=>{
    const input=e.target;if(input.dataset.r===undefined)return;
    const text=e.clipboardData.getData('text/plain');if(!/[\t\n]/.test(text))return;
    e.preventDefault();const rows=text.replace(/\r/g,'').replace(/\n$/,'').split('\n').map(r=>r.split('\t')),r=+input.dataset.r,c=+input.dataset.c;
    if(r+rows.length>200||c+Math.max(...rows.map(x=>x.length))>12||rows.some(row=>row.some(v=>v.length>500))){notice('Paste exceeds the 200-row, 12-column or 500-character cell limit.');return;}
    checkpoint();const cols=Math.max(project.headers.length,c+Math.max(...rows.map(x=>x.length)));
    while(project.headers.length<cols){project.headers.push('Series '+project.headers.length);project.chart.series.push(project.headers.length-1);project.cells.forEach(row=>row.push('0'));}
    while(project.cells.length<r+rows.length)project.cells.push(Array(cols).fill(''));
    rows.forEach((row,i)=>row.forEach((v,j)=>project.cells[r+i][c+j]=v));values=[];errors={};changed({table:true,controls:true});
  });
  $('formulaInput').onchange=e=>setCell(...selected,e.target.value);
  $('cellFormat').onchange=e=>cellStyle('format',e.target.value);
  $('cellBackground').onchange=e=>cellStyle('background',e.target.value);
  $('cellBold').onclick=()=>cellStyle('bold',!project.cellStyles[ref(...selected)]?.bold);
  $('addRow').onclick=()=>{if(project.cells.length>=200)return notice('Maximum 200 rows.');checkpoint();project.cells.push(project.headers.map((_,i)=>i?'0':'New'));changed({table:true});};
  $('addColumn').onclick=()=>{if(project.headers.length>=12)return notice('Maximum 12 columns.');checkpoint();project.headers.push('Series '+project.headers.length);project.cells.forEach(r=>r.push('0'));project.chart.series.push(project.headers.length-1);changed({table:true,controls:true});};
  $('addNote').onclick=()=>{if(project.annotations.length>=20)return notice('Maximum 20 text layers.');checkpoint();project.annotations.push({text:'Your insight here',x:.15,y:.35,size:18,color:project.chart.foreground,bold:true});selectedNote=project.annotations.length-1;changed({controls:true});};
  $('noteControls').onchange=e=>{const i=e.target.dataset.note,key=e.target.dataset.key;if(i===undefined)return;if(!e.target.checkValidity()){e.target.reportValidity();return;}checkpoint();project.annotations[+i][key]=key==='size'?+e.target.value:e.target.value;changed();};
  $('noteControls').onclick=e=>{const b=e.target.closest('button');if(!b)return;const remove=b.dataset.removeNote,bold=b.dataset.boldNote;if(remove!==undefined){checkpoint();project.annotations.splice(+remove,1);selectedNote=-1;changed({controls:true});}else if(bold!==undefined){checkpoint();project.annotations[+bold].bold=!project.annotations[+bold].bold;changed({controls:true});}};
  $('overlays').onpointerdown=e=>{const b=e.target.closest('[data-drag-note]');if(!b)return;e.preventDefault();const i=+b.dataset.dragNote;checkpoint();selectedNote=i;const bounds=$('canvas').getBoundingClientRect();drag={i,startX:e.clientX,startY:e.clientY,x:project.annotations[i].x,y:project.annotations[i].y,bounds,button:b};b.setPointerCapture(e.pointerId);};
  $('overlays').onpointermove=e=>{if(!drag)return;const n=project.annotations[drag.i];n.x=Math.max(0,Math.min(.95,drag.x+(e.clientX-drag.startX)/drag.bounds.width));n.y=Math.max(0,Math.min(.98,drag.y+(e.clientY-drag.startY)/drag.bounds.height));drag.button.style.left=n.x*100+'%';drag.button.style.top=n.y*100+'%';drag.button.style.background='#615ddd20';drag.button.style.color=n.color;};
  const finishDrag=()=>{if(drag){drag=null;changed();}};$('overlays').onpointerup=finishDrag;$('overlays').onpointercancel=finishDrag;
  $('overlays').onkeydown=e=>{const b=e.target.closest('[data-drag-note]');if(!b||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();checkpoint();const i=+b.dataset.dragNote,n=project.annotations[i],step=e.shiftKey?.02:.005;n.x=Math.max(0,Math.min(.95,n.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0)));n.y=Math.max(0,Math.min(.98,n.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)));changed();$('overlays').querySelector(`[data-drag-note="${i}"]`).focus();};
  $('undo').onclick=undo;$('redo').onclick=redo;$('saveProject').onclick=saveProject;
  $('export').onclick=async()=>{const format=$('exportFormat').value;$('export').disabled=true;try{const response=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project,format})});if(!response.ok)throw Error((await response.json()).error);download(await response.blob(),safeName()+'.'+format);}catch(e){notice(e.message);}finally{$('export').disabled=Object.keys(errors).length>0;}};
  $('openProject').onclick=()=>chooseFile('project');$('importCsv').onclick=()=>chooseFile('csv');
  $('exportCsv').onclick=()=>{const quote=v=>'"'+String(v).replace(/"/g,'""')+'"';download(new Blob([[project.headers,...project.cells].map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv'}),safeName()+'.csv');};
  $('reset').onclick=async()=>{if(!confirm('Replace the canvas with the sample? You can undo this.'))return;try{const p=await api('/api/default');checkpoint();restore(JSON.stringify(p));}catch(e){notice(e.message);}};
  $('help').onclick=()=>$('helpDialog').showModal();$('closeHelp').onclick=()=>$('helpDialog').close();
  document.addEventListener('keydown',e=>{if(!(e.ctrlKey||e.metaKey))return;if(e.key.toLowerCase()==='s'){e.preventDefault();saveProject();}if(e.key.toLowerCase()==='z'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();e.shiftKey?redo():undo();}});
  new ResizeObserver(()=>{if(!drag)drawOverlays();}).observe($('canvas'));
}
function remapStyles(axis,index){
  // Formula references intentionally remain literal after row/column deletion.
  const styles={};for(const [key,value] of Object.entries(project.cellStyles)){let c=key.charCodeAt(0)-65,r=+key.slice(1)-1;const n=axis==='row'?r:c;if(n===index)continue;if(n>index){if(axis==='row')r--;else c--;}styles[ref(r,c)]=value;}project.cellStyles=styles;
}
function chooseFile(kind){
  const input=$('fileInput');input.accept=kind==='csv'?'.csv,text/csv':'.json,application/json';input.value='';
  input.onchange=async()=>{const file=input.files[0];if(!file)return;if(file.size>900000)return notice('Choose a file smaller than 900 KB.');try{const text=await file.text();const p=await api(kind==='csv'?'/api/csv':'/api/validate',kind==='csv'?{csv:text}:JSON.parse(text));checkpoint();if(kind==='csv'){project.headers=p.headers;project.cells=p.cells;project.cellStyles={};project.chart.series=p.chart.series;restore(JSON.stringify(project));}else restore(JSON.stringify(p));}catch(e){notice('Could not open file: '+e.message);}};input.click();
}
async function init(){
  try{
    const sample=await api('/api/default');project=sample;
    let recovery='';try{const saved=localStorage.getItem(KEY);if(saved)project=await api('/api/validate',JSON.parse(saved));}catch{recovery='The previous browser draft could not be restored. The sample is loaded; open a saved project to recover your work.';}
    wire();syncTop();buildTable();buildControls();drawOverlays();updateUndo();await renderChart();if(recovery)notice(recovery);
  }catch(e){notice('Could not start Plotcraft: '+e.message);}
}
init();
