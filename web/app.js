import {generateKey, encrypt, decrypt, toCents} from './paillier.js';
const $ = id => document.getElementById(id);
const clubs = [
  {id:'site-1',name:'Arts Collective',group:'north',amount:'1240.00',initial:'A'},
  {id:'site-2',name:'Robotics Society',group:'north',amount:'1860.00',initial:'R'},
  {id:'site-3',name:'Green Campus',group:'south',amount:'920.00',initial:'G'},
  {id:'site-4',name:'Music Circle',group:'south',amount:'1580.00',initial:'M'},
];
let key, mode='local', lastReceipt, busy=false, hostedAvailable=false, providerLabel='Hosted AI', traceData;
const formatter = new Intl.NumberFormat('en-SG',{minimumFractionDigits:2,maximumFractionDigits:2});
const averageFormatter = new Intl.NumberFormat('en-SG',{minimumFractionDigits:2,maximumFractionDigits:4});
for (const club of clubs) {
  const row=document.createElement('div'); row.className='record';
  const name=document.createElement('div'); name.className='record-name';
  const avatar=document.createElement('span'); avatar.className='club-avatar'; avatar.textContent=club.initial; avatar.setAttribute('aria-hidden','true');
  const info=document.createElement('div'); const strong=document.createElement('strong'); strong.textContent=club.name;
  const small=document.createElement('small'); small.textContent=(club.group==='north'?'North':'South')+' campus · '+club.id;
  info.append(strong,small);name.append(avatar,info);
  const label=document.createElement('label'); label.className='money-input';
  const dollar=document.createElement('span');dollar.textContent='$';
  const input=document.createElement('input');input.id=club.id;input.type='text';input.inputMode='decimal';input.value=club.amount;input.maxLength=8;input.setAttribute('aria-label',club.name+' budget in Singapore dollars');input.autocomplete='off';
  input.addEventListener('input',invalidate);label.append(dollar,input);row.append(name,label);$('records').append(row);
}
function stage(name,state){const node=$('stage-'+name);node.className=state;node.querySelector('.stage-state').textContent=state==='done'?'DONE':state==='working'?'ACTIVE':'READY';}
function invalidate(){if(busy)return;lastReceipt=null;traceData=null;$('download').disabled=true;$('result-label').textContent='YOUR COLLECTIVE VIEW';$('result-number').replaceChildren(document.createTextNode('Ready'));const sub=document.createElement('span');sub.textContent='for the big picture.';$('result-number').append(sub);$('result-description').textContent='Bring four encrypted contributions together and unlock a shared planning number.';$('result-badge').textContent='BROWSER-OWNED DECRYPTION';$('transcript').textContent='Run the workspace to inspect your encrypted records,\nvalidated plan and computation receipt.';$('trace-badge').textContent='AWAITING RUN';for(const name of ['encrypt','plan','compute','reveal'])stage(name,'');$('run-status').textContent='Your updated workspace is ready.';}
function showTrace(name){if(!traceData)return;$('transcript').textContent=JSON.stringify(traceData[name],null,2);$('transcript').scrollTop=0;for(const button of document.querySelectorAll('.trace-tab')){button.classList.toggle('active',button.dataset.trace===name);button.setAttribute('aria-pressed',String(button.dataset.trace===name));}}
const traceTabs=document.createElement('div');traceTabs.className='trace-tabs';traceTabs.setAttribute('role','group');traceTabs.setAttribute('aria-label','Inspect run details');for(const [name,label] of [['envelope','Encrypted request'],['validated_plan','Validated plan'],['receipt','Run receipt']]){const button=document.createElement('button');button.className='trace-tab';button.type='button';button.dataset.trace=name;button.textContent=label;button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>showTrace(name));traceTabs.append(button);}$('transcript').before(traceTabs);
function setMode(next){if(busy)return;mode=next;for(const name of ['local','hosted']){$(name+'-mode').classList.toggle('active',name===mode);$(name+'-mode').setAttribute('aria-pressed',String(name===mode));}$('mode-note').textContent=mode==='hosted'?providerLabel+' builds the plan from encrypted contributions.':'Explore the full encrypted workflow locally.';invalidate();}
$('local-mode').addEventListener('click',()=>setMode('local'));
$('hosted-mode').addEventListener('click',()=>setMode('hosted'));
$('operation').addEventListener('change',invalidate);
const nextFrame=()=>new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,20)));
function lock(value){busy=value;$('run').disabled=value;$('operation').disabled=value;$('local-mode').disabled=value;$('hosted-mode').disabled=value||!hostedAvailable;for(const club of clubs)$(club.id).disabled=value;}
fetch('/api/status').then(r=>r.json()).then(data=>{hostedAvailable=data.hosted_available;providerLabel=data.provider||'Hosted AI';$('hosted-mode').disabled=!hostedAvailable;$('evaluator-label').textContent=data.evaluator;if(hostedAvailable)setMode('hosted');}).catch(()=>{$('run-status').textContent='Start the local workspace server, then refresh this page.';});
$('run').addEventListener('click',async()=>{
  invalidate();
  let values;
  try{values=clubs.map(c=>toCents($(c.id).value));}catch(error){$('run-status').textContent=error.message;return;}
  lock(true);const started=performance.now();
  try{
    stage('encrypt','working');$('run-status').textContent='Creating browser-owned encryption and sealing your contributions…';await nextFrame();
    key ||= await generateKey();
    const records=[];for(let i=0;i<clubs.length;i++){const c=clubs[i];records.push({id:c.id,group:c.group,ciphertext:encrypt(values[i],key).toString()});await nextFrame();}
    stage('encrypt','done');stage('plan','working');$('run-status').textContent=mode==='hosted'?'Hosted AI is building an approved plan from encrypted records…':'The local planner is preparing the approved encrypted operation…';await nextFrame();
    const operation=$('operation').value;
    const response=await fetch('/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,operation,public_key:key.n.toString(),records})});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Please retry this encrypted run.');
    if(result.provider_envelope.public_key!==key.n.toString()||JSON.stringify(result.provider_envelope.records)!==JSON.stringify(records)||result.plan.operation!==operation)throw new Error('The returned run did not match this workspace. Please retry.');
    stage('plan','done');stage('compute','done');stage('reveal','working');await nextFrame();
    const numerator=decrypt(result.ciphertext,key);const resultCents=numerator/result.divisor;
    const expected=operation==='difference'?values[0]+values[1]-values[2]-values[3]:values.reduce((a,b)=>a+b,0)/(operation==='average'?values.length:1);
    if(resultCents!==expected)throw new Error('The local result check did not match. Please start a fresh run.');
    stage('reveal','done');
    const titles={total:'TOTAL EVENT BUDGET',average:'AVERAGE BUDGET PER CLUB',difference:'NORTH CAMPUS − SOUTH CAMPUS'};
    const copy={total:'Four private contributions. One collective budget to bring your next big idea to life.',average:'A shared benchmark, calculated from exact encrypted totals.',difference:'A clear campus-level comparison, calculated directly from encrypted contributions.'};
    const displayValue=(operation==='average'?averageFormatter:formatter).format(resultCents/100);
    $('result-label').textContent=titles[operation];$('result-number').replaceChildren();const currency=document.createElement('span');currency.className='currency';currency.textContent='SGD';$('result-number').append(currency,document.createTextNode(displayValue));
    $('result-description').textContent=copy[operation];$('result-badge').textContent='✓ EXACT RESULT VERIFIED LOCALLY';$('trace-badge').textContent=result.receipt.live_api?'LIVE API RUN':'LOCAL PLANNER RUN';
    traceData={envelope:result.provider_envelope,validated_plan:result.plan,receipt:result.receipt};showTrace('validated_plan');
    lastReceipt={product:'OrbitSum',...result.receipt,operation,plan:result.plan,result:{currency:'SGD',numerator_cents:numerator,divisor:result.divisor,display:displayValue},verified_locally:true,browser_duration_ms:Math.round(performance.now()-started),created_at:new Date().toISOString()};
    $('download').disabled=false;$('run-status').textContent='Verified in '+((performance.now()-started)/1000).toFixed(1)+'s · '+(result.receipt.live_api?'Live '+result.receipt.provider+' plan':'Local deterministic plan')+' · '+result.receipt.evaluator;
  }catch(error){$('run-status').textContent=error.message||'Please retry this encrypted run.';for(const name of ['encrypt','plan','compute','reveal'])if($('stage-'+name).classList.contains('working'))stage(name,'');}
  finally{lock(false);}
});
$('download').addEventListener('click',()=>{if(!lastReceipt)return;const blob=new Blob([JSON.stringify(lastReceipt,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='orbitsum-run-receipt.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
