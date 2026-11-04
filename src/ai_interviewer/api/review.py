"""Reviewer shell: data requires X-Admin-Key; the browser keeps it only in memory."""
REVIEW_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Interview review</title>
<style>
:root{font-family:system-ui,sans-serif;color:#172838;background:#f2f5f8}body{margin:0}
main{max-width:1100px;margin:32px auto;padding:28px;background:white;border-radius:16px}
h1{font-size:1.8rem}h2{font-size:1.3rem}p,label{line-height:1.6}input,button{font:inherit}
button{padding:10px 16px;border:0;border-radius:8px;background:#145b76;color:white;cursor:pointer}
button:disabled{opacity:.5;cursor:default}input{padding:10px;border:1px solid #9aadb8;border-radius:6px;max-width:90%;width:360px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #dde5eb;vertical-align:top}
th{font-weight:600;background:#f2f5f8}.note{padding:14px;background:#edf5f9;border-radius:8px}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.score{font-size:1.25rem;font-weight:650}
.competency{padding:20px 0;border-bottom:1px solid #dde5eb}blockquote{margin:12px 0;padding:12px 16px;background:#f2f5f8;border-left:3px solid #8da8b4;white-space:pre-wrap}
.muted{color:#506575}.alert{padding:12px;background:#fff3da;border-radius:6px}#error{color:#9c2525}[hidden]{display:none!important}
@media(max-width:700px){main{margin:0;padding:18px;border-radius:0}table{font-size:.85rem}td,th{padding:8px}}
</style><script src="/assets/review.js" defer></script></head><body><main>
<h1>Interview review</h1><p class="note">Each report combines three transcript evaluations. Review the citations, rubric and unresolved issues before making a decision.</p>
<form id="login"><label for="admin-key">Admin key</label><br><input id="admin-key" type="password" autocomplete="off" required>
<button type="submit">Sign in</button><p class="muted">Use ADMIN_API_KEY from your .env file. The key is kept in this page only until you sign out or reload.</p></form>
<div id="workspace" hidden><div class="actions"><button id="refresh">Refresh list</button><button id="logout">Sign out</button></div>
<p id="status" role="status"></p><div style="overflow-x:auto"><table><thead><tr><th>Interview</th><th>Role</th><th>Session</th><th>Report</th><th>Actions</th></tr></thead><tbody id="interviews"></tbody></table></div>
<section id="report" hidden><div class="actions"><button id="download">Download HTML</button></div><div id="report-content"></div></section></div>
<p id="error" role="alert"></p></main></body></html>"""

REVIEW_JS = r"""
'use strict';
let adminKey='', timer=null, selected=null, polling=false;
const error=document.querySelector('#error'), workspace=document.querySelector('#workspace');
const states={invited:'Invited',consented:'Consented',active:'In progress',completed:'Completed',aborted:'Interrupted'};
const reportStates={not_generated:'Not generated',queued:'Queued',running:'Generating',ready:'Ready',failed:'Failed to generate'};
const alerts={scoring_dispersion:'Evaluations differ by more than one point. Review the reasoning carefully.',inconsistent_evidence:'An evaluation found insufficient evidence. These aspects were left unscored.',injection_attempt:'Candidate instructions were detected and excluded from evaluation.',sensitive_data_excluded:'Excerpts containing sensitive information were excluded.',analysis_fallback:'Fallback questions were used for some answers.',mock_scoring:'Test report: does not contain real scores.'};
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
async function api(path,options={}){const response=await fetch(path,{...options,headers:{'X-Admin-Key':adminKey,...options.headers}});if(!response.ok){let message='Could not complete the request.';try{message=(await response.json()).detail||message;}catch(e){}if(response.status===401)logout();throw new Error(message);}return response;}
function logout(){clearInterval(timer);timer=null;adminKey='';selected=null;workspace.hidden=true;document.querySelector('#login').hidden=false;document.querySelector('#admin-key').value='';document.querySelector('#interviews').replaceChildren();document.querySelector('#report-content').replaceChildren();document.querySelector('#report').hidden=true;}
async function load(){
 if(polling||!adminKey)return;polling=true;
 try{const data=await(await api('/admin/interviews')).json();const body=document.querySelector('#interviews');body.replaceChildren();
  document.querySelector('#status').textContent=data.scoring_enabled?(data.auto_generate?'Reports are generated automatically after interviews with current consent end.':'Real report generation is enabled.'):'New reports use mock scoring.';
  for(const item of data.interviews){const row=node('tr');row.append(node('td',item.name),node('td',item.role_id),node('td',states[item.status]||item.status),node('td',(reportStates[item.report_status]||item.report_status)+(item.report_kind==='mock'?' · mock':'')));
   const actions=node('td');if(item.report_status==='ready'){const view=node('button','View report');view.addEventListener('click',()=>show(item.id).catch(e=>error.textContent=e.message));actions.append(view);}else if(['completed','aborted'].includes(item.status)){const generate=node('button',item.report_status==='failed'?'Retry · 3 evaluations':'Generate · 3 evaluations');generate.disabled=['queued','running'].includes(item.report_status);generate.addEventListener('click',async()=>{generate.disabled=true;error.textContent='';try{await api('/admin/interviews/'+item.id+'/report',{method:'POST'});await load();await show(item.id);}catch(e){error.textContent=e.message;}finally{generate.disabled=false;}});actions.append(generate);}row.append(actions);body.append(row);
  }
  if(!data.interviews.length){const row=node('tr'),cell=node('td','No interviews yet.');cell.colSpan=5;row.append(cell);body.append(row);}
 }catch(e){error.textContent=e.message;}finally{polling=false;}
}
async function show(id){
 const data=await(await api('/admin/interviews/'+id+'/review')).json();selected=id;const report=data.report,content=document.querySelector('#report-content');content.replaceChildren();
 content.append(node('h2','Report · '+data.interview.name),node('p','Human review pending','note'),node('p',report.summary),node('p',report.recommendation));
 const date=new Date(report.generated_at);content.append(node('p','Generated: '+date.toLocaleString()+' · Three evaluations per competency','muted'));
 for(const flag of report.flags){if(alerts[flag])content.append(node('p',alerts[flag],'alert'));}
 const evidence=new Map(data.evidence.map(turn=>[turn.id,turn.text]));
 for(const score of report.scores){const section=node('section',undefined,'competency');section.append(node('h3',data.competencies[score.competency_id]||score.competency_id),node('p',score.score===null?'Insufficient evidence':score.score+' / 5','score'),node('p',score.rationale));
  if(score.dispersion>0)section.append(node('p','Evaluation spread: '+score.dispersion+' point(s).','muted'));
  const anchors=data.rubric?.[score.competency_id]||[];if(anchors.length){const details=node('details'),list=node('ul');details.append(node('summary','View rubric anchors'));for(const anchor of anchors)list.append(node('li',anchor.score+' / 5 · '+anchor.description));details.append(list);section.append(details);}
  for(const turnId of score.evidence_turn_ids){const quote=node('blockquote',evidence.get(turnId)||'Citation unavailable.');quote.dataset.turnId=turnId;section.append(quote,node('p','Turn '+turnId,'muted'));}content.append(section);
 }
 content.append(node('h3','Follow-up questions'));const questions=node('ul');for(const question of report.suggested_questions)questions.append(node('li',question));if(!report.suggested_questions.length)questions.append(node('li','Review the relevance of citations and the limits of the example provided.'));content.append(questions);
 document.querySelector('#report').hidden=false;document.querySelector('#report').scrollIntoView({behavior:'smooth'});
}
document.querySelector('#login').addEventListener('submit',async event=>{event.preventDefault();error.textContent='';adminKey=document.querySelector('#admin-key').value;document.querySelector('#admin-key').value='';try{await api('/admin/interviews');document.querySelector('#login').hidden=true;workspace.hidden=false;await load();timer=setInterval(load,5000);}catch(e){adminKey='';error.textContent=e.message;}});
document.querySelector('#refresh').addEventListener('click',load);document.querySelector('#logout').addEventListener('click',logout);
document.querySelector('#download').addEventListener('click',async()=>{if(!selected)return;try{const response=await api('/admin/interviews/'+selected+'/report.html');const url=URL.createObjectURL(await response.blob());const link=node('a');link.href=url;link.download='report-'+selected+'.html';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error.textContent=e.message;}});
window.addEventListener('pagehide',logout);
"""
