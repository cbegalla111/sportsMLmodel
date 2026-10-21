'use strict';
let state=null,league='NBA';
const $=id=>document.getElementById(id);
const esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>typeof x==='number'?x.toFixed(4):'—';
function error(e){$('error').textContent=e.message||e;$('error').hidden=false;}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(state?{'X-CSRF-Token':state.csrf}:{})},...(body?{body:JSON.stringify(body)}:{})});const j=await r.json();if(!r.ok)throw Error(j.error);return j;}
function table(headers,rows){return '<table><thead><tr>'+headers.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';}
async function refresh(){state=await api('/api/state');$('login').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;render();}
function render(){const l=state.leagues.find(x=>x.name===league),e=l.experiment;
$('leagues').innerHTML=state.leagues.map(x=>`<button data-league="${x.name}" class="${x.name===league?'selected':''}">${x.name}</button>`).join('');
$('count').textContent=l.n.toLocaleString();$('freshness').textContent=l.data_through||'No data';$('status').textContent=e?'Historical test complete':'Not validated';
$('notice').textContent=l.n?'Historical data available. Current forecasts require fresh data and sufficient history.':'No real data loaded for this league. Import documented results; models and probabilities are withheld until validated.';
$('home').innerHTML=$('away').innerHTML=l.teams.map(t=>`<option>${esc(t)}</option>`).join('');if(l.teams.length>1)$('away').selectedIndex=1;
$('date').value=l.data_through?new Date(Date.parse(l.data_through)+86400000).toISOString().slice(0,10):new Date().toISOString().slice(0,10);
$('feature-list').textContent='Optional sport features: '+l.features.join(', ')+'. Prefix each with home_ or away_. CSV features also require feature_asof.';
$('sources').textContent=league==='NBA'&&l.n?'Bundled import: FiveThirtyEight historical NBA results (CC BY 4.0), upstream Basketball-Reference. Additional uploads retain row-level source labels. Exact downloads and timestamps are saved in sources/nba-manifest.json.':'CSV/manual sources are user supplied and not independently verified.';
const feed=JSON.parse(state.settings['feed_'+league]||'{}');
const fixtures=feed.status==='ok' && Date.now()-Date.parse(feed.checked)<86400000 ? (feed.upcoming||[]) : [];
$('schedule-status').textContent=fixtures.length?'✓ '+fixtures.length+' upcoming fixtures from the current source feed':'○ Current schedule unavailable or stale';
$('fixtures').innerHTML='<option value="">Choose a source-backed fixture</option>'+fixtures.map((f,i)=>`<option value="${i}">${esc(f.date+' · '+f.home+' / '+f.away)}</option>`).join('');
$('fixtures').onchange=()=>{const f=fixtures[$('fixtures').value];if(!f)return;$('date').value=f.date;for(const k of ['home','away']){if(![...$(k).options].some(o=>o.value===f[k]))$(k).add(new Option(f[k],f[k]));$(k).value=f[k];}};
$('feed-status').textContent=feed.checked?'Last feed attempt: '+feed.checked+' · '+feed.status+(feed.error?' · '+feed.error:''):'No automatic feed configured; CSV/manual fallback.';
$('stale').textContent=l.data_through?(Math.floor((Date.now()-Date.parse(l.data_through))/86400000)>30?'STALE · current forecasts withheld':'Recent results · key availability inputs missing'):'No source connected';
$('prediction').innerHTML='';$('models').innerHTML=e?table(['Candidate','Selection log loss','Status'],e.candidates.map(c=>[c.name,c.status==='completed'?fmt(c.mean_log_loss):c.reason,c.name===e.selected?'SELECTED':c.status])):'No experiment yet. At least 700 decisive events across 100 dates required.';
$('metrics').innerHTML=e?`<h3>${esc(e.selected)} · untouched final test</h3>${table(['Metric','Result'],[['Sample size',e.test.n],['Log loss',fmt(e.test.log_loss)],['Brier',fmt(e.test.brier)],['Accuracy',fmt(e.test.accuracy)],['ROC-AUC',fmt(e.test.roc_auc)],['Elo Brier baseline',fmt(e.baseline_test.brier)],['Brier 95% block interval',e.test.brier_week_block_bootstrap_95.map(fmt).join(' – ')]])}<p class="note">${esc(e.test.interval_note)}</p><p class="note">Final period: ${esc(e.final_test_start)} through ${esc(e.last_date)}. ${esc(e.calibration)}</p><p class="note">Dataset SHA-256: ${esc(e.dataset_sha256)}</p>`:'';
$('calibration-table').innerHTML=e?table(['Probability band','n','Mean forecast','Observed'],e.test.calibration.map(b=>[b.band.join('–'),b.n,fmt(b.predicted),fmt(b.observed)])):'';
$('seasons').innerHTML=e?'<h3>Final-test performance by season</h3>'+table(['Season','n','Log loss','Brier'],Object.entries(e.test.by_season||e.test.by_year).map(([year,m])=>[year,m.n,fmt(m.log_loss),fmt(m.brier)]))+`<p class="note">${esc(e.limitations.join(' '))}</p>`:'';
if(l.sources.length)$('sources').textContent=l.sources.join(' · ');
plot(e?.test.calibration||[]);
const history=state.history.filter(p=>p.league===league).sort((a,b)=>Math.max(b.home_probability,b.away_probability)-Math.max(a.home_probability,a.away_probability));
$('history').innerHTML=history.length?table(['Date','Matchup','Most likely','Probability','Mode','Outcome','Saved UTC'],history.map(p=>[p.date,p.home+' / '+p.away,p.home_probability>=.5?p.home:p.away,(100*Math.max(p.home_probability,p.away_probability)).toFixed(1)+'%',p.mode,p.eventual_outcome,p.created])):'No saved predictions.';
}
function plot(bins){const c=$('calibration'),x=c.getContext('2d'),w=c.width,h=c.height;x.clearRect(0,0,w,h);x.strokeStyle='#40515f';x.beginPath();x.moveTo(45,20);x.lineTo(45,h-40);x.lineTo(w-20,h-40);x.stroke();x.setLineDash([5,5]);x.beginPath();x.moveTo(45,h-40);x.lineTo(w-20,20);x.stroke();x.setLineDash([]);x.fillStyle='#91a4b3';x.font='12px system-ui';x.fillText('Observed win frequency',50,15);x.fillText('Predicted probability  0 → 1',145,h-10);x.fillText('0',25,h-38);x.fillText('1',25,25);for(const b of bins){x.fillStyle='#8de0b3';x.beginPath();x.arc(45+b.predicted*(w-65),h-40-b.observed*(h-60),5,0,2*Math.PI);x.fill();}}
async function action(fn){$('error').hidden=true;try{await fn();}catch(e){error(e);}}
$('login-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('/api/login',{password:$('password').value});$('password').value='';await refresh();});};
$('leagues').onclick=e=>{if(e.target.dataset.league)action(async()=>{league=e.target.dataset.league;render();await api('/api/settings',{league});});};
$('logout').onclick=()=>action(async()=>{await api('/api/logout',{});state=null;$('workspace').hidden=true;$('login').hidden=false;$('logout').hidden=true;});
$('train').onclick=()=>action(async()=>{$('train').disabled=true;$('train').textContent='Running fixed-budget comparison…';try{await api('/api/train',{league});await refresh();}finally{$('train').disabled=false;$('train').textContent='Run chronological comparison';}});
$('prediction-form').onsubmit=e=>{e.preventDefault();action(async()=>{const p=await api('/api/predict',{league,home:$('home').value,away:$('away').value,event_date:$('date').value,scenario:$('scenario').checked,overrides:JSON.parse($('overrides').value||'{}')});await refresh();$('prediction').innerHTML=`<div class="prob"><span>${esc(p.home)} ${(p.home_probability*100).toFixed(1)}%</span><span>${esc(p.away)} ${(p.away_probability*100).toFixed(1)}%</span></div><div class="bar"><span></span></div><p class="note">${esc(p.mode)} · conditional on decisive outcome. ${esc(p.availability)}</p>${table(['Factor','Input difference','Log-odds contribution'],p.factors.map(f=>[f.factor,fmt(f.difference),fmt(f.log_odds_contribution)]))}<p class="note">${esc(p.explanation)}</p>`;$('prediction').querySelector('.bar span').style.width=(p.home_probability*100)+'%';});};
$('upload-form').onsubmit=e=>{e.preventDefault();action(async()=>{const csv=await $('csv').files[0].text();const r=await api('/api/import',{csv});await refresh();$('notice').textContent=r.accepted_rows+' validated rows accepted (duplicate identical IDs are idempotent).';});};
$('manual-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('/api/manual',{game:{event_id:$('manual-id').value,league,date:$('manual-date').value,home:$('manual-home').value,away:$('manual-away').value,home_score:$('manual-hs').value,away_score:$('manual-as').value,outcome:$('manual-outcome').value,source:$('manual-source').value,neutral:$('manual-neutral').checked?'1':'0'}});await refresh();});};
api('/api/state').then(s=>{state=s;league=s.settings.league||'NBA';$('login').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;render();}).catch(()=>{});

// Development-only live refresh; the server enables this explicitly, behind login.
setInterval(async()=>{
  if(!state?.preview_revision || document.hidden)return;
  try{
    const r=await fetch('/api/revision');
    if(!r.ok)return;
    const next=await r.json();
    if(next.revision && next.revision!==state.preview_revision)location.reload();
  }catch(_){} // A stopped/restarting development server must not discard user state.
},2000);
