"""Small, escaped HTML pages and self-hosted JavaScript (no third-party assets)."""
from html import escape
from uuid import UUID

STYLE = """
:root{font-family:system-ui,sans-serif;color:#172838;background:#f2f5f8}body{margin:0}
main{max-width:760px;margin:32px auto;padding:28px;background:white;border-radius:16px}
h1{font-size:1.7rem}p,li,label{line-height:1.6}button,input,textarea,select{font:inherit}
button{padding:12px 20px;border:0;border-radius:8px;background:#145b76;color:white;cursor:pointer}
button:disabled{opacity:.5;cursor:default}textarea{display:block;box-sizing:border-box;width:100%;min-height:120px;padding:12px}
label{display:block;margin:14px 0}a{color:#145b76}.note{padding:14px;background:#edf5f9;border-radius:8px}
#error{color:#9c2525;min-height:1.5em}#conversation{padding:0;list-style:none}#conversation li{margin:12px 0;padding:12px;background:#f2f5f8;border-radius:8px;white-space:pre-wrap}
#conversation .candidate{background:#e9f5ef}video{width:100%;max-height:240px;background:#172838;border-radius:8px}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}[hidden]{display:none!important}
@media(max-width:600px){main{margin:0;padding:20px;border-radius:0}button{width:100%}}
"""


def shell(title: str, body: str, script: str) -> str:
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{STYLE}</style><script src="/assets/{script}.js" defer></script></head><body><main>{body}</main></body></html>'


def consent_page(token: str, days: int, contact: str) -> str:
    return shell("Consentimiento — entrevista IA", f"""
<h1>Antes de empezar</h1>
<p>Soy un entrevistador de IA; esta entrevista se graba y la revisa una persona. La decisión final siempre es humana.</p>
<p>Esta sala permite una entrevista en texto: se guardan tus respuestas y la transcripción. Audio y video todavía no están habilitados; no se capturan durante la entrevista en texto.</p>
<p>El equipo responsable de la entrevista podrá revisar la transcripción y el reporte. Se conservarán durante {days} días desde el cierre; podés solicitar su borrado a <strong>{escape(contact)}</strong>.</p>
<p>El reporte evalúa únicamente el contenido de tus respuestas. No evalúa voz, imagen, acento ni apariencia. Evitá compartir datos sensibles que no sean necesarios para hablar de tu experiencia profesional.</p>
<p>Podés terminar en cualquier momento. Si preferís una alternativa con una persona, pedísela al equipo responsable.</p>
<form id="consent" data-action="/i/{escape(token, quote=True)}/consent">
<label><input type="checkbox" id="accepted" required> Entiendo que interactúo con una IA y acepto que se registren mis respuestas para la revisión humana descrita.</label>
<button type="submit">Aceptar y entrar</button></form><p id="error" role="alert"></p>
""", "consent")


def room_page(token: str, interview_id: UUID) -> str:
    return shell("Sala de entrevista", f"""
<h1>Tu entrevista</h1><p class="note" id="status" role="status">La entrevista se realiza en texto. El registro comienza cuando elegís Empezar.</p>
<div id="room" data-start="/i/{escape(token, quote=True)}/start" data-session="/session/{interview_id}">
<p>Audio y avatar todavía no están disponibles. Podés probar tus dispositivos de forma local, sin grabarlos ni enviarlos al servidor.</p>
<video id="preview" muted playsinline hidden></video><div class="actions"><button id="devices" type="button">Probar micrófono y cámara</button><button id="start" type="button">Empezar o continuar</button><button id="finish" type="button" disabled>Terminar entrevista</button></div>
<ol id="conversation" aria-live="polite"></ol>
<form id="answer"><label for="text">Tu respuesta</label><textarea id="text" maxlength="12000" required disabled></textarea><button type="submit" id="send" disabled>Enviar respuesta</button></form>
<form id="survey" hidden><h2>Tu experiencia</h2><label>¿Las instrucciones fueron claras? <select id="clarity">{options()}</select></label><label>¿Te sentiste tratado/a justamente? <select id="fairness">{options()}</select></label><label>Comentario opcional<textarea id="comment" maxlength="2000"></textarea></label><button type="submit">Enviar encuesta</button></form>
</div><p id="error" role="alert"></p>
""", "room")


def options() -> str:
    return ''.join(f'<option value="{i}">{i} — {label}</option>' for i, label in [(1, "muy poco"), (2, "poco"), (3, "intermedio"), (4, "bastante"), (5, "mucho")])


CONSENT_JS = r"""
'use strict';
const form=document.querySelector('#consent'), error=document.querySelector('#error');
form.addEventListener('submit',async event=>{
 event.preventDefault(); error.textContent='';
 const button=form.querySelector('button'); button.disabled=true;
 try {
  const response=await fetch(form.dataset.action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accepted:document.querySelector('#accepted').checked})});
  const data=await response.json(); if(!response.ok) throw new Error(data.detail||'No se pudo guardar el consentimiento.');
  location.assign(data.room);
 }catch(e){error.textContent=e.message;button.disabled=false;}
});
"""

ROOM_JS = r"""
'use strict';
const room=document.querySelector('#room'), status=document.querySelector('#status'), error=document.querySelector('#error');
const start=document.querySelector('#start'), finish=document.querySelector('#finish'), text=document.querySelector('#text'), send=document.querySelector('#send');
let active=false, stream=null;
function append(speaker,message){const item=document.createElement('li');item.className=speaker;item.textContent=(speaker==='candidate'?'Vos: ':'Entrevistador IA: ')+message;document.querySelector('#conversation').append(item);}
function controls(busy){start.disabled=busy||active;finish.disabled=busy||!active;text.disabled=busy||!active;send.disabled=busy||!active;}
async function post(path,body={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.detail||'No se pudo completar la solicitud.');return data;}
function decision(d){if(d.text)append('interviewer',d.text);if(d.end_session){active=false;status.textContent='Entrevista finalizada. El equipo humano revisará tus respuestas.';document.querySelector('#survey').hidden=false;}else{active=true;status.textContent='Registro de la conversación activo. Podés terminar cuando quieras.';}}
start.addEventListener('click',async()=>{controls(true);error.textContent='';try{const d=await post(room.dataset.start);decision(d.decision);}catch(e){error.textContent=e.message;}finally{controls(false);}});
document.querySelector('#answer').addEventListener('submit',async event=>{event.preventDefault();if(!active)return;controls(true);error.textContent='';const answer=text.value;try{const d=await post(room.dataset.session+'/turn',{text:answer});append('candidate',answer);text.value='';decision(d);}catch(e){error.textContent=e.message;}finally{controls(false);}});
finish.addEventListener('click',async()=>{controls(true);error.textContent='';try{decision(await post(room.dataset.session+'/finish'));}catch(e){error.textContent=e.message;}finally{controls(false);}});
document.querySelector('#survey').addEventListener('submit',async event=>{event.preventDefault();error.textContent='';try{await post(room.dataset.session+'/survey',{clarity:Number(document.querySelector('#clarity').value),fairness:Number(document.querySelector('#fairness').value),comment:document.querySelector('#comment').value});event.target.hidden=true;status.textContent='Gracias por compartir tu experiencia.';}catch(e){error.textContent=e.message;}});
function stopDevices(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}document.querySelector('#preview').hidden=true;}
document.querySelector('#devices').addEventListener('click',async()=>{error.textContent='';stopDevices();try{stream=await navigator.mediaDevices.getUserMedia({audio:true,video:true});const preview=document.querySelector('#preview');preview.srcObject=stream;preview.hidden=false;await preview.play();setTimeout(stopDevices,8000);}catch(e){error.textContent='No se pudo acceder a los dispositivos. Podés continuar en texto.';}});
window.addEventListener('pagehide',stopDevices);
"""
