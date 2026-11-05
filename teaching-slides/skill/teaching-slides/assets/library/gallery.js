'use strict';
const catalog=JSON.parse(document.getElementById('catalog-data').textContent);
const previews=JSON.parse(document.getElementById('preview-data').textContent);
const $=id=>document.getElementById(id);
const labels={reference:'参考素材',tried:'已有改编案例',reusable:'可复用经验',retired:'已退役'};
const storeKey='teaching-slides-feedback-v1';
let observations=[], active=null, currentIndex=0, compareIndex=1, comparing=false, storageWorks=true;
const reasonDrafts=new Map();
function draftKey(){return active.id+'|'+exampleRef(active.examples[currentIndex]).id;}
function saveReasonDraft(){if(active)reasonDrafts.set(draftKey(),$('reason').value);}
try {
  const raw=JSON.parse(localStorage.getItem(storeKey)||'[]');
  if(Array.isArray(raw)) observations=raw;
  localStorage.setItem(storeKey,JSON.stringify(observations));
} catch(e) { storageWorks=false; $('storage-note').textContent='当前仅保存在本页，请在关闭前导出。'; }
function updateQueue(){
  $('export').disabled=!observations.length;
  $('export').textContent=`导出反馈（${observations.length}）`;
  if(storageWorks) try { localStorage.setItem(storeKey,JSON.stringify(observations)); }
  catch(e){storageWorks=false;$('storage-note').textContent='当前仅保存在本页，请在关闭前导出。';}
}
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function section(parent,title,text){parent.append(el('h3',title),el('p',text));}
function list(parent,title,items){const ul=el('ul');items.forEach(item=>ul.append(el('li',item)));parent.append(el('h3',title),ul);}
function exampleLabel(ex,index){return ex.label||`例 ${index+1} · 第 ${ex.slide} 页`;}
function exampleRef(ex){return {id:ex.id||`${ex.source_id}:${ex.slide}`,source_id:ex.source_id,slide:ex.slide,preview_sha256:ex.sha256};}
function showExample(index){
  saveReasonDraft();
  currentIndex=index;
  if(compareIndex===currentIndex)compareIndex=(currentIndex+1)%active.examples.length;
  renderDetail();
  $('reason').value=reasonDrafts.get(draftKey())||'';
}
function renderDetail(){
  const ex=active.examples[currentIndex];
  $('detail-title').textContent=active.title;
  $('detail-image').src=previews[ex.preview];
  $('detail-image').alt=active.title+'：'+exampleLabel(ex,currentIndex);
  $('main-caption').textContent=exampleLabel(ex,currentIndex)+' · 当前观察对象';
  const tabs=$('example-tabs');tabs.replaceChildren();
  active.examples.forEach((example,index)=>{
    const button=el('button',exampleLabel(example,index),'secondary example-tab');
    button.type='button';button.setAttribute('role','tab');button.setAttribute('aria-selected',String(index===currentIndex));
    button.tabIndex=index===currentIndex?0:-1;
    button.addEventListener('click',()=>showExample(index));
    button.addEventListener('keydown',event=>{
      if(!['ArrowLeft','ArrowRight'].includes(event.key))return;
      event.preventDefault();const step=event.key==='ArrowRight'?1:-1;
      showExample((currentIndex+step+active.examples.length)%active.examples.length);
      $('example-tabs').children[currentIndex].focus();
    });
    tabs.append(button);
  });
  $('compare-toggle').hidden=active.examples.length<2;
  $('compare-toggle').textContent=comparing?'返回单例预览':'并排比较';
  $('compare-toggle').setAttribute('aria-pressed',String(comparing));
  $('preview-pair').classList.toggle('comparing',comparing);
  $('compare-figure').hidden=!comparing;
  $('compare-select-label').hidden=!comparing;
  const select=$('compare-select');select.replaceChildren();
  active.examples.forEach((example,index)=>{
    if(index===currentIndex)return;
    const option=el('option',exampleLabel(example,index));option.value=String(index);select.append(option);
  });
  if(comparing){
    select.value=String(compareIndex);
    const second=active.examples[compareIndex];
    $('compare-image').src=previews[second.preview];
    $('compare-image').alt=active.title+'：'+exampleLabel(second,compareIndex);
    $('compare-caption').textContent=exampleLabel(second,compareIndex)+' · 比较参考';
  }
  const source=catalog.sources.find(s=>s.id===ex.source_id);
  const area=$('detail-copy');area.replaceChildren();
  section(area,'表达目的',active.intent);section(area,'空间组织',active.spatial_form);
  list(area,'可以怎样变化',active.adaptations);list(area,'使用时留意',active.caveats);
  section(area,'当前例子的来源',`${source.title} · 第 ${ex.slide} 页 · ${labels[active.status]}`);
  if(ex.note)section(area,'这个例子的变化',ex.note);
  area.append(el('p',`已做：${active.evidence.map(e=>e.label).join('；')}。证据仅表示所列检查；实际使用效果以项目反馈记录为准。`));
  $('feedback-example').textContent='观察对象：'+exampleLabel(ex,currentIndex);
}
function openDetail(pattern){
  active=pattern;currentIndex=0;compareIndex=1;comparing=false;
  $('feedback-note').textContent='';$('reason').value=reasonDrafts.get(draftKey())||'';renderDetail();$('detail').showModal();
}
function render(){
  const query=$('search').value.trim().toLocaleLowerCase(), relation=$('relation').value, status=$('lifecycle').value;
  const matches=catalog.patterns.filter(p=>(!query||JSON.stringify(p).toLocaleLowerCase().includes(query))&&(!relation||p.relationships.includes(relation))&&(!status||p.status===status));
  const grid=$('grid');grid.replaceChildren();
  matches.forEach(p=>{
    const card=el('article',undefined,'card');card.dataset.pattern=p.id;
    const imageButton=el('button',undefined,'preview');imageButton.type='button';imageButton.setAttribute('aria-label',`查看 ${p.title}`);
    const img=el('img');img.src=previews[p.examples[0].preview];img.alt=p.title+'的来源页';img.loading='lazy';imageButton.append(img);
    imageButton.addEventListener('click',()=>openDetail(p));
    const open=el('button',`查看 ${p.examples.length} 个例子与变化`,'open');open.type='button';open.addEventListener('click',()=>openDetail(p));
    card.append(imageButton,el('h2',p.title),el('div',p.relationships.map(r=>catalog.relationships[r]).join(' · '),'meta'),el('p',p.intent),el('p',`${labels[p.status]} · ${p.examples.length} 个来源页`),open);
    grid.append(card);
  });
  $('results').textContent=`显示 ${matches.length} / ${catalog.patterns.length} 种表达 · ${matches.reduce((n,p)=>n+p.examples.length,0)} 个来源页`;
  if(!matches.length)grid.append(el('p','暂时没有匹配的参考，可以清除筛选或发展新的表达。','empty'));
}
Object.entries(catalog.relationships).forEach(([key,value])=>{const option=el('option',value);option.value=key;$('relation').append(option);});
$('edition').textContent=`v${catalog.version} · ${catalog.updated}`;
$('distribution-label').textContent=catalog.distribution==='public-preview'?'公开预览 · 离线浏览':'私人试点 · 离线浏览';
const represented=new Set(catalog.patterns.flatMap(p=>p.relationships));
const gaps=Object.entries(catalog.relationships).filter(([key])=>!represented.has(key)).map(([,value])=>value);
$('gaps').textContent=gaps.length?'待真实案例补充的关系：'+gaps.join('、')+'。':'这些分类已有参考，仍可继续发展新的表达。';
['search','relation','lifecycle'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
$('close').addEventListener('click',()=>$('detail').close());
$('detail').addEventListener('close',saveReasonDraft);
$('compare-toggle').addEventListener('click',()=>{comparing=!comparing;renderDetail();});
$('compare-select').addEventListener('change',()=>{compareIndex=Number($('compare-select').value);renderDetail();});
$('feedback-form').addEventListener('submit',event=>{
  event.preventDefault();const project=$('project-name').value.trim();
  const obs={id:'fb-'+(crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(36).slice(2)),
    pattern_id:active.id,example_ref:exampleRef(active.examples[currentIndex]),scope:$('scope').value,
    target:$('target').value.trim(),action:$('action').value,reason:$('reason').value.trim(),context:$('context').value,
    reporter:'user-via-gallery',created_at:new Date().toISOString(),project_id:project,delivery_blocking:$('delivery-blocking').checked};
  const output=$('output-version').value.trim();if(output)obs.output_id=output;
  if(!project||!obs.target||!obs.reason){$('feedback-note').textContent='请填写项目编号、具体对象及原因。';return;}
  observations.push(obs);updateQueue();$('feedback-note').textContent='已加入待导出反馈；尚未写入项目或修改例库。';$('reason').value='';
});
$('export').addEventListener('click',()=>{
  const batch={schema_version:1,project_id:null,observations};
  const blob=new Blob([JSON.stringify(batch,null,2)+'\n'],{type:'application/json'});
  const link=el('a');link.href=URL.createObjectURL(blob);link.download='teaching-slides-feedback.json';link.click();
  setTimeout(()=>URL.revokeObjectURL(link.href),1000);$('storage-note').textContent='已请求下载反馈文件；请确认保存，再导入对应项目。';
});
updateQueue();render();
