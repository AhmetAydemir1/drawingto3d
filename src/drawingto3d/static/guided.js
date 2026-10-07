import {showStl} from './preview.js';
const $=id=>document.getElementById(id), sheet=$('sheet'), ctx=sheet.getContext('2d');
let state=null, picture=new Image(), mode='profile', points=[], pending=false;
// PLAN-21 §7.3: kaydedilmemiş metin taslakları burada durur — render, seçim değişimi veya başarısız
// bir kayıt onları silmez; karar sunucuya yazıldığında temizlenir.
let selectedCallout=null, calloutDrag=null, suppressClick=false, labelById={};
const drafts=new Map();
const text=(id,value)=>{$(id).textContent=value;};
function status(message,error=false){text('status',message);$('status').classList.toggle('error',error);}
function busy(value){pending=value;for(const el of document.querySelectorAll('button,input,select,textarea'))el.disabled=value; if(!value)render();}
async function api(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'İşlem tamamlanamadı');return result;}
function selectOptions(id,items,chosen){const el=$(id);el.replaceChildren();for(const [value,label] of items){const opt=document.createElement('option');opt.value=value;opt.textContent=label;el.append(opt);}el.value=chosen??'';}
function render(){if(!state)return;$('controls').hidden=false;for(const id of ['pick-profile','pick-calibration','pick-hole','pick-callout','draw-callout'])$(id).disabled=pending;
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
 $('bind-start').disabled=pending||!state.decisions.profile_id;renderProposals();renderBindings();renderSketch();renderLog();renderCallouts();setMode(mode);renderView();draw();}

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
const MODE_HINT={calibration:'Bilinen ölçünün iki ucuna tıklayın. Yakın uçlar ve daire merkezlerine yakalanır.',
 bind:'Bağlanacak iki uca tıklayın: seçilen konturun köşesi ya da bir dairenin merkezi. Değer yukarıdaki ölçü satırından ya da elle girilir.',
 hole:'Çizimde bir daireye tıklayın; çapını ve türünü aşağıda belirtin.',
 callout:'İncelenecek ölçü/not kutusuna tıklayın; listeden de seçebilirsiniz.',
 'callout-draw':'Yeni ölçü/not alanı için çizim üzerinde bir kutu sürükleyin. Escape iptal eder.',
 'callout-edit':'Alanı düzeltmek için çizim üzerinde yeni kutuyu sürükleyin. Escape iptal eder.',
 'target':'Gösterdiği yeri seçmek için çizimde daireye, yaya, köşeye ya da konturun içine tıklayın; çoklu seçimde hepsi birikir. Escape seçimi bırakır.'};
function setMode(value){mode=value;text('mode',MODE_HINT[mode]||'Dış konturun kenarına tıklayın veya listeden seçin.');$('bind-cancel').hidden=mode!=='bind';}
function updatePoints(){text('points',`${points.length}/2 nokta seçildi${points.length===2?` · çizimde ${Math.hypot(points[1][0]-points[0][0],points[1][1]-points[0][1]).toFixed(1)} piksel`:''}`);}
function scale(){return Math.min(sheet.width/picture.width,sheet.height/picture.height);}
// PLAN-21 §7.2: tek koordinat dönüşümü. Canvas backing boyutu ile CSS boyutu ayrı olabilir, bu yüzden
// client koordinatı doğrudan görüntü pikseli sayılmaz. Seçim, hit-test, sürükleme ve crop aynı
// yardımcıları kullanır; görüntü yüklenmeden seçim/kayıt yapılmaz.
function imagePoint(event){const rect=sheet.getBoundingClientRect(),s=scale();
 return [(event.clientX-rect.left)*sheet.width/rect.width/s,(event.clientY-rect.top)*sheet.height/rect.height/s];}
function clamp(value,low,high){return Math.max(low,Math.min(high,value));}
function regionBox(region){return {x:region[0]*picture.width,y:region[1]*picture.height,
 w:(region[2]-region[0])*picture.width,h:(region[3]-region[1])*picture.height};}
function normalizedRegion(a,b){return [clamp(Math.min(a[0],b[0]),0,picture.width)/picture.width,
 clamp(Math.min(a[1],b[1]),0,picture.height)/picture.height,
 clamp(Math.max(a[0],b[0]),0,picture.width)/picture.width,
 clamp(Math.max(a[1],b[1]),0,picture.height)/picture.height];}
function regionArea(region){return (region[2]-region[0])*(region[3]-region[1]);}
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
 const frame=state.options.sheet_frame;if(frame&&frame.found&&(!$('view-show')||$('view-show').checked)){const r=frame.rect;ctx.save();ctx.setLineDash([7,5]);ctx.strokeStyle='#6b4fbb';ctx.lineWidth=2;ctx.strokeRect(r[0]*s,r[1]*s,(r[2]-r[0])*s,(r[3]-r[1])*s);ctx.setLineDash([]);const cx=(r[0]+r[2])/2*s,cy=(r[1]+r[3])/2*s;for(const [i,axis] of (frame.axes||[]).entries()){ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+axis.page[0]*70,cy+axis.page[1]*70);ctx.strokeStyle=i?'#6b4fbb':'#8a2be2';ctx.lineWidth=3;ctx.stroke();}ctx.restore();}
 // PLAN-21 §7.1: callout kutuları. Etiket yeniden sıralanabilir bir gösterim adıdır; gerçek kimlik
 // (ve dolayısıyla kayıt) hiç değişmez.
 for(const row of calloutList()){const box=regionBox(row.region),x=box.x*s,y=box.y*s,w=box.w*s,h=box.h*s,on=row.id===selectedCallout;
  const excluded=row.disposition==='not_model_input';   // G12.1b: yalnız adı konmuş karar "dışarıda"
  ctx.save();ctx.setLineDash(excluded?[5,4]:[]);ctx.lineWidth=on?3:2;
  ctx.strokeStyle=excluded?'#9a938a':(on?'#178a51':'#2f6ea8');ctx.strokeRect(x,y,w,h);
  ctx.fillStyle=excluded?'#9a938a':'#2f6ea8';ctx.font='13px system-ui';ctx.fillText(row.label,x+3,Math.max(12,y-4));ctx.restore();}
 drawTargetHighlight();   // G6: seçili/önerilen hedefin kendisi çizimde görünür
 if(calloutDrag){const box=regionBox(normalizedRegion(calloutDrag.start,calloutDrag.current));
  ctx.save();ctx.setLineDash([6,4]);ctx.strokeStyle='#b56519';ctx.lineWidth=2;
  ctx.strokeRect(box.x*s,box.y*s,box.w*s,box.h*s);ctx.restore();}}
function compass(v){if(!v||v.length!==2)return '?';const [x,y]=v;if(Math.abs(x)>=Math.abs(y))return x>0?'sağ':'sol';return y>0?'aşağı':'yukarı';}
function renderView(){const el=$('view-text');if(!el)return;const frame=state.options&&state.options.sheet_frame;const approved=state.decisions&&state.decisions.view;
 if(approved){el.textContent=`Onaylandı: X ${compass(approved.x_page)}, Y ${compass(approved.y_page)}${approved.frame_rect?` · çerçeve ${approved.frame_rect.map(n=>Math.round(n)).join(' / ')} px`:''} · kaynak ${approved.source}.`;return;}
 if(!frame){el.textContent='Görüş bilgisi bu okumada yok.';return;}
 const axes=frame.axes||[];const where=frame.found?`çerçeve ${frame.rect.map(n=>Math.round(n)).join(' / ')} px`:'çerçeve bulunamadı';
 el.textContent=`${where}; ${axes.length===2?`öneri: X ${compass(axes[0].page)}, Y ${compass(axes[1].page)}`:'eksen önerisi yok'} · ${frame.provenance||''}`;}
// --- G3 callout inceleme (PLAN-21 §6–7): etkin liste sunucudan gelir, tarayıcı yalnız gösterir ---------
function calloutList(){const show=$('callout-show-ignored').checked;
 // G12.1b (PLAN-25 §14/§16): liste filtresi ADI KONMUŞ kapsam kararına bakar — çıplak eski "yok
 // sayıldı" bayrağı satırı gizlemez; o satır kanıtsızdır (legacy_unclassified) ve yeniden karar
 // beklediği için navigasyonda görünür kalır.
 const rows=(state.effective_callouts||[]).filter(row=>show||row.disposition!=='not_model_input');
 // §7.1/§7.3: C1 yalnız bir gösterim adıdır; gerçek kimlik ve kayıt değişmez.
 const out=rows.map((row,index)=>({...row,label:`C${index+1}`}));labelById={};for(const row of out)labelById[row.id]=row.label;return out;}
function calloutRow(id){return id?(calloutList().find(row=>row.id===id)||null):null;}
function calloutStates(){const map={};for(const row of state.callouts||[])map[row.id]=row;return map;}
function calloutBadge(row,stateRow){if(row.disposition==='not_model_input')return 'Modele ait değil';
 if(row.disposition==='redundant')return 'Zaten temsil ediliyor';
 if(row.disposition==='build_relevant_unsupported')return 'Gerçek ölçü/not · uygulanamıyor';
 if(row.ignored)return 'Modele ait değil';if(row.unbindable)return 'Gerçek ölçü/not · uygulanamıyor';const t=(stateRow&&stateRow.transcription)||{state:'missing'};
 if(t.state==='missing')return 'İncelenmedi';if(t.state==='current')return 'Metin kaydedildi';return t.reason==='region_changed'?'Alan değişti':'Metin eskidi';}
function storedText(id){const row=(state.decisions.transcriptions||[]).find(item=>item.callout_id===id);return row?row.raw_text||'':'';}
function calloutAt(p){const hits=calloutList().filter(row=>{const box=regionBox(row.region);
 return p[0]>=box.x&&p[0]<=box.x+box.w&&p[1]>=box.y&&p[1]<=box.y+box.h;});
 // §7.1: en küçük kapsayan kutu kazanır; eşitlikte kimlik sırası — kararlı hit-test.
 return hits.sort((a,b)=>regionArea(a.region)-regionArea(b.region)||a.id.localeCompare(b.id))[0]||null;}
function drawCrop(row){const canvas=$('callout-crop');if(!canvas)return;const cx=canvas.getContext('2d');
 cx.clearRect(0,0,canvas.width,canvas.height);if(!picture.width)return;
 const crop=regionBox(row.crop_region),region=regionBox(row.region);if(crop.w<=0||crop.h<=0)return;
 cx.drawImage(picture,crop.x,crop.y,crop.w,crop.h,0,0,canvas.width,canvas.height);
 const sx=canvas.width/crop.w,sy=canvas.height/crop.h;
 cx.strokeStyle='#178a51';cx.lineWidth=2;cx.strokeRect((region.x-crop.x)*sx,(region.y-crop.y)*sy,region.w*sx,region.h*sy);
 text('callout-crop-note','Kırpma yalnız inceleme kolaylığıdır; doğruluk kararı değildir.');}
// --- G3R-04: tespit sonucu ve nedeni — boş liste tek bir "metinsiz çizim" açıklamasına indirgenmez ----
const DETECTION_REASON={invalid_frame:'çizim çerçevesi okunamadı',unsupported_page:'bu sayfa desteklenmiyor',
 invalid_bbox_nonfinite:'metin kutusu sonlu değil',invalid_bbox_area:'metin kutusu boş',
 bbox_outside_frame:'metin kutusu sayfa dışında',unknown_text_method:'bilinmeyen metin yöntemi',
 region_collapsed:'metin kutusu bölgede sıfıra çöküyor',duplicate_hint_conflict:'aynı bölgede çelişen metinler',
 provenance_ids_capped:'kanıt listesi üst sınıra ulaştı',source_digest_mismatch:'gözlem kaydı bu oturumun kaynağıyla eşleşmiyor'};
function detectionReasons(diagnostics){return [...new Set((diagnostics||[]).map(row=>row.code))]
 .filter(code=>code!=='no_text_observations').map(code=>DETECTION_REASON[code]||`bilinmeyen neden: ${code}`);}
function detectionNotice(hasRows){const detection=state.callout_detection||null;
 if(!detection)return hasRows?'':'Aday bulunmuyor; bu eski kayıtta tespit bilgisi yok. Alanı “Yeni alan çiz” ile siz çizebilirsiniz.';
 const reasons=detectionReasons(detection.diagnostics);
 if(hasRows)return reasons.length?`Uyarı: bazı gözlemler adaya çevrilemedi (${reasons.join('; ')}).`:'';
 if(reasons.length)return `Aday üretilemedi: ${reasons.join('; ')}. Alanı “Yeni alan çiz” ile siz çizebilirsiniz.`;
 const textOnly=(detection.diagnostics||[]).some(row=>row.code==='no_text_observations');
 if(textOnly)return 'Bu çizimde basılı metin bulunamadı: metinsiz çizim normal bir sonuçtur. Alanı “Yeni alan çiz” ile siz çizebilirsiniz.';
 return 'Tespit bu okumada aday üretmedi; nedeni kayıtta yok. Alanı “Yeni alan çiz” ile siz çizebilirsiniz.';}
function renderCallouts(){const list=$('callout-list');if(!list)return;const rows=calloutList(),states=calloutStates();
 if(selectedCallout&&!rows.some(row=>row.id===selectedCallout))selectedCallout=null;
 list.replaceChildren();
 for(const row of rows){const li=document.createElement('li');li.className=row.id===selectedCallout?'selected':'';
  if(selectMode){const box=document.createElement('input');box.type='checkbox';box.checked=selectedForBulk.has(row.id);
   box.onchange=()=>{box.checked?selectedForBulk.add(row.id):selectedForBulk.delete(row.id);renderCallouts();};li.append(box);}
  const name=document.createElement('strong');name.textContent=row.label;
  const note=document.createElement('small');
  note.textContent=` · ${row.source_kind==='manual'?'elle çizilen alan':'makine adayı'} · ${calloutBadge(row,states[row.id])}${drafts.has(row.id)?' · kaydedilmemiş metin':''}`;
  li.append(name,note);
  li.onclick=()=>{if(selectMode){selectedForBulk.has(row.id)?selectedForBulk.delete(row.id):selectedForBulk.add(row.id);renderCallouts();return;}selectedCallout=row.id;render();};list.append(li);}
 const all=state.effective_callouts||[];
 // G12.1b: "modele ait değil" sayısı yalnız ADI KONMUŞ kararı sayar — eski çıplak bayrak bu sayıya
 // girmez, çünkü o satır hâlâ kontrol bekliyor demektir (PLAN-25 §14).
 const claimed=all.filter(row=>row.disposition==='not_model_input').length;
 const reviewed=all.filter(row=>{const t=(states[row.id]||{}).transcription;return t&&t.state!=='missing';}).length;
 const open=unresolvedRows().length;
 text('callout-summary',all.length?`${(state.callout_candidates||[]).length} makine adayı · ${all.length} etkin alan · ${reviewed} incelendi · ${claimed} modele ait değil · ${open} kontrol bekliyor`
  :'Bu okumada ölçü/not alanı yok.');
 text('callout-detection',detectionNotice(all.length));
 // UX-01 A (§6): "Sonraki eksik" sayacı — hiçbir tıklama karar yazmaz.
 text('callout-remaining',all.length?(open?`${open} kontrol kaldı`:'Tüm ölçü/not kontrolleri tamamlandı.'):'');
 $('callout-next').disabled=pending||!open;$('callout-prev').disabled=pending||!rows.length;
 // UX-01 B (§7): seçim modu yalnız kullanıcının kendi işaretlerinden doğar; görünmeyen seçim sessizce düşer.
 $('callout-multi').hidden=!all.length;$('callout-multi').textContent=selectMode?'Seçimi kapat':'Çoklu seç';
 for(const id of [...selectedForBulk])if(!all.some(item=>item.id===id))selectedForBulk.delete(id);
 $('callout-bulk-bar').hidden=!selectMode;text('callout-bulk-count',`${selectedForBulk.size} alan seçildi`);
 $('callout-bulk-apply').disabled=pending||!selectedForBulk.size;$('callout-bulk-cancel').disabled=pending;
 const row=calloutRow(selectedCallout);$('callout-detail').hidden=!row;
 if(!row)return;
 text('callout-title',`${row.label} · ${row.source_kind==='manual'?'elle çizilen alan':'makine tespiti'}${row.region_override?' · alan düzeltildi':''}`);
 text('callout-state',calloutBadge(row,states[row.id]));
 text('callout-hint-line',row.machine_text_hint?`Çizimde şu mu yazıyor? ${row.machine_text_hint}`:'Bu bölgede ne yazıyor? Makine ipucu yok; çizimde yazanı siz yazın.');
 const field=$('callout-text');if(document.activeElement!==field)field.value=drafts.has(row.id)?drafts.get(row.id):storedText(row.id);
 text('callout-draft',drafts.has(row.id)?'Kaydedilmemiş metin var: “Metni kaydet” demeden karar oluşmaz.':'');
 $('callout-hint-yes').disabled=pending||!row.machine_text_hint;$('callout-hint-yes').hidden=!row.machine_text_hint;
 $('callout-hint-edit').hidden=!row.machine_text_hint;
 for(const id of ['callout-save','callout-ignore','callout-restore','callout-edit','callout-new','callout-hint-ignore'])$(id).disabled=pending;
 $('callout-ignore').hidden=row.ignored;$('callout-restore').hidden=!row.ignored;
 // UX-01 §10/§12: ham kimlik ve geometri yalnız "Teknik ayrıntılar" altında görünür.
 $('callout-technical').hidden=false;
 text('callout-raw',`kimlik: ${row.id} · alan: ${(row.region||[]).map(value=>Number(value).toFixed(3)).join(', ')} · kaynak: ${row.source_kind}`
  +`${row.region_override?' · alan düzeltildi':''} · geometri: ${row.geometry_version||'—'}`);drawCrop(row);}
const CALLOUT_NOTE={add_region:'Yeni alan kaydedildi.',edit_region:'Alan düzeltmesi kaydedildi.',set_ignored:'Karar kaydedildi.',
 bulk_set_ignored:'Seçilen alanlar tek adımda "modele ait değil" olarak işaretlendi.',
 set_disposition:'Kapsam kararı kaydedildi.',
 transcribe:'Metin kaydedildi; onaylanan hedefle birlikte derlemeye girer.'};
async function refreshState(){try{const response=await fetch('/api/guided/'+state.token);const data=await response.json();if(response.ok)state=data;}catch(e){/* durum alınamadı: mevcut state olduğu gibi kalır */}}
async function command(action,payload,after){busy(true);const known=new Set((state.effective_callouts||[]).map(row=>row.id));
 const previous=selectedCallout,previousOrder=calloutList().map(row=>row.id);let advance=null;
 try{state=await api('/api/guided/callout',{token:state.token,revision:state.revision,action,payload});
  if(action==='add_region'){const fresh=(state.effective_callouts||[]).find(row=>!known.has(row.id));if(fresh)selectedCallout=fresh.id;}
  if(action==='transcribe')drafts.delete(payload.callout_id);   // karar sunucuya yazıldı: taslak artık gereksiz
  status(CALLOUT_NOTE[action]||'Karar kaydedildi.');
  if(after)after();
  // UX-01 §6.4: oto-ilerleme yalnız başarılı karardan sonra kurulur; hata/çakışma/iptal kurmaz.
  // PLAN-25 §17: liste YALNIZ satırı gerçekten çözebilen komutları taşır — legacy set_unbindable
  // (artık build_relevant_unsupported yazar) burada değildir; kapsam kararı da kapıdan geçer.
  if(['transcribe','set_ignored','set_disposition'].includes(action))advance={id:previous,order:previousOrder};}
 catch(e){status(e.message,true);
  // §7.3: çakışmada sessiz last-write-wins yok — hata görünür, yazılan taslak durur, güncel durum alınır.
  if(/oturum değişti/.test(e.message)){await refreshState();status(`${e.message} — yazdığınız metin duruyor; güncel durum alındı, kararı tekrar kaydedebilirsiniz.`,true);}}
 finally{busy(false);}
 if(advance)advanceAfterDecision(advance.id,advance.order);}
// G12.2 (PLAN-25 §36/§42): üretim biçimi açık bir kullanıcı kararıdır. Anahtarı ve geometri sürümünü
// sunucu sabitler; istemci yalnız türü söyler, bu yüzden burada `save()` değil komut yolu kullanılır.
async function chooseStrategy(kind){busy(true);
 try{state=await api('/api/guided/strategy',{token:state.token,revision:state.revision,kind});
  status(kind==='unsupported'?'Parça "bu sürümde desteklenmiyor" olarak işaretlendi; üretim başlamaz.'
                            :'Oluşturma biçimi kaydedildi.');}
 catch(e){status(e.message,true);if(/oturum değişti/.test(e.message))await refreshState();}
 finally{busy(false);}}
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
  const name=end=>humanRef(end.id);
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
sheet.onclick=async event=>{if(!state||pending)return;
 if(suppressClick){suppressClick=false;return;}   // §7.2: sürüklemenin ardından gelen click başka modu seçmez
 const rect=sheet.getBoundingClientRect(),s=scale(),displayed=rect.width/picture.width,p=imagePoint(event);
 if(mode==='target'){const hit=targetHit(p,displayed);
  if(!hit)return status(targetKind==='arc'?'Bu noktada yay yok: yay kenarına tıklayın.'
   :targetKind==='vertex_pair'?'Bu noktada köşe yok: kontur köşesine yakın tıklayın.'
   :targetKind==='profile'?'Bu noktada kontur yok: bir konturun içine tıklayın.'
   :'Bu noktada daire yok: dairenin kenarına ya da içine tıklayın.',true);
  if(targetKind==='circle_group'){targetPick=targetPick.includes(hit)?targetPick.filter(x=>x!==hit):[...targetPick,hit];}
  else if(targetKind==='vertex_pair'){targetPick=targetPick.filter(x=>x!==hit);targetPick=[...targetPick,hit].slice(-2);}
  else targetPick=[hit];
  renderTarget();draw();return;}
 if(mode==='callout'||mode==='callout-draw'||mode==='callout-edit'){const hit=calloutAt(p);
  if(hit){selectedCallout=hit.id;render();}else{selectedCallout=null;render();status('Bu noktada ölçü/not alanı yok; listeden seçin ya da “Yeni alan çiz” ile çizin.');}return;}
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
async function save(decisions,after){busy(true);try{state=await api('/api/guided/save',{token:state.token,revision:state.revision,decisions});status('Karar kaydedildi.');if(after)after();}catch(e){status(e.message,true);}finally{busy(false);}}
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
document.addEventListener('keydown',event=>{if(event.key!=='Escape')return;
 if(targetPick.length){targetPick=[];proposalHighlight=null;setMode('callout');
  status('Yer seçimi bırakıldı; hiçbir karar yazılmadı.');renderTarget();draw();return;}
 if(calloutDrag){calloutDrag=null;status('Alan çizimi iptal edildi.');draw();return;}
 if(mode==='callout-draw'||mode==='callout-edit')setMode('callout');});
// --- G3 kullanıcı komutları (PLAN-21 §6.4/§7.4) --------------------------------------------------------
$('pick-callout').onclick=()=>setMode('callout');
$('draw-callout').onclick=()=>setMode('callout-draw');
$('callout-new').onclick=()=>setMode('callout-draw');
$('callout-show-ignored').onchange=()=>render();
$('callout-hint-yes').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 if(!row.machine_text_hint)return status('Bu bölgede makine ipucu yok; metni kendiniz yazın.',true);
 command('transcribe',{callout_id:row.id,raw_text:row.machine_text_hint,accept_hint:true});};
$('callout-hint-edit').onclick=()=>{const row=calloutRow(selectedCallout);if(!row||!row.machine_text_hint)return;
 const field=$('callout-text');field.value=row.machine_text_hint;drafts.set(row.id,row.machine_text_hint);
 field.scrollIntoView({block:'center'});field.focus();renderCallouts();
 status('İpucu taslağa alındı; düzeltip “Metni kaydet” deyin. Kaydet demeden hiçbir karar yazılmaz.');};
$('callout-hint-ignore').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 command('set_ignored',{callout_id:row.id,ignored:true});};
$('callout-text').oninput=()=>{if(selectedCallout)drafts.set(selectedCallout,$('callout-text').value);renderCallouts();};
$('callout-save').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 const value=$('callout-text').value;if(!value.trim())return status('Boş metin kaydedilemez: çizimde yazanı girin.',true);
 command('transcribe',{callout_id:row.id,raw_text:value});};
$('callout-ignore').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);command('set_ignored',{callout_id:row.id,ignored:true});};
$('callout-restore').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);command('set_ignored',{callout_id:row.id,ignored:false});};
$('callout-edit').onclick=()=>{if(!calloutRow(selectedCallout))return status('Önce düzeltilecek ölçü/not alanını seçin.',true);setMode('callout-edit');};
// --- UX-01 A/B: "Sonraki eksik" akışı + tek atomik toplu kapsam kararı (UX_PLAN §6–§7) ---------------
// Çözülmüş tanımı G12.1b'den sonra SUNUCUDAN gelir (PLAN-25 §14/§15): satırın kapsam kovası
// çözüyorsa çözülmüş sayılır. Navigasyon hiçbir karar yazmaz; oto-ilerleme yalnız başarılı ve
// satırı çözen karardan sonra kurulur. Hiçbir satır kendiliğinden kapsam dışı olmaz: toplu karar
// yalnız kullanıcının kendi seçtiği satırlarla, tek atomik `bulk_set_ignored` isteğiyle yazılır.
// --- G12.1b (PLAN-25 §14/§15): çözülmüşlük BACKEND kapsam kovasından okunur ------------------------
// Tarayıcı ikinci bir kapsam motoru kurmaz: hangi satırın hangi kovada olduğuna sunucu karar verir.
// Çözen kovalar: not_model_input, geçerli redundant, build_applied. Bloklayan kovalar
// (build_relevant_unsupported, legacy_unclassified, invalid_duplicate, stale, compile_blocked,
// unclassified) satırı çözülmüş SAYMAZ — "Sonraki eksik" bu satırlara uğrar, oto-ilerleme kurmaz.
const RESOLVED_BUCKETS=['not_model_input','redundant','build_applied'];
function coverageBucket(id){const coverage=state&&state.coverage;if(!coverage)return null;
 for(const name of Object.keys(coverage)){const ids=coverage[name];if(Array.isArray(ids)&&ids.includes(id))return name;}return null;}
function rowResolved(id){const row=(state.effective_callouts||[]).find(item=>item.id===id)||null;if(!row)return true;
 const bucket=coverageBucket(id);if(bucket)return RESOLVED_BUCKETS.includes(bucket);
 return false;}   // kapsam bilgisi yoksa satır çözülmüş sayılmaz: sessiz varsayım yok.
function unresolvedRows(){return calloutList().filter(row=>!rowResolved(row.id));}
function goToCallout(id){selectedCallout=id;render();
 const li=[...document.querySelectorAll('#callout-list li')].find(item=>item.classList.contains('selected'));
 if(li)li.scrollIntoView({block:'center'});}
function advanceAfterDecision(previousId,order){
 // G11R-03 (bağımsız inceleme): karar satırı görünür listeden düşünce (ör. “Bu bir ölçü/not değil”
 // ve “İhmal edilenleri göster” kapalı) yeniden çizim seçimi temizler; bu kullanıcının taşınması
 // değildir — sıradaki açık alan, kararın KENDİ konumundan (karar öncesi görünür sıra) sürdürülür.
 // Kullanıcı bu arada başka satıra geçtiyse ilerlemeyiz.
 if(!previousId)return;
 if(selectedCallout&&selectedCallout!==previousId)return;
 // §6.4: ilerleme yalnız satır gerçekten çözülmüş hale geldiyse — çözülmemiş satırdan zıplanmaz.
 if(!rowResolved(previousId))return;
 const rows=unresolvedRows().filter(row=>row.id!==previousId);if(!rows.length)return;
 const base=order&&order.length?order:calloutList().map(row=>row.id);
 const start=base.indexOf(previousId);
 const seq=start<0?base:[...base.slice(start+1),...base.slice(0,start+1)];
 const pick=seq.find(id=>rows.some(row=>row.id===id));
 if(pick)goToCallout(pick);}
$('callout-next').onclick=()=>{const rows=unresolvedRows();
 if(!rows.length)return status('Tüm ölçü/not kontrolleri tamamlandı.');
 const index=rows.findIndex(row=>row.id===selectedCallout);goToCallout(rows[(index+1)%rows.length].id);};
$('callout-prev').onclick=()=>{const list=calloutList();if(!list.length)return;
 const index=list.findIndex(row=>row.id===selectedCallout);
 const pick=list[(index<=0?list.length:index)-1];if(pick)goToCallout(pick.id);};
let selectMode=false;const selectedForBulk=new Set();
$('callout-multi').onclick=()=>{selectMode=!selectMode;if(!selectMode)selectedForBulk.clear();render();};
$('callout-bulk-cancel').onclick=()=>{selectMode=false;selectedForBulk.clear();render();};
$('callout-bulk-apply').onclick=()=>{const ids=[...selectedForBulk];
 if(!ids.length)return status('Önce listeden alan seçin.',true);
 command('bulk_set_ignored',{callout_ids:ids,ignored:true},()=>{selectMode=false;selectedForBulk.clear();});};
// §7.2: sürükleme pointer olaylarıyla yürür; Escape/iptal kayıt üretmez, pointer capture yarım çizimi bırakır.
sheet.addEventListener('pointerdown',event=>{if(!state||pending||!picture.width)return;
 if(mode!=='callout-draw'&&mode!=='callout-edit')return;
 const origin=mode==='callout-edit'?calloutRow(selectedCallout):null;
 if(mode==='callout-edit'&&!origin)return status('Önce düzeltilecek ölçü/not alanını seçin.',true);
 const point=imagePoint(event);calloutDrag={mode,start:point,current:point,origin};suppressClick=false;
 if(sheet.setPointerCapture)sheet.setPointerCapture(event.pointerId);draw();});
sheet.addEventListener('pointermove',event=>{if(!calloutDrag)return;calloutDrag.current=imagePoint(event);draw();});
sheet.addEventListener('pointerup',event=>{if(!calloutDrag)return;const drag=calloutDrag;calloutDrag=null;
 if(sheet.releasePointerCapture){try{sheet.releasePointerCapture(event.pointerId);}catch(e){/* pointer zaten serbest */}}
 suppressClick=true;   // aynı hareketin click'i profile/hole seçmesin
 const region=normalizedRegion(drag.start,drag.current),box=regionBox(region);
 if(box.w<4||box.h<4){draw();return status('Alan çok küçük: çizim üzerinde bir kutu sürükleyin.',true);}
 if(drag.mode==='callout-edit')command('edit_region',{callout_id:drag.origin.id,region});else command('add_region',{region});});
sheet.addEventListener('pointercancel',()=>{if(!calloutDrag)return;calloutDrag=null;status('Alan çizimi iptal edildi.',true);draw();});
$('build').onclick=async()=>{busy(true);status('Kararlardan 3B taslak hazırlanıyor; STEP yeniden açılarak kontrol ediliyor…');try{state=await api('/api/guided/build',{token:state.token,revision:state.revision});render();if(state.error)throw Error(state.error);if(state.stl)await showStl(state.stl,$('preview'));status('Taslak hazır. Geometrik kontrol tamam; çizimle ölçü doğruluğunu ayrıca inceleyin.');}catch(e){status(e.message,true);}finally{busy(false);}};
(async()=>{const token=new URLSearchParams(location.search).get('session');if(token){busy(true);try{const r=await fetch('/api/guided/'+token);const data=await r.json();if(!r.ok)throw Error(data.error);state=data;await loadImage();render();if(state.stl)await showStl(state.stl,$('preview'));status('Kaydedilmiş oturum açıldı.');}catch(e){status(e.message,true);}finally{busy(false);}}})().catch(()=>{});

// --- G6 hedef onayı (PLAN §11): öneri → kullanıcı onayı ya da kendi seçimi, kanıtıyla birlikte -------
// Sunucu ne okuduysa onu gösterir; burada üretilen tek şey kullanıcının *kararıdır* (hedef satırı) ya
// da kapsam kararı ("bağlanamaz"). Öneri kendiliğinden onaylanmaz.
let targetInfo=null,targetKey=null,targetLoading=null,targetPick=[],proposalHighlight=null,targetKind='circle';
let readiness=null,readinessRevision=null;
const TARGET_KIND_LABEL={circle:'tek daire',circle_group:'daire grubu',arc:'yay',vertex_pair:'iki uç',profile:'kontur'};
const TARGET_STATE_LABEL={missing:'gösterdiği yer onaylanmadı',current:'gösterdiği yer güncel',stale:'gösterdiği yer eskidi',missing_transcription:'önce metni yazın'};
function pickedTranscription(){return (state.decisions.transcriptions||[]).find(row=>row.callout_id===selectedCallout)||null;}
function calloutStateRow(id){return calloutStates()[id]||null;}
function isStaleTarget(){const row=calloutStateRow(selectedCallout);return Boolean(row&&row.target&&row.target.state==='stale');}
function vertexOf(edgeId,which){for(const profile of state.options.profiles||[])for(const edge of profile.edges||[])if(edge.id===edgeId)return which==='end'?edge.end:edge.start;return null;}
function insideProfile(profile,p){const pts=profile.points||[];let inside=false;
 for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [xi,yi]=pts[i],[xj,yj]=pts[j];
  if(((yi>p[1])!==(yj>p[1]))&&(p[0]<(xj-xi)*(p[1]-yi)/((yj-yi)||1e-9)+xi))inside=!inside;}return inside;}
function targetHit(p,displayed){   // test modu: tür kullanıcının seçimidir, kimlik çizimden gelir
 if(targetKind==='arc'){let best=null;for(const prim of state.options.primitives||[]){if(prim.kind!=='arc')continue;
  const delta=Math.abs(Math.hypot(p[0]-prim.center[0],p[1]-prim.center[1])-prim.radius);
  if(delta*displayed<18&&(!best||delta<best.delta))best={id:prim.id,delta};}return best?best.id:null;}
 if(targetKind==='profile'){let found=null;for(const profile of state.options.profiles||[])if(insideProfile(profile,p))found=profile.id;return found;}
 if(targetKind==='vertex_pair'){const end=snapEnd(p,displayed);return end&&end.kind==='vertex'?end.id:null;}
 const hit=holeAt(p,displayed);return hit?hit.id:null;}
function targetHighlight(){if(targetPick.length)return {kind:targetKind,ids:targetPick};
 if(proposalHighlight)return proposalHighlight;
 const stored=(targetInfo&&targetInfo.target)||null;return stored?{kind:stored.target_kind,ids:stored.target_ids}:null;}
function drawTargetHighlight(){const show=targetHighlight();if(!show||!state)return;const s=scale();
 ctx.save();ctx.setLineDash([6,4]);ctx.lineWidth=3;ctx.strokeStyle='#7a2ea8';
 for(const id of show.ids){
  const circle=(state.options.circles||[]).find(c=>c.id===id);
  if(circle){ctx.beginPath();ctx.arc(circle.center[0]*s,circle.center[1]*s,(circle.radius+3/ (scale()||1))*s,0,2*Math.PI);ctx.stroke();continue;}
  const profile=(state.options.profiles||[]).find(item=>item.id===id);
  if(profile){ctx.beginPath();(profile.points||[]).forEach((v,i)=>i?ctx.lineTo(v[0]*s,v[1]*s):ctx.moveTo(v[0]*s,v[1]*s));ctx.closePath();ctx.stroke();continue;}
  const arc=(state.options.primitives||[]).find(item=>item.kind==='arc'&&item.id===id);
  if(arc){ctx.beginPath();ctx.arc(arc.center[0]*s,arc.center[1]*s,arc.radius*s,0,2*Math.PI);ctx.stroke();continue;}
  const [edge,which]=String(id).split(':');const end=vertexOf(edge,which);
  if(end){ctx.beginPath();ctx.arc(end[0]*s,end[1]*s,8,0,2*Math.PI);ctx.stroke();}}
 ctx.restore();}
function renderTarget(){const panel=$('target-panel');if(!panel)return;const row=calloutRow(selectedCallout);
 if(!row){panel.hidden=true;targetInfo=null;targetKey=null;targetPick=[];proposalHighlight=null;return;}
 panel.hidden=false;
 const key=`${row.id}@${state.revision}`;
 if(targetKey!==key){proposalHighlight=null;targetPick=[];targetKey=key;targetInfo=null;}
 if(targetKey===key&&!targetInfo&&targetLoading!==key){targetLoading=key;loadTarget(key);}
 const stored=(targetInfo&&targetInfo.target)||null,stateRow=calloutStateRow(row.id)||{};
 const target=stateRow.target||{state:'missing',reason:null};
 const unsupported=row.disposition==='build_relevant_unsupported'||row.unbindable;
 const redundant=row.disposition==='redundant';
 text('target-state',unsupported?'gerçek ölçü/not: bu sürüm uygulayamıyor'
  :redundant?'zaten başka bir bilgiyle temsil ediliyor':(TARGET_STATE_LABEL[target.state]||target.state));
 const summary=$('target-summary');
 // PLAN-25 §16: desteklenmeyen satıra gelindiğinde panel ne olduğunu ve ne gerektiğini söyler.
 summary.textContent=unsupported?`Bu gerçek bilgi şu an modele uygulanamıyor. Model oluşturmak için bu capability çözülmeli veya karar düzeltilmeli.${row.disposition_reason?` (Gerekçe: ${row.disposition_reason})`:''}`
  :redundant?`Zaten başka bir bilgiyle temsil ediliyor (dayanak: ${row.duplicate_of||'—'}).${coverageBucket(row.id)==='invalid_duplicate'?' Dayanak şu an geçerli değil: dayanağı yeniden bağlayın.':''}`
  :(targetInfo===null?'Öneriler alınıyor…':(target.state==='stale'?`Gösterdiği yer eskidi (${target.reason||'—'}); yeniden onaylayın — onay eski geometriye bağlanmaz.`
   :(stored?`Onaylı: ${targetDescription(stored)} · ${evidenceText(stored)}`:'Gösterdiği yer henüz onaylanmadı.')));
 const box=$('target-proposals');box.replaceChildren();
 const proposals=(targetInfo&&targetInfo.proposals)||[];
 if(targetInfo&&proposalHighlight&&!highlightedProposal())proposalHighlight=null;   // bayat vurgu sessizce kalmaz
 if(targetInfo&&targetInfo.error){const p=document.createElement('p');p.className='muted';p.textContent=`Öneri alınamadı: ${targetInfo.error}`;box.append(p);}
 for(const [index,item] of proposals.entries()){const div=document.createElement('div');div.className='feature';
  const choose=document.createElement('button');choose.className='secondary';choose.textContent='Seç';
  choose.onclick=()=>confirmProposal(item);
  const label=document.createElement('span');label.style.cursor='pointer';
  label.textContent=`${index+1}. ${targetDescription(item)} · ${evidenceText(item)}`;
  label.onclick=()=>{proposalHighlight={kind:item.target_kind,ids:item.target_ids};renderTarget();draw();};
  div.append(choose,label);box.append(div);}
 if(!proposals.length&&!(targetInfo&&targetInfo.error)){const p=document.createElement('p');p.className='muted';
  p.textContent=pickedTranscription()?'Bu bölgede öneri yok: “Başka yer seç” ile çizimden seçin.':'Önce metni kaydedin: gösterdiği yer onayı güncel bir okumaya bağlanır.';box.append(p);}
 $('target-proposal-label').hidden=!proposals.length;
 const active=activeProposal();
 $('target-confirm').disabled=pending||row.ignored||!active;
 $('target-confirm').textContent=active?`Doğru · ${proposals.indexOf(active)+1}. öneri`:'Doğru';
 $('target-other').disabled=pending||row.ignored;$('target-group').disabled=pending||row.ignored;
 $('target-unbindable').disabled=pending;
 $('target-unbindable').textContent=unsupported?'Bu kararı geri al':'Gerçek ölçü/not ama şu an modele uygulanamıyor';
 $('target-redundant').disabled=pending;
 $('target-redundant').textContent=redundant?'Bu kararı geri al':'Zaten başka bir bilgiyle temsil ediliyor';
 renderRedundantOptions();
 $('target-kind').disabled=pending||row.ignored;
 const picked=$('target-picked');
 picked.textContent=targetPick.length?`Seçilen ${targetPick.length} yer: ${targetPick.map(humanRef).join(', ')} — tür: ${TARGET_KIND_LABEL[targetKind]}.`:'';
 $('target-apply').hidden=!targetPick.length;$('target-cancel').hidden=!targetPick.length;
 $('target-apply').disabled=pending;
 text('target-note',target.state==='stale'&&stored?'Onay, taşıdığı geometri anahtarı eski kaldığı için "reconfirm" olarak yeniden yazılır; eski onay üretime girmez.'
  :'Onayladığınız yer, metnin okumasıyla birlikte delik/ölçü kararına derlenir.');}
// UX-01 §12: ana copy ham kimlik göstermez — kimlikler yalnız "Teknik ayrıntılar"da; sunucuya gerçek ID gider.
function humanRef(id){if(!state)return String(id);
 const circleIndex=(state.options.circles||[]).findIndex(circle=>circle.id===id);
 if(circleIndex>=0)return `Daire ${circleIndex+1}`;
 const edges=(state.options.profiles||[]).flatMap(profile=>profile.edges||[]);
 if(String(id).includes(':')){const [edge,which]=String(id).split(':');const index=edges.findIndex(item=>item.id===edge);
  return index>=0?`Köşe ${index+1}${which==='end'?' (bitiş)':which==='start'?' (başlangıç)':''}`:'Köşe';}
 if((state.options.profiles||[]).some(profile=>profile.id===id))return 'Dış şekil';
 const arcs=(state.options.primitives||[]).filter(prim=>prim.kind==='arc');
 const arcIndex=arcs.findIndex(arc=>arc.id===id);
 if(arcIndex>=0)return `Yay ${arcIndex+1}`;
 return 'Öğe';}
function targetDescription(row){return `${TARGET_KIND_LABEL[row.target_kind]||row.target_kind} · ${(row.target_ids||[]).map(humanRef).join(', ')}`;}
function evidenceText(row){const e=(row.evidence||[])[0]||{};return `${row.evidence_tier||''}${e.detail?` · ${e.detail}`:e.ref?` · ${e.ref}`:e.kind?` · ${e.kind}`:''}`;}
// R03 (inceleme): tek aktif öneri — etikete tıklayıp vurgulamak *neyi* onaylayacağını belirler;
// genel [Onayla] vurgulanan öneriyi (yoksa ilkini — düğme bunu açıkça söyler) yazar, asla
// sessizce başka bir hedefi değil. Vurgu listeyle eşleşmezse bayat sayılır ve temizlenir.
function highlightedProposal(){if(!proposalHighlight||!targetInfo||!targetInfo.proposals)return null;
 return targetInfo.proposals.find(item=>item.target_kind===proposalHighlight.kind&&String(item.target_ids)===String(proposalHighlight.ids))||null;}
function activeProposal(){return highlightedProposal()||((targetInfo&&targetInfo.proposals||[])[0]||null);}
async function loadTarget(key){try{const data=await api('/api/guided/propose',{token:state.token,callout_id:selectedCallout});
  if(targetLoading===key)targetInfo={key,...data};}
 catch(e){if(targetLoading===key)targetInfo={key,error:e.message,proposals:[],target:null};}
 finally{if(targetLoading===key)targetLoading=null;}
 renderTarget();draw();}
function saveTarget(kind,ids,evidence,reconfirm){const t=pickedTranscription();
 if(!t){status('Önce metni kaydedin: gösterdiği yer onayı güncel bir okumaya bağlanır.',true);return;}
 if(!kind||!ids.length){status('Gösterdiği yer türü ve kimlikleri gerekli.',true);return;}
 const row={callout_id:selectedCallout,target_kind:kind,target_ids:ids,transcription_revision:t.revision,
  parser_version:(targetInfo&&targetInfo.parser_version)||null,evidence:evidence,reconfirm:Boolean(reconfirm)};
 // UX-01 §6.4: hedef onayı da satırı çözebilir; oto-ilerleme yalnız başarılı save'den sonra kurulur.
 const previous=selectedCallout;
 save({...state.decisions,callout_targets:[...(state.decisions.callout_targets||[]).filter(item=>item.callout_id!==selectedCallout),row]},
  ()=>advanceAfterDecision(previous));}
function confirmProposal(item){if(!item)return status('Onaylanacak öneri yok.',true);
 saveTarget(item.target_kind,item.target_ids,[{kind:'proposal',ref:`${item.evidence_tier} · ${(item.target_ids||[]).join(', ')}`}],isStaleTarget());}
function beginTargetPick(kind){targetKind=kind;$('target-kind').value=kind;targetPick=[];proposalHighlight=null;
 // UX_PLAN §11: tür kutusu normalde gizli; yalnız manual seçim sırasında görünür.
 $('target-kind-box').hidden=false;setMode('target');renderTarget();draw();
 status('Çizim üzerinde gösterdiği yeri seçin: tür seçimi sizin, kimlikler çizimden gelir.');}
// --- G8 hazırlık (PLAN §14): üretim yalnız "hazır" iken başlar ---------------------------------------
async function loadReadiness(){if(!state)return;
 if(readiness&&readinessRevision===state.revision){renderReadiness();return;}
 try{const r=await fetch('/api/guided/readiness',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({token:state.token})});if(r.ok){readiness=await r.json();readinessRevision=state.revision;}}
 catch(e){/* hazırlık okunamadı: panel eski değeriyle kalır, üretim düğmesi kapanır */readiness=null;}
 renderReadiness();}
// UX-01 §9.3: her kategori kullanıcının yapacağı işe çevrilir; sayılar backend readiness satırlarından gelir.
const READINESS_TASK={missing_transcription:'Ölçü/not kontrolü',parse_error:'Ölçü/not metnini düzelt',
 parse_ambiguous:'Ölçü/not metnini netleştir',missing_unit:'Birimi belirt',missing_target:'Gösterdiği yeri seç',
 ambiguous_target:'Gösterdiği yeri seç',stale_target:'Gösterdiği yeri yeniden onayla',missing_profile:'Dış şekli seç',
 missing_calibration:'Ölçeği tamamla',missing_view:'Görüş yönünü onayla',
 unsupported_semantic:'Modele uygulanıp uygulanmayacağına karar ver',
 unsupported_cad_feature:'Modele uygulanıp uygulanmayacağına karar ver',callout_conflict:'Çelişkiyi düzelt',
 geometry_conflict:'Çizim/geometri sorununu düzelt',
 // G12.1b (PLAN-25 §18): üç kapsam kategorisi kullanıcının yapacağı işe çevrilir.
 unsupported_build_relevant:'Desteklenmeyen gerçek bilgiyi gözden geçir',
 legacy_unclassified:'Eski kapsam kararını yeniden ver',
 stale_duplicate_reference:'Dayanağı yeniden bağla',
 // G12.2 (PLAN-25 §42): üretim biçimi maddesinin kontrol listesi karşılığı.
 missing_build_strategy:'Parçanın ana oluşturma biçimini seç',
 stale_build_strategy:'Oluşturma biçimini yeniden onayla',
 unsupported_build_strategy:'Oluşturma biçimini gözden geçir'};
// PLAN-25 §19: kapsam özeti yalnız backend counts'undan çizilir; teknik kova adları görünmez.
const COVERAGE_WORDING={not_model_input:'modele ait değil',build_applied:'modele uygulandı',
 redundant:'zaten temsil ediliyor',build_relevant_unsupported:'desteklenmiyor'};
function coverageLine(coverage){const counts=(coverage&&coverage.counts)||{};const parts=[];
 for(const name of Object.keys(COVERAGE_WORDING)){const count=counts[name]||0;if(count)parts.push(`${count} ${COVERAGE_WORDING[name]}`);}
 const waiting=Object.keys(counts).filter(name=>!(name in COVERAGE_WORDING)).reduce((n,name)=>n+(counts[name]||0),0);
 if(waiting)parts.push(`${waiting} kontrol bekliyor`);return parts.join(' · ');}
// G9 UX turu: hazırlık bir eylem listesidir — her madde *sunucunun kendi satırındaki* `action`/`reason`
// ile ilgili denetime götürür (eylem DOM'dan geri okunmaz; karar sunucunun satırından gelir).
function readinessGo(q){const row=q&&q.callout_id?calloutRow(q.callout_id):null;
 if(row){selectedCallout=row.id;render();}
 const go=el=>{if(!el)return;el.scrollIntoView({block:'center'});if(el.focus)el.focus();};
 const action=q?q.action:null;
 if(action==='transcribe'||action==='edit_transcription'){const first=row?null:unresolvedRows()[0];
  if(first){selectedCallout=first.id;render();}return go($('callout-text'));}
 if(action==='confirm_target'||action==='review_callout'||action==='review_conflict')return go($('target-panel'));
 if(action==='confirm_view')return go($('view-confirm'));
 // G12.2 §42: strateji maddesi paneli öne alır — kullanıcı seçimi orada yapar.
 if(action==='choose_build_strategy')return go($('strategy-choices'));
 const byReason={profile_not_chosen:$('profile'),calibration_missing:$('pick-calibration'),
  thickness_missing:$('thickness'),trace_not_acknowledged:$('ack'),binding_axis_missing:$('bind-axis'),
  binding_unsupported:$('bindings'),binding_unresolved:$('bindings'),view_not_confirmed:$('view-confirm'),
  view_mismatch:$('view-confirm')};
 go(byReason[q&&q.reason]||$('readiness-box'));}
function renderReadiness(){const list=$('readiness-questions');if(!list)return;const r=readiness,summary=$('readiness-summary');
 if(!r){summary.textContent='Eksikler okunuyor…';text('coverage-summary','');list.replaceChildren();return;}
 text('coverage-summary',r.coverage?coverageLine(r.coverage):'');
 summary.textContent=r.ready?'✓ Tüm gerekli bilgiler tamamlandı':`Model henüz hazır değil · ${r.questions.length} şey kaldı`;
 list.replaceChildren();
 // Sayılar backend satırlarından gruplanır (§9.2): aynı görev birden çok satırsa tek sayıyla yazılır.
 const groups=[];
 for(const q of r.questions){const task=READINESS_TASK[q.category]||q.text;
  const group=groups.find(item=>item.task===task);if(group){group.count+=1;group.questions.push(q);}
  else groups.push({task,count:1,questions:[q]});}
 for(const group of groups){const li=document.createElement('li');
  const mark=document.createElement('span');mark.textContent='○ ';
  const line=document.createElement('span');line.textContent=group.count>1?`${group.count} ${group.task}`:group.task;
  li.append(mark,line);li.onclick=()=>readinessGo(group.questions[0]);list.append(li);}
 // Tamamlananlar current session state'ten okunur (§9.2 ✓ satırları).
 const done=[];
 if(state.decisions.profile_id)done.push('Dış şekil seçildi');
 if(state.decisions.thickness)done.push('Kalınlık girildi');
 if(state.decisions.calibration)done.push('Ölçek girildi');
 if(state.decisions.view)done.push('Görüş yönü onaylandı');
 for(const item of done){const li=document.createElement('li');li.className='muted';li.textContent=`✓ ${item}`;list.append(li);}
 const build=$('build');build.disabled=pending||!r.ready;
 build.title=r.ready?'':'Üretim yalnız eksik kalanlar tamamlanınca başlar.';}
// --- GX inceleme paketi (PLAN §12): paket taşır, karar içe aktarılınca doğar -------------------------
function bundleName(){return `inceleme-${String(state.token).slice(0,8)}-r${state.revision}.json`;}
$('review-export').onclick=async()=>{busy(true);
 try{const bundle=await api('/api/guided/export',{token:state.token});
  const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=bundleName();link.click();URL.revokeObjectURL(url);
  status('İnceleme paketi indirildi: paket bu okumanın kendisini taşır, karar içe aktarılınca doğar.');}
 catch(e){status(e.message,true);}finally{busy(false);}};
$('review-import').onchange=async event=>{const file=event.target.files[0];event.target.value='';if(!file)return;
 busy(true);status('Paket doğrulanıyor…');
 try{const bundle=JSON.parse(await file.text());
  state=await api('/api/guided/import',{token:state.token,revision:state.revision,bundle});
  status('İnceleme içe aktarıldı: eylemler bu kaydın doğrulamasından geçti ve “dış inceleme” olarak işaretlendi.');}
 catch(e){status(e.message,true);}finally{busy(false);}};
// --- bağlanma: var olan düğmeler ve çizim döngüsü -----------------------------------------------
$('target-confirm').onclick=()=>{const item=activeProposal();
 if(!item)return status('Onaylanacak öneri yok; “Başka yer seç” ile çizimden seçin.',true);
 $('target-kind-box').hidden=true;confirmProposal(item);};
$('target-other').onclick=()=>beginTargetPick($('target-kind').value||'circle');
$('target-group').onclick=()=>beginTargetPick('circle_group');
$('target-kind').onchange=()=>{targetKind=$('target-kind').value;renderTarget();};
$('target-apply').onclick=()=>{if(!targetPick.length)return status('Önce çizimden yer seçin.',true);
 $('target-kind-box').hidden=true;
 saveTarget(targetKind,targetPick,[{kind:'user_click',ref:`${targetKind} · ${targetPick.map(humanRef).join(', ')}`}],isStaleTarget());};
$('target-cancel').onclick=()=>{targetPick=[];proposalHighlight=null;$('target-kind-box').hidden=true;setMode('callout');renderTarget();draw();};
// --- G12.1b (PLAN-25 §10–§13): üç kapsam kararı; gerekçe ve dayanak kullanıcıdan -------------------
// Legacy `set_unbindable` arayüzden kaldırıldı: aynı düğme artık doğrudan set_disposition çağırır,
// gerekçe zorunludur ve frontend varsayılan bir gerekçe UYDURMAZ. Dayanak seçimi backend'in
// `decision:<ad>` sözlüğünü kullanır; sunucu reddederse taslak/seçim korunur ve hata görünür kalır.
const DECISION_REF_LABEL={calibration:'kalibrasyon',profile:'dış profil kararı',thickness:'kalınlık kararı',
 holes:'delik kararları',bindings:'bağlanan ölçüler',contour:'kontur kararı',view:'görüş yönü',trace:'izleme onayı'};
function decisionRefPresent(name){const d=(state&&state.decisions)||{};
 if(name==='calibration')return d.calibration!=null;if(name==='profile')return Boolean(d.profile_id);
 if(name==='thickness')return d.thickness!=null;if(name==='holes')return Boolean((d.holes||[]).length);
 if(name==='bindings')return Boolean((d.bindings||[]).length);
 if(name==='contour')return Boolean((d.contour||{}).drop||(d.contour||{}).approve_join);
 if(name==='view')return d.view!=null;if(name==='trace')return Boolean(d.trace_acknowledged);return false;}
function renderRedundantOptions(){const select=$('redundant-reference');if(!select||!state)return;
 const previous=select.value;select.replaceChildren();
 for(const row of calloutList()){if(row.id===selectedCallout)continue;const option=document.createElement('option');
  option.value=row.id;option.textContent=`${row.label} · ${row.source_kind==='manual'?'elle çizilen alan':'makine adayı'}`;select.append(option);}
 for(const name of Object.keys(DECISION_REF_LABEL))if(decisionRefPresent(name)){
  const option=document.createElement('option');option.value=`decision:${name}`;option.textContent=DECISION_REF_LABEL[name];select.append(option);}
 if(previous&&[...select.children].some(option=>option.value===previous))select.value=previous;
 if(!select.children.length){const option=document.createElement('option');option.value='';
  option.textContent='Dayanak yok: önce başka bir satırı ya da kararı tamamlayın';select.append(option);}}
function closeDispositionBoxes(){$('unsupported-box').hidden=true;$('unsupported-actions').hidden=true;
 $('redundant-box').hidden=true;$('redundant-actions').hidden=true;}
$('target-unbindable').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 if(row.disposition==='build_relevant_unsupported'||row.unbindable){command('set_disposition',{callout_id:row.id,disposition:null},closeDispositionBoxes);return;}
 closeDispositionBoxes();$('unsupported-box').hidden=false;$('unsupported-actions').hidden=false;
 $('unsupported-reason').value='';$('unsupported-reason').focus();
 status('Gerçek ölçü/not ama şu an uygulanamıyor: nedenini yazın — gerekçe kaydın parçası olur.');};
$('unsupported-cancel').onclick=()=>{closeDispositionBoxes();};
$('unsupported-save').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 const reason=$('unsupported-reason').value.trim();
 if(!reason)return status('Gerekçe boş olamaz: bu bilgi neden uygulanamıyor?',true);
 command('set_disposition',{callout_id:row.id,disposition:'build_relevant_unsupported',disposition_reason:reason},closeDispositionBoxes);};
$('target-redundant').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 if(row.disposition==='redundant'){command('set_disposition',{callout_id:row.id,disposition:null},closeDispositionBoxes);return;}
 closeDispositionBoxes();renderRedundantOptions();$('redundant-box').hidden=false;$('redundant-actions').hidden=false;
 status('Dayanak seçin: bu bilgiyi zaten temsil eden satır ya da karar hangisi?');};
$('redundant-cancel').onclick=()=>{closeDispositionBoxes();};
$('redundant-save').onclick=()=>{const row=calloutRow(selectedCallout);if(!row)return status('Önce bir ölçü/not seçin.',true);
 const reference=$('redundant-reference').value;
 if(!reference)return status('Dayanak seçin: hangi karar bu bilgiyi zaten temsil ediyor?',true);
 command('set_disposition',{callout_id:row.id,disposition:'redundant',duplicate_of:reference},closeDispositionBoxes);};
// render() sarmalayıcısı: her yeniden çizimde hedef paneli ve hazırlık tazelenir (okuma, karar değil).
function renderStrategy(){const box=$('strategy-choices');if(!box)return;
 // Sıra PLAN-25 §42'nin kendi listesidir; öneri gelmeyen tür de görünür kalır (kullanıcı yine seçebilir).
 const data=(state&&state.build_strategy)||{},labels=data.labels||{},decision=data.decision||null;
 const byKind=new Map((data.proposals||[]).map(row=>[row.kind,row]));
 const kinds=['extrude_profile','revolve_profile','multi_view_composite','unsupported'];
 box.replaceChildren(...kinds.map(kind=>{const row=byKind.get(kind)||{},pending=row.status==='capability_pending';
  const label=document.createElement('label');label.className='strategy-choice';
  const input=document.createElement('input');input.type='radio';input.name='strategy';input.value=kind;
  input.checked=!!(decision&&decision.kind===kind);input.disabled=!!pending;
  const span=document.createElement('span');span.textContent=row.label||labels[kind]||kind;
  if(pending){const note=document.createElement('small');note.className='muted';note.textContent=' (bu sürümde yok)';span.append(note);}
  else if(row.confidence==='high'){const note=document.createElement('small');note.className='muted';note.textContent=' (önerilir)';span.append(note);}
  label.append(input,span);return label;}));
 const stateText={missing:'Henüz seçilmedi — üretim bu kararı bekler.',
                  stale:'Karar güncel değil (profil, kontur, görüş ya da okuma değişti); yeniden onaylayın.',
                  current:`Seçili: ${labels[(decision||{}).kind]||(decision||{}).kind||''}`}[data.state]||'';
 text('strategy-state',stateText);
 const rows=[];for(const row of (data.proposals||[])){if(row.reasons&&row.reasons.length)rows.push(row.reasons.join(' '));
  for(const item of (row.evidence||[]))rows.push(`${item.kind}: ${item.detail}`);}
 text('strategy-evidence',rows.length?[...new Set(rows)].join('\n'):'Kanıt satırı yok.');
 $('strategy-save').disabled=!(state&&state.decisions);}
$('strategy-save').onclick=()=>{const picked=document.querySelector('input[name="strategy"]:checked');
 if(!picked)return status('Önce bir oluşturma biçimi seçin.',true);
 if(picked.disabled)return status('Bu seçenek bu sürümde yok.',true);
 chooseStrategy(picked.value);};
render=(base=>function(){base();renderTarget();renderStrategy();loadReadiness();})(render);
