import {showStl} from './preview.js';
const $=id=>document.getElementById(id), sheet=$('sheet'), ctx=sheet.getContext('2d');
let state=null, picture=new Image(), mode='profile', points=[], pending=false;
const text=(id,value)=>{$(id).textContent=value;};
function status(message,error=false){text('status',message);$('status').classList.toggle('error',error);}
function busy(value){pending=value;for(const el of document.querySelectorAll('button,input,select'))el.disabled=value; if(!value)render();}
async function api(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'İşlem tamamlanamadı');return result;}
function selectOptions(id,items,chosen){const el=$(id);el.replaceChildren();for(const [value,label] of items){const opt=document.createElement('option');opt.value=value;opt.textContent=label;el.append(opt);}el.value=chosen??'';}
function render(){if(!state)return;$('controls').hidden=false;for(const id of ['pick-profile','pick-calibration','pick-hole'])$(id).disabled=pending;
 const d=state.decisions,o=state.options;selectOptions('profile',[['','Kontur seçin'],...o.profiles.map((p,i)=>[p.id,`${i+1} · ${p.kind==='circle'?'Daire':'Kapalı kontur'}`])],d.profile_id);
 const sel=o.profiles.find(p=>p.id===d.profile_id),fix=$('contour-fix');fix.replaceChildren();
 if(sel&&sel.contour&&sel.contour.ok===false){const lead=document.createElement('span');lead.className='hint';
  lead.textContent='Doğrulama bu konturu geçersiz buldu (çizimde işaretli). Sorunlu kenarı çıkarın; açık kalan ucu kapatmayı onaylayın:';fix.append(lead);
  const ids=[...new Set((sel.contour.issues||[]).flatMap(i=>i.ids||[]))];
  for(const id of ids){const drop=document.createElement('button');drop.className='secondary';drop.disabled=pending;drop.textContent=`${id} kenarını çıkar`;
   drop.onclick=()=>save({...d,contour:{...(d.contour||{}),drop:[...new Set([...((d.contour||{}).drop||[]),id])]}});fix.append(drop);}
  const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.disabled=pending;
  box.checked=!!((d.contour||{}).approve_join);
  box.onchange=()=>save({...d,contour:{...(d.contour||{}),approve_join:box.checked}});
  label.append(box,document.createTextNode(' Açık kalan ucu orta noktada kapatmayı onaylıyorum'));fix.append(label);}
 if(d.contour&&(d.contour.drop||[]).length){const note=document.createElement('span');note.className='hint';
  note.textContent=`Düzeltme kayıtlı: ${(d.contour.drop||[]).length} kenar çıkarıldı${d.contour.approve_join?', birleşim onaylı':''}. Üretim bunu yeniden denetleyecek.`;
  const clear=document.createElement('button');clear.className='secondary';clear.disabled=pending;clear.textContent='Düzeltmeyi temizle';
  clear.onclick=()=>save({...d,contour:{drop:[],approve_join:false}});fix.append(note,clear);}
 const measurement=$('measurement').value;selectOptions('measurement',[['','Ölçüyü ben gireceğim'],...o.measurements.map(m=>[m.id,`${m.text} (${m.unit})`])],measurement||d.calibration?.span_id);
 const selected=$('circle').value;selectOptions('circle',[['','Daire seçin'],...o.circles.map((c,i)=>[c.id,`Daire ${i+1}`])],selected);syncDepth();
 $('thickness').value=d.thickness??'';$('ack').checked=d.trace_acknowledged;if(d.calibration){points=[d.calibration.first,d.calibration.second];$('cal-value').value=d.calibration.value;$('cal-unit').value=d.calibration.unit;}
 updatePoints();$('questions').replaceChildren(...state.questions.map(q=>{const el=document.createElement('li');el.textContent=q;return el;}));
 $('features').replaceChildren(...d.holes.map(h=>{const row=document.createElement('div');row.className='feature';row.textContent=`${h.kind==='through'?'Delik':'Cep'} · Ø${h.diameter} mm${h.depth?` · ${h.depth} mm derinlik`:''}`;const b=document.createElement('button');b.className='secondary';b.textContent='Kaldır';b.onclick=()=>save({...d,holes:d.holes.filter(x=>x.circle_id!==h.circle_id)});row.append(b);return row;}));
 $('undo').disabled=pending||!state.can_undo;$('build').disabled=pending||state.questions.length>0;
 $('accept-all').hidden=!(state.proposals||[]).length;$('accept-all').disabled=pending;
 $('links').replaceChildren();for(const [key,label] of [['step','Taslak STEP'],['plan','CAD planı'],['audit','Geometri kontrolü']])if(state[key]){const a=document.createElement('a');a.href=state[key];a.textContent=label;a.download='';$('links').append(a);}
 if(!state.stl)$('preview').hidden=true;const klass=state.archetype&&state.archetype.class?` · sınıf: ${state.archetype.class}`:'';text('summary',`${o.profiles.length} kontur · ${o.circles.length} daire · ${o.measurements.length} ölçü adayı${klass} · kayıt ${state.revision}`);
 $('bind-start').disabled=pending||!state.decisions.profile_id;renderProposals();renderBindings();renderSketch();renderLog();setMode(mode);renderView();draw();}

const FIELD_LABEL={profile_id:'Dış kontur',calibration:'Ölçek',thickness:'Kalınlık',depth:'Cep derinliği'};
const CONFIDENCE_LABEL={bound:'okumaya bağlı',rule:'kural',assumed:'varsayım',model:'model önerisi'};
function describeValue(item){const v=item.value;
 if(item.field==='calibration')return `${v.value} ${v.unit} · ${v.span_id?`menü: ${v.span_id}`:'kaynak: okumanın kendi noktaları'}`;
 if(item.field==='profile_id')return `${v} · izlenen taslak`;
 if(item.field==='thickness'||item.field==='depth')return `${v} mm`;
 if(item.field.startsWith('hole:'))return `${v.kind==='through'?'geçişli delik':'kör cep'} · Ø${v.diameter} mm · ${v.circle_id}`;
 return JSON.stringify(v);}
function evidenceLine(item){const e=item.evidence||{},bits=[];
 if(e.text)bits.push(`basılı "${e.text}"`);if(e.span_id)bits.push(`okuma: ${e.span_id}`);if(e.rule)bits.push(`kural: ${e.rule}`);
 if(e.px!==undefined)bits.push(`${e.px} px`);if(e.px_per_mm)bits.push(`${e.px_per_mm} px/mm`);
 if(e.error_px!==undefined)bits.push(`${e.error_px} px sapma`);if(e.drawn_mm!==undefined)bits.push(`çizilen ${e.drawn_mm} mm`);
 if(e.width_mm!==undefined)bits.push(`kontur ${e.width_mm}×${e.height_mm} mm`);if(e.circles!==undefined)bits.push(`${e.circles} daire`);
 if(e.confirmed!==undefined)bits.push(e.confirmed?'geçişli doğrulandı':'geçişli doğrulanamadı');if(e.kind_source)bits.push(e.kind_source);
 if(e.thickness!==undefined)bits.push(`kalınlık ${e.thickness} mm`);if(e.value!==undefined&&e.unit)bits.push(`basılı ${e.value} ${e.unit}`);
 if(e.resolved_from)bits.push(e.resolved_from==='reading'?'okumanın kendi noktaları':'uzunluk kısıtıyla çözüldü');
 if(e.menu_id)bits.push(`menü: ${e.menu_id}`);if(e.geometry_mm)bits.push(e.geometry_mm);
 return bits.join(' · ');}
function renderProposals(){const box=$('proposals'),items=state.proposals||[];box.replaceChildren();
 if(!items.length){const p=document.createElement('p');p.className='muted';p.textContent='Bu çizim için öneri yok: okuma bir ölçü ya da özellik bağlayamadı. Aşağıdaki adımları elle tamamlayın.';box.append(p);return;}
 for(const item of items){const row=document.createElement('div');row.className='proposal';
  const head=document.createElement('div');const strong=document.createElement('strong');strong.textContent=FIELD_LABEL[item.field]||item.field;
  const badge=document.createElement('span');badge.className='badge';badge.textContent=CONFIDENCE_LABEL[item.confidence]||item.confidence;
  head.append(strong,badge);row.append(head);
  const value=document.createElement('div');value.textContent=describeValue(item);row.append(value);
  const ev=document.createElement('small');ev.textContent=evidenceLine(item);row.append(ev);
  if(item.alternatives&&item.alternatives.length){const alt=document.createElement('small');alt.textContent='Çizimdeki diğer basılı aday: '+item.alternatives.map(a=>`${a.text} (${a.value} mm)`).join(' · ');row.append(alt);}
  const b=document.createElement('button');b.className='secondary';b.textContent='Yalnız bunu onayla';b.disabled=pending;b.onclick=()=>accept([item.field],describeValue(item));row.append(b);
  box.append(row);}}
function renderLog(){const list=$('log');list.replaceChildren();
 for(const entry of (state.log||[]).slice().reverse()){const li=document.createElement('li');
  li.textContent=`${(entry.at||'').slice(11,19)} · ${entry.actor}/${entry.action} · ${entry.field}${entry.note?` — ${entry.note}`:''}`;
  if(entry.evidence){const d=document.createElement('details');const s=document.createElement('summary');s.textContent='kanıt';
   const code=document.createElement('code');code.textContent=Object.entries(entry.evidence).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join('\n');
   d.append(s,code);li.append(d);}list.append(li);}
 if(!list.children.length){const li=document.createElement('li');li.className='muted';li.textContent='Henüz adım yok.';list.append(li);}}
async function accept(fields,label){busy(true);try{state=await api('/api/guided/accept',{token:state.token,revision:state.revision,fields:fields||null});
 points=state.decisions.calibration?[state.decisions.calibration.first,state.decisions.calibration.second]:[];
 if(state.proposals&&!state.proposals.length)$('accept-all').hidden=true;
 status(fields?`Öneri onaylandı: ${label||fields.join(', ')}`:'Okumanın tüm önerileri sizin kararınız olarak kaydedildi.');
 render();if(state.stl)await showStl(state.stl,$('preview'));}
 catch(e){status(e.message,true);}finally{busy(false);}}
document.getElementById('accept-all').onclick=()=>accept(null);
function setMode(value){mode=value;text('mode',mode==='calibration'?'Bilinen ölçünün iki ucuna tıklayın. Yakın uçlar ve daire merkezlerine yakalanır.':mode==='bind'?'Bağlanacak iki uca tıklayın: seçilen konturun köşesi ya da bir dairenin merkezi. Değer yukarıdaki ölçü satırından ya da elle girilir.':mode==='hole'?'Çizimde bir daireye tıklayın; çapını ve türünü aşağıda belirtin.':'Dış konturun kenarına tıklayın veya listeden seçin.');$('bind-cancel').hidden=mode!=='bind';}
function updatePoints(){text('points',`${points.length}/2 nokta seçildi${points.length===2?` · çizimde ${Math.hypot(points[1][0]-points[0][0],points[1][1]-points[0][1]).toFixed(1)} piksel`:''}`);}
function scale(){return Math.min(sheet.width/picture.width,sheet.height/picture.height);}
function draw(){ctx.clearRect(0,0,sheet.width,sheet.height);if(!picture.width||!state)return;const s=scale();ctx.drawImage(picture,0,0,picture.width*s,picture.height*s);
 for(const p of state.options.profiles){ctx.beginPath();p.points.forEach((v,i)=>i?ctx.lineTo(v[0]*s,v[1]*s):ctx.moveTo(v[0]*s,v[1]*s));ctx.closePath();ctx.strokeStyle=p.id===state.decisions.profile_id?'#178a51':'#4e83a850';ctx.lineWidth=p.id===state.decisions.profile_id?3:1;ctx.stroke();}
 // The contour audit's own positions, marked where the drawing is wrong (PLAN §26.4-A): a ring and a
 // cross at every closure gap, crossing or overlap the selected boundary carries.
 const selected=state.options.profiles.find(item=>item.id===state.decisions.profile_id);
 if(selected&&selected.contour&&selected.contour.ok===false)for(const issue of (selected.contour.issues||[])){
   if(!issue.at)continue;const x=issue.at[0]*s,y=issue.at[1]*s;
   ctx.beginPath();ctx.arc(x,y,9,0,2*Math.PI);ctx.strokeStyle='#b4392b';ctx.lineWidth=2;ctx.stroke();
   ctx.beginPath();ctx.moveTo(x-6,y-6);ctx.lineTo(x+6,y+6);ctx.moveTo(x+6,y-6);ctx.lineTo(x-6,y+6);ctx.stroke();}
 const chosen=$('circle').value;for(const c of state.options.circles)if(c.id===chosen||state.decisions.holes.some(h=>h.circle_id===c.id)){ctx.beginPath();ctx.arc(c.center[0]*s,c.center[1]*s,c.radius*s,0,2*Math.PI);ctx.strokeStyle='#b56519';ctx.lineWidth=3;ctx.stroke();}
 for(const [i,p] of points.entries()){ctx.beginPath();ctx.arc(p[0]*s,p[1]*s,5,0,2*Math.PI);ctx.fillStyle='#b4392b';ctx.fill();ctx.fillText(String(i+1),p[0]*s+8,p[1]*s-8);}if(points.length===2){ctx.beginPath();ctx.moveTo(points[0][0]*s,points[0][1]*s);ctx.lineTo(points[1][0]*s,points[1][1]*s);ctx.strokeStyle='#b4392b';ctx.lineWidth=2;ctx.stroke();}
 for(const [i,end] of bindPoints.entries()){ctx.beginPath();ctx.arc(end.x*s,end.y*s,6,0,2*Math.PI);ctx.fillStyle='#265947';ctx.fill();ctx.fillText(String(i+1),end.x*s+8,end.y*s-8);}
 // PLAN §8.6: the sheet's own frame and axes, drawn so the user can check them before confirming.
 const frame=state.options.sheet_frame;if(frame&&frame.found&&(!$('view-show')||$('view-show').checked)){const r=frame.rect;ctx.save();ctx.setLineDash([7,5]);ctx.strokeStyle='#6b4fbb';ctx.lineWidth=2;ctx.strokeRect(r[0]*s,r[1]*s,(r[2]-r[0])*s,(r[3]-r[1])*s);ctx.setLineDash([]);const cx=(r[0]+r[2])/2*s,cy=(r[1]+r[3])/2*s;for(const [i,axis] of (frame.axes||[]).entries()){ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+axis.page[0]*70,cy+axis.page[1]*70);ctx.strokeStyle=i?'#6b4fbb':'#8a2be2';ctx.lineWidth=3;ctx.stroke();}ctx.restore();}}
function compass(v){if(!v||v.length!==2)return '?';const [x,y]=v;if(Math.abs(x)>=Math.abs(y))return x>0?'sağ':'sol';return y>0?'aşağı':'yukarı';}
function renderView(){const el=$('view-text');if(!el)return;const frame=state.options&&state.options.sheet_frame;const approved=state.decisions&&state.decisions.view;
 if(approved){el.textContent=`Onaylandı: X ${compass(approved.x_page)}, Y ${compass(approved.y_page)}${approved.frame_rect?` · çerçeve ${approved.frame_rect.map(n=>Math.round(n)).join(' / ')} px`:''} · kaynak ${approved.source}.`;return;}
 if(!frame){el.textContent='Görüş bilgisi bu okumada yok.';return;}
 const axes=frame.axes||[];const where=frame.found?`çerçeve ${frame.rect.map(n=>Math.round(n)).join(' / ')} px`:'çerçeve bulunamadı';
 el.textContent=`${where}; ${axes.length===2?`öneri: X ${compass(axes[0].page)}, Y ${compass(axes[1].page)}`:'eksen önerisi yok'} · ${frame.provenance||''}`;}
function distSegment(p,a,b){const x=b[0]-a[0],y=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*x+(p[1]-a[1])*y)/(x*x+y*y||1)));return Math.hypot(p[0]-a[0]-t*x,p[1]-a[1]-t*y);}
function holeAt(p,displayed){const far=c=>Math.hypot(p[0]-c.center[0],p[1]-c.center[1]);
 const rim=state.options.circles.map(c=>[Math.abs(far(c)-c.radius),c]).sort((a,b)=>a[0]-b[0])[0];
 if(rim&&rim[0]*displayed<18)return rim[1];
 // A pocket is drawn as one wide circle: clicking its middle is nowhere near its rim, so a click
 // *inside* a circle picks the smallest circle that contains it (a hole inside a pocket wins).
 return state.options.circles.filter(c=>far(c)<c.radius).sort((a,b)=>a.radius-b.radius)[0]||null;}
function syncDepth(){$('depth-label').hidden=$('hole-kind').value!=='pocket';$('hole-depth').disabled=$('hole-kind').value!=='pocket';if($('hole-kind').value!=='pocket')$('hole-depth').value='';}
let bindPoints=[];
function snapEnd(p,displayed){const profile=state.options.profiles.find(item=>item.id===state.decisions.profile_id);
 const candidates=[...state.options.circles.map(c=>({kind:'centre',id:c.id,x:c.center[0],y:c.center[1]})),
  ...(profile&&profile.edges||[]).flatMap((e,i)=>[{kind:'vertex',id:`${e.id}:start`,x:e.start[0],y:e.start[1],profile:state.decisions.profile_id,geometry_version:(state.geometry&&state.geometry.version)||null,end:'start'},{kind:'vertex',id:`${e.id}:end`,x:e.end[0],y:e.end[1],profile:state.decisions.profile_id,geometry_version:(state.geometry&&state.geometry.version)||null,end:'end'}])];
 let best=null,limit=16/displayed;for(const v of candidates){const d=Math.hypot(v.x-p[0],v.y-p[1]);if(d<limit){limit=d;best=v;}}return best;}
function renderBindings(){const box=$('bindings'),rows=state.decisions.bindings||[];box.replaceChildren();
 for(const [index,row] of rows.entries()){const div=document.createElement('div');div.className='feature';
  const remove=document.createElement('button');remove.className='secondary';remove.textContent='Kaldır';
  remove.onclick=()=>save({...state.decisions,bindings:rows.filter((_,i)=>i!==index)});
  const label=document.createElement('span');
  const name=end=>end.kind==='centre'?end.id:`kontur ${end.id.replace('edge:','köşe ')}`;
  const meaning=row.axis?(row.axis.toUpperCase()+(row.direction===1?'+':'−')):'eksen soruldu';
  label.textContent=`${row.value} ${row.unit==='in'?'inç':'mm'} · ${meaning} · ${name(row.first)} ↔ ${name(row.second)}`;
  div.append(remove,label);box.append(div);}
 if(!rows.length){const hint=document.createElement('small');hint.textContent='Henüz bağ yok: ölçek yalnız iki noktalı kalibrasyondan geliyor.';box.append(hint);}}
function renderSketch(){const box=$('sketch'),s=state.sketch||{};box.replaceChildren();
 const line=(text,cls)=>{const p=document.createElement('p');if(cls)p.className=cls;p.textContent=text;box.append(p);};
 if(s.error){line(`Kesin eskiz çözülemedi: ${s.error}`);return;}
 if(!s.px_per_mm){line('Ölçek henüz yok: bilinen ölçüyü iki noktayla girin ya da basılı bir ölçüyü bağlayın.');return;}
 line(`Ölçek ${Number(s.px_per_mm).toFixed(4)} px/mm · ${s.source==='bindings'?`bağlanan ${s.bindings} basılı ölçüden en küçük karelerle çözüldü`:'iki noktalı kalibrasyondan (bağ yok)'}.`);
 for(const row of s.rows||[])line(`• basılı ${row.value_mm} mm · ölçek altında çizili ${row.drawn_mm} mm · sapma ${row.residual_mm>0?'+':''}${row.residual_mm} mm${row.span_id?` (okuma ${row.span_id})`:''}`);
 if(s.conflicts&&s.conflicts.length)line(`Çelişki: ${s.conflicts.length} bağ tek ölçekle uzlaşmıyor; üretim bunlar düzeltilene kadar beklemede.`);
 line(`Bağlanmayan: ${(s.unbound_circles||[]).length} daire, ${(s.unbound_edges||[]).length} kenar pikselden izlenen taslaktır (${s.profile_bound?'kontur kısmen bağlı':'kontur bağlı değil'}).`,'muted');
 if(s.contour&&s.contour.ok===false){line(`Kontur geçersiz: ${s.contour.issues.length} sorun — ${(s.contour.issues[0]||{}).message||''}`,'muted');}
 else if(s.open_contour_px!==null&&s.open_contour_px!==undefined)line(`Kontur kapanış hatası ${s.open_contour_px} piksel.`,'muted');
 // The applied correction, measured on its own (PLAN §26.3): how far the drawn edges had to move to close.
 if(s.applied_move_px!==null&&s.applied_move_px!==undefined&&s.applied_move_px>0){
  const moved_mm=s.px_per_mm?s.applied_move_px/s.px_per_mm:null;
  line(`Uçlar bu konturu kapatmak için en çok ${Number(s.applied_move_px).toFixed(2)} piksel${moved_mm!==null?` (≈${moved_mm.toFixed(2)} mm)`:''} kaydırıldı.`,'muted');}
 // What the user's own measured ties did to the geometry (PLAN §26.4-B): status, what is still free, and
 // which ties cannot both hold — the core's restriction notes are quoted, never smoothed over.
 if(s.solved_dimensions){const sol=s.solved_dimensions;
  const word=sol.status==='conflict'?'ÇELİŞKİ':sol.status==='unsupported'?'bu bağlar desteklenmiyor':'çözüldü';
  line(`Ölçü çözümü: ${word} · serbest koordinat ${sol.free??'—'} · uygulanan değişim ${sol.moved!=null?`${Number(sol.moved).toFixed(2)} px`:'—'}.`, sol.status==='conflict'?'':'muted');
  for(const note of sol.notes||[])line(`• ${note}`,'muted');
  for(const ids of sol.conflicts||[])line(`• çakışan bağlar: ${(ids||[]).join(', ')}`,'muted');}
}
sheet.onclick=async event=>{if(!state||pending)return;const rect=sheet.getBoundingClientRect(),s=scale(),displayed=rect.width/picture.width,p=[(event.clientX-rect.left)*sheet.width/rect.width/s,(event.clientY-rect.top)*sheet.height/rect.height/s];
 if(mode==='calibration'){const candidates=[...state.options.profiles.flatMap(p=>p.edges?.flatMap(e=>[e.start,e.end])||[]),...state.options.circles.map(c=>c.center)];let point=p,best=12/displayed;for(const v of candidates){const d=Math.hypot(v[0]-p[0],v[1]-p[1]);if(d<best){best=d;point=v;}}if(points.length===2)points=[];points.push(point);updatePoints();draw();}
 else if(mode==='hole'){const hit=holeAt(p,displayed);if(hit){$('circle').value=hit.id;fillDiameter();draw();}else status('Bu noktada daire yok: bir dairenin kenarına ya da içine tıklayın.',true);}
 else if(mode==='bind'){const end=snapEnd(p,displayed);if(!end)return status('Bağ ucu seçilen konturun bir köşesine ya da bir daire merkezine yakın olmalı.',true);
  if(bindPoints.length===1&&bindPoints[0].id===end.id&&bindPoints[0].x===end.x&&bindPoints[0].y===end.y)return status('Aynı uca iki kez tıklandı; ikinci ucu seçin.',true);
  bindPoints.push(end);if(bindPoints.length<2){status('Bir uç seçildi; ikinci uca tıklayın.');draw();return;}
  const value=Number($('cal-value').value);if(!(value>0)){bindPoints=[];draw();return status('Bağlanacak basılı değeri girin ya da yukarıdaki ölçü satırını seçin.',true);}
  const axis=$('bind-axis').value,direction=Number($('bind-direction').value);
   if(!axis||!direction){status('Bağlanan ölçünün eksenini (X/Y) ve yönünü seçin; anlam sizin kararınız.',true);draw();return;}
   const used=new Set((state.decisions.bindings||[]).map(b=>b.id));let decisionId;do{decisionId='b'+Math.random().toString(36).slice(2,8);}while(used.has(decisionId));
   const binding={id:decisionId,value,unit:$('cal-unit').value,span_id:$('measurement').value||null,axis,direction,first:bindPoints[0],second:bindPoints[1]};bindPoints=[];
  save({...state.decisions,bindings:[...(state.decisions.bindings||[]),binding]});}
 else{let found=null,best=14/displayed;for(const profile of state.options.profiles)for(let i=0;i<profile.points.length;i++){const d=distSegment(p,profile.points[i],profile.points[(i+1)%profile.points.length]);if(d<best){best=d;found=profile.id;}}if(found)await save({...state.decisions,profile_id:found});}};
async function save(decisions){busy(true);try{state=await api('/api/guided/save',{token:state.token,revision:state.revision,decisions});status('Karar kaydedildi.');}catch(e){status(e.message,true);}finally{busy(false);}}
function fillDiameter(){const c=state.options.circles.find(c=>c.id===$('circle').value),cal=state.decisions.calibration;if(c&&cal){const ppm=Math.hypot(cal.second[0]-cal.first[0],cal.second[1]-cal.first[1])/(cal.value*(cal.unit==='in'?25.4:1));$('hole-diameter').value=(2*c.radius/ppm).toFixed(3);}draw();}
$('file').onchange=async event=>{const file=event.target.files[0];if(!file)return;busy(true);status('Çizim okunuyor ve konturlar hazırlanıyor…');try{const response=await fetch('/api/guided/open',{method:'POST',body:await file.arrayBuffer()});const result=await response.json();if(!response.ok)throw Error(result.error);state=result;points=[];history.replaceState({},'',`/guided?session=${state.token}`);await loadImage();status(state.proposals.length?`Okuma ${state.proposals.length} öneri getirdi; onaylayın ya da elle tamamlayın.`:state.questions.length?`Okuma öneri getirmedi; ${state.questions.length} alanı elle tamamlayın.`:'Dış konturu seçerek başlayın.');}catch(e){status(e.message,true);}finally{busy(false);}};
function loadImage(){return new Promise((resolve,reject)=>{picture=new Image();picture.onload=()=>{$('empty').hidden=true;sheet.hidden=false;sheet.height=Math.round(sheet.width*picture.height/picture.width);draw();resolve();};picture.onerror=()=>reject(Error('Çizim gösterilemedi'));picture.src=state.drawing;});}
$('pick-profile').onclick=()=>setMode('profile');$('pick-calibration').onclick=()=>{points=[];updatePoints();draw();setMode('calibration');};$('pick-hole').onclick=()=>setMode('hole');
$('bind-start').onclick=()=>{if(!state.decisions.profile_id)return status('Önce dış konturu seçin.',true);if(!(Number($('cal-value').value)>0))return status('Bağlanacak basılı değeri girin ya da yukarıdaki ölçü satırını seçin.',true);bindPoints=[];setMode('bind');draw();};
$('bind-cancel').onclick=()=>{bindPoints=[];setMode('profile');draw();};
$('profile').onchange=()=>save({...state.decisions,profile_id:$('profile').value||null});$('thickness').onchange=()=>save({...state.decisions,thickness:$('thickness').value?Number($('thickness').value):null});$('apply-thickness').onclick=()=>save({...state.decisions,thickness:$('thickness').value?Number($('thickness').value):null});$('ack').onchange=()=>save({...state.decisions,trace_acknowledged:$('ack').checked});
$('measurement').onchange=()=>{const m=state.options.measurements.find(m=>m.id===$('measurement').value);if(m){$('cal-value').value=m.value;$('cal-unit').value=m.unit;setMode('calibration');}};
$('view-confirm').onclick=()=>{const frame=state.options.sheet_frame;const axes=(frame&&frame.axes&&frame.axes.length===2)?frame.axes:[{page:[1,0]},{page:[0,-1]}];
 if(!$('view-ack').checked)return status('Önce eksen yönünü ve çerçeveyi onaylayın.',true);
 save({...state.decisions,view:{x_page:axes[0].page,y_page:axes[1].page,frame_rect:(frame&&frame.found)?frame.rect:null,source:(frame&&frame.found)?'sheet_frame':'page_axes',geometry_version:state.geometry&&state.geometry.version}});}
$('view-show').onchange=()=>draw();
$('apply-calibration').onclick=()=>{if(points.length!==2)return status('Önce çizimde ölçünün iki noktasını seçin.',true);save({...state.decisions,calibration:{first:points[0],second:points[1],value:Number($('cal-value').value),unit:$('cal-unit').value,span_id:$('measurement').value||null}});};
$('circle').onchange=fillDiameter;$('hole-kind').onchange=syncDepth;
$('add-hole').onclick=()=>{const h={circle_id:$('circle').value,kind:$('hole-kind').value,diameter:Number($('hole-diameter').value),depth:$('hole-kind').value==='pocket'?Number($('hole-depth').value):null};if(!h.circle_id)return status('Bir daire seçin.',true);save({...state.decisions,holes:[...state.decisions.holes.filter(x=>x.circle_id!==h.circle_id),h]});};
$('undo').onclick=async()=>{busy(true);try{state=await api('/api/guided/undo',{token:state.token,revision:state.revision});points=[];status('Son karar geri alındı.');}catch(e){status(e.message,true);}finally{busy(false);}};
$('build').onclick=async()=>{busy(true);status('Kararlardan 3B taslak hazırlanıyor; STEP yeniden açılarak kontrol ediliyor…');try{state=await api('/api/guided/build',{token:state.token,revision:state.revision});render();if(state.error)throw Error(state.error);if(state.stl)await showStl(state.stl,$('preview'));status('Taslak hazır. Geometrik kontrol tamam; çizimle ölçü doğruluğunu ayrıca inceleyin.');}catch(e){status(e.message,true);}finally{busy(false);}};
(async()=>{const token=new URLSearchParams(location.search).get('session');if(token){busy(true);try{const r=await fetch('/api/guided/'+token);const data=await r.json();if(!r.ok)throw Error(data.error);state=data;await loadImage();render();if(state.stl)await showStl(state.stl,$('preview'));status('Kaydedilmiş oturum açıldı.');}catch(e){status(e.message,true);}finally{busy(false);}}})().catch(()=>{});
