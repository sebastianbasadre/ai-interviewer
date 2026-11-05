"""Small, escaped HTML pages and self-hosted JavaScript (no third-party assets)."""
from html import escape
from uuid import UUID

STYLE = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#233c35;background:#f7f8f4;font-synthesis:none;--green:#236348;--muted:#6a7770;--line:#e0e5dc}*{box-sizing:border-box}body{margin:0}button,input,textarea,select{font:inherit}button,a,input,textarea,select{-webkit-tap-highlight-color:transparent}button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #97bfa6;outline-offset:4px}button{display:inline-flex;align-items:center;justify-content:center;gap:9px;border:1px solid transparent;border-radius:10px;padding:13px 20px;background:var(--green);color:#fff;font-weight:600;font-size:14px;cursor:pointer;transition:background .18s,transform .18s}button:hover:not(:disabled){background:#184c36;transform:translateY(-1px)}button:disabled{opacity:.45;cursor:default}.secondary{background:white;border-color:var(--line);color:#31483b}.secondary:hover:not(:disabled){background:#eff3ec}.quiet{background:transparent;color:var(--muted);border-color:transparent}.quiet:hover:not(:disabled){background:#e9eee5;color:#233c35}.danger{background:transparent;border-color:#dbd4cf;color:#9a4e43}.danger:hover:not(:disabled){background:#fbede8}a{color:var(--green)}h1,h2,h3,p{margin-top:0}h1{font-weight:500;letter-spacing:-1.6px;font-size:42px;line-height:1.15;margin-bottom:12px}h2{font-size:21px;font-weight:550;letter-spacing:-.4px}h3{font-size:14px;font-weight:650}p,label,li{line-height:1.65}p{font-size:14px}.muted{color:var(--muted)}.eyebrow{text-transform:uppercase;letter-spacing:2px;font-size:10px;font-weight:700;color:var(--green);margin-bottom:14px}.app-header{max-width:1240px;margin:auto;height:88px;padding:0 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:11px;font-weight:650;font-size:18px;letter-spacing:-.5px}.brand-symbol{width:30px;height:30px;display:grid;place-items:center;background:var(--green);color:white;border-radius:9px}.brand-symbol svg{width:19px;height:19px}.header-note{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#7b9b7c;flex-shrink:0}main{max-width:1240px;margin:0 auto;padding:44px 40px 20px}.page-heading{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:28px}.page-heading p{margin:0;color:var(--muted);max-width:600px}.pill{display:inline-flex;align-items:center;gap:8px;white-space:nowrap;border:1px solid var(--line);border-radius:30px;padding:9px 13px;font-size:11px;background:#fff;color:#5b6e5e}.room-grid{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:24px;align-items:start}.stage-card{border:1px solid #dfe4da;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 5px 20px #243f2710}.stage{position:relative;isolation:isolate;aspect-ratio:16/10;background:#142d27;overflow:hidden;color:#edf3e9}.stage::before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(ellipse at 50% 65%,#2b5141 0%,#1a362c 45%,#112820 100%)}.stage-top{position:absolute;top:20px;left:22px;right:22px;display:flex;justify-content:space-between;align-items:center;z-index:2;pointer-events:none}.stage-label{display:inline-flex;align-items:center;gap:8px;background:#12271ec9;border:1px solid #ffffff18;border-radius:24px;padding:7px 11px;font-size:10px;font-weight:500;color:#dce9d9}.stage .dot{background:#9bbba0}.stage-number{font-size:11px;letter-spacing:.5px;color:#b5c8b5}.stage-placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center;padding:60px 24px}.orb{height:112px;width:112px;border:1px solid #9eb69a40;border-radius:50%;display:grid;place-items:center;margin-bottom:26px;box-shadow:0 0 0 18px #c3d9b705,0 0 0 36px #c3d9b704;background:radial-gradient(circle at 35% 30%,#638867,#304e3b 65%)}.soundwave{display:flex;align-items:center;gap:5px;height:38px}.soundwave i{display:block;width:4px;border-radius:4px;background:#d2e5c4;height:18px}.soundwave i:nth-child(2),.soundwave i:nth-child(4){height:28px}.soundwave i:nth-child(3){height:38px}.stage-placeholder h2{font-size:22px;font-weight:400;margin:0 0 8px;color:#f0f4eb}.stage-placeholder p{font-size:12px;color:#a8c0ab;margin:0;max-width:300px}.stage:has(#avatar:not([hidden])) .stage-placeholder{display:none}#avatar{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#142d27}.stage-bottom{position:absolute;bottom:18px;left:22px;z-index:2;font-size:10px;color:#c5d5c3;letter-spacing:.2px}.stage-bottom span{background:#132a20ca;border-radius:5px;padding:5px 8px}.stage-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px;flex-wrap:wrap}.stage-controls .actions{margin:0}.stage-caption{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}.actions{display:flex;flex-wrap:wrap;gap:9px;margin:16px 0}#start{padding-left:24px;padding-right:24px}#connect-media:disabled,#disconnect-media:disabled{display:none}.status-line{display:flex;gap:10px;padding:17px 2px 0;align-items:baseline}.status-line .dot{margin-top:7px}.status-line p{color:var(--muted);font-size:12px;margin:0}#media-status:empty{display:none}.side-card{border:1px solid var(--line);background:#fff;border-radius:15px;padding:23px;margin-bottom:16px}.side-card h2{font-size:15px;letter-spacing:-.2px;margin-bottom:18px}.session-row{display:flex;justify-content:space-between;gap:10px;font-size:12px;margin:14px 0;color:var(--muted)}.session-row strong{font-weight:550;color:#324b3b;text-align:right}.side-card hr{border:0;border-top:1px solid var(--line);margin:20px 0}.check-list{list-style:none;padding:0;margin:0}.check-list li{display:flex;gap:11px;font-size:12px;line-height:1.5;color:#67766a;margin:14px 0}.check-mark{width:18px;height:18px;flex-shrink:0;border-radius:50%;display:grid;place-items:center;background:#eef4e9;color:#537b4c;font-size:11px}.side-card .secondary{width:100%;font-size:12px;padding:11px 8px}.language-card{background:#edf2e7;border:1px solid #e1e8d9;border-radius:15px;padding:22px}.language-card h3{margin-bottom:7px}.language-card p{font-size:12px;margin:0;color:#62735e}.language-badges{display:flex;gap:6px;margin-top:14px}.language-badges span{font-size:10px;border:1px solid #d1ddc7;background:#f6f9f1;color:#527249;padding:4px 8px;border-radius:5px}.room-note{padding-top:20px;margin-top:20px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:11px}.room-note p{font-size:11px;margin:0}.room-note .quiet{font-size:11px;padding:0 0 0 8px;white-space:nowrap}.app-footer{max-width:1240px;margin:0 auto;padding:26px 40px;display:flex;justify-content:space-between;gap:16px;color:#889185;font-size:10px;letter-spacing:.15px}.app-footer span:last-child{color:#6d7e69}#error{color:#a04436;border-radius:10px;font-size:13px;line-height:1.6;margin:12px 0}#error:not(:empty){padding:14px 18px;background:#fff0e9;border:1px solid #efd8cc}#device-status{font-size:12px;margin-bottom:10px}#device-status:empty{display:none}#preview{width:100%;border-radius:10px;margin:14px 0 10px;max-height:210px;background:#142d27}meter{width:100%;height:12px;accent-color:var(--green)}#conversation{padding:0;list-style:none;margin-top:24px}#conversation li{padding:17px 20px;margin:10px 0;background:#fff;border:1px solid var(--line);border-radius:12px;font-size:14px;white-space:pre-wrap}#conversation .candidate{background:#ecf2e5;border-color:#dce6d3}textarea{display:block;width:100%;min-height:115px;padding:15px;border:1px solid #ccd7c8;border-radius:10px;background:#fff;color:#233c35;resize:vertical;margin-bottom:12px}label{display:block;font-size:13px;margin:14px 0}select{background:#fff;padding:9px;border:1px solid var(--line);border-radius:7px;max-width:100%}#answer,#survey{background:#fff;border:1px solid var(--line);border-radius:15px;padding:24px;margin-top:20px}.consent-layout{display:grid;grid-template-columns:290px minmax(0,1fr);gap:64px;align-items:start;max-width:1040px;margin:8px auto 28px}.consent-intro{position:sticky;top:30px}.consent-intro h1{font-size:42px}.consent-intro>p{color:var(--muted)}.consent-content{background:#fff;border:1px solid var(--line);border-radius:18px;padding:32px}.consent-content>p{font-size:13px;line-height:1.8;color:#5c6e61}.consent-content>p:first-child{font-weight:550;color:#2e4839}.consent-content strong{overflow-wrap:anywhere}.consent-content form{border-top:1px solid var(--line);padding-top:14px;margin-top:22px}.consent-content form label{display:flex;align-items:flex-start;gap:12px;color:#3e5345;cursor:pointer}.consent-content input{margin:5px 0 0;accent-color:var(--green);width:18px;height:18px;flex-shrink:0}.consent-content button{width:100%;margin-top:12px}.consent-intro .side-card{margin-top:26px;background:transparent}.note{padding:14px;background:#edf2e7;border-radius:10px}[hidden]{display:none!important}
@media(min-width:1400px){main{padding-top:52px}.stage{aspect-ratio:16/9}}
@media(max-width:950px){.room-grid{grid-template-columns:minmax(0,1fr) 250px;gap:18px}.side-card,.language-card{padding:18px}h1{font-size:34px}.consent-layout{grid-template-columns:240px minmax(0,1fr);gap:30px}.stage{aspect-ratio:4/3}.stage-controls{padding:15px}.stage-caption{display:none}}
@media(max-width:740px){.app-header{height:70px;padding:0 22px}main{padding:30px 20px 12px}.header-note{font-size:10px}.brand{font-size:16px}.page-heading{align-items:flex-start;margin-bottom:23px;gap:12px}.page-heading .pill{font-size:0;padding:10px;gap:0}.page-heading h1{font-size:32px;letter-spacing:-1px}.page-heading p{font-size:12px}.room-grid{grid-template-columns:1fr}.stage{aspect-ratio:4/3}.stage-top{left:16px;right:16px;top:16px}.stage-bottom{left:16px}.stage-controls{gap:10px}.stage-controls .actions{flex:1}.stage-controls #start{flex:1}.stage-placeholder h2{font-size:20px}.orb{width:90px;height:90px;margin-bottom:22px}.side-column{display:grid;grid-template-columns:1fr 1fr;gap:14px}.side-card{margin-bottom:0}.language-card{grid-column:1/-1}.language-badges{margin-top:10px}.room-note{align-items:flex-start}.app-footer{padding:20px;font-size:9px}.consent-layout{display:block;margin:0}.consent-intro{position:static}.consent-intro h1{font-size:36px}.consent-intro .side-card{display:none}.consent-content{padding:22px;margin-top:25px}.consent-intro>p{max-width:440px}}
@media(max-width:400px){.side-column{grid-template-columns:1fr}.language-card{grid-column:auto}.stage-placeholder{padding:50px 16px}.stage-number{display:none}.stage-label{font-size:9px}.app-footer{flex-direction:column;gap:7px}.room-note{flex-direction:column;gap:12px}}
#svg-avatar{position:absolute;inset:0;width:100%;height:100%;background:#142d27}.stage:has(#svg-avatar:not([hidden])) .stage-placeholder{display:none}@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
"""


def shell(title: str, body: str, script: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#236348"><title>{escape(title)}</title><style>{STYLE}</style><script src="/assets/{script}.js" defer></script></head><body><header class="app-header"><div class="brand"><span class="brand-symbol" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 7v10M10 4v16M15 7v10M20 10v4" stroke-linecap="round"/></svg></span>interview<span class="muted">/</span></div><span class="header-note"><span class="dot" aria-hidden="true"></span>AI conversation · Human perspective</span></header><main>{body}</main><footer class="app-footer"><span>A little space to share your experience.</span><span>AI assisted. Human reviewed.</span></footer></body></html>'''


def consent_page(token: str, days: int, contact: str, *, realtime: bool = False, tavus: bool = False, anthropic: bool = False, scoring: bool = False) -> str:
    media_notice = ("You can speak through your microphone and hear the interviewer. Whisper and Piper process audio on this server. Only the transcript is stored, not audio files. Your camera is not required." if realtime else
                    "This room supports a text interview. Your answers and the transcript are stored. Audio and video are not enabled or captured in text mode.")
    if tavus:
        media_notice += " Tavus receives the synthetic interviewer voice to generate its video avatar. The avatar is AI generated, not a person. Please review the Tavus privacy policy before accepting."
    if anthropic:
        media_notice += " Anthropic receives questions and filtered excerpts of your answers for the current competency to identify whether the situation, your actions or the outcome need clarification."
    if scoring:
        media_notice += " After the interview, Anthropic receives the rubric and filtered professional excerpts of the transcript to propose competency scores with citations. A person reviews the report. Insufficient evidence is left unscored."
    elif anthropic:
        media_notice += " Final candidate evaluation is still in test mode."
    return shell("Consent — AI interview", f"""
<div class="consent-layout"><section class="consent-intro"><p class="eyebrow">A thoughtful conversation</p><h1>Before you start</h1><p>A chance to share the experience, decisions and ideas that make you, you.</p><div class="side-card"><h2>Made for a real conversation</h2><ul class="check-list"><li><span class="check-mark" aria-hidden="true">✓</span>Your experience, in your own words</li><li><span class="check-mark" aria-hidden="true">✓</span>English or Spanish — your choice</li><li><span class="check-mark" aria-hidden="true">✓</span>Every decision stays human</li></ul></div></section><section class="consent-content" aria-label="Interview information and consent">
<p>I am an AI interviewer. This interview is recorded as a transcript and reviewed by a person. The final decision is always made by a human.</p>
<p>{media_notice}</p>
<p>The interview team can review the transcript and report. They will be retained for {days} days after the interview ends. To request deletion, contact <strong>{escape(contact)}</strong>.</p>
<p>The report assesses only the content of your answers, not your voice, image, accent or appearance. Avoid sharing sensitive information unrelated to your professional experience.</p>
<p>You can end the interview at any time. Contact the team if you prefer an interview with a person.</p>
<form id="consent" data-action="/i/{escape(token, quote=True)}/consent">
<label><input type="checkbox" id="accepted" required> I understand that I am interacting with an AI and consent to my answers being recorded for the human review described above.</label>
<button type="submit">Accept and enter <span aria-hidden="true">→</span></button></form><p id="error" role="alert"></p></section></div>
""", "consent")


def room_page(token: str, interview_id: UUID, *, realtime: bool = False, tavus: bool = False, svg: bool = False, english_voice: str = "") -> str:
    media_notice = ("Start automatically connects your microphone and the interviewer. Use headphones to prevent echo. Your camera is not required. Answer in English or Spanish; the interviewer will follow your language." if realtime else
                    "Audio and avatar are not available yet. You can test your devices locally without recording or uploading them.")
    if realtime and not tavus:
        media_notice += " The video avatar is not enabled yet."
    voice_credit = '<p>English voice: Jenny (Dioco)</p>' if realtime and english_voice == "en_GB-jenny_dioco-medium" else ""
    return shell("Interview room", f"""
<div class="page-heading"><div><p class="eyebrow">Your interview space</p><h1>A conversation about you.</h1><p>Bring your experience. We will take it one question at a time.</p></div><span class="pill"><span class="dot" aria-hidden="true"></span><span id="session-state">Ready when you are</span></span></div>
<div id="room" data-start="/i/{escape(token, quote=True)}/start" data-session="/session/{interview_id}" data-realtime="{str(realtime).lower()}">
<div class="room-grid"><section aria-label="Interview conversation">
<div class="stage-card"><div class="stage">
<div class="stage-top"><span class="stage-label"><span class="dot" aria-hidden="true"></span>AI INTERVIEWER</span><span class="stage-number">YOUR STORY. YOUR PACE.</span></div>
<div class="stage-placeholder"><div class="orb" aria-hidden="true"><div class="soundwave"><i></i><i></i><i></i><i></i><i></i></div></div><h2 id="stage-title">{"Your interviewer will be here" if tavus else "Your conversation starts here"}</h2><p id="stage-hint">{"Take a breath. When you are ready, start the conversation." if realtime else "Share your experience in the text conversation below."}</p></div>
<svg id="svg-avatar" viewBox="0 0 400 500" xmlns="http://www.w3.org/2000/svg" hidden aria-hidden="true"><defs><radialGradient id="av-sg" cx="38%" cy="30%" r="65%"><stop offset="0%" stop-color="#f0d0a0"/><stop offset="100%" stop-color="#c89050"/></radialGradient><radialGradient id="av-sg2" cx="38%" cy="30%" r="65%"><stop offset="0%" stop-color="#d4a870"/><stop offset="100%" stop-color="#b87840"/></radialGradient></defs><rect width="400" height="500" fill="#142d27"/><ellipse cx="200" cy="430" rx="260" ry="190" fill="#1a3028"/><polygon points="170,418 200,458 230,418 218,398 200,413 182,398" fill="#f8f4ee"/><polygon points="78,500 170,418 182,398 128,500" fill="#1e3830"/><polygon points="322,500 230,418 218,398 272,500" fill="#1e3830"/><ellipse cx="200" cy="395" rx="28" ry="30" fill="url(#av-sg)"/><ellipse cx="200" cy="225" rx="98" ry="118" fill="url(#av-sg)"/><path d="M 103 190 Q 102 93 200 83 Q 298 93 297 190 Q 290 133 260 110 Q 230 93 200 91 Q 170 93 140 110 Q 110 133 103 190 Z" fill="#2a1c10"/><ellipse cx="102" cy="238" rx="12" ry="17" fill="url(#av-sg2)"/><ellipse cx="298" cy="238" rx="12" ry="17" fill="url(#av-sg2)"/><path d="M 148 183 Q 168 174 192 180" stroke="#2a1c10" stroke-width="4" fill="none" stroke-linecap="round"/><path d="M 208 180 Q 232 174 252 183" stroke="#2a1c10" stroke-width="4" fill="none" stroke-linecap="round"/><ellipse cx="170" cy="207" rx="21" ry="13" fill="white"/><ellipse cx="170" cy="207" rx="10" ry="10" fill="#5a3e28"/><ellipse cx="170" cy="207" rx="5.5" ry="5.5" fill="#120e08"/><ellipse cx="174" cy="203" rx="2.5" ry="2" fill="white" opacity="0.9"/><ellipse cx="230" cy="207" rx="21" ry="13" fill="white"/><ellipse cx="230" cy="207" rx="10" ry="10" fill="#5a3e28"/><ellipse cx="230" cy="207" rx="5.5" ry="5.5" fill="#120e08"/><ellipse cx="234" cy="203" rx="2.5" ry="2" fill="white" opacity="0.9"/><ellipse id="av-bl" cx="170" cy="207" rx="21" ry="0" fill="url(#av-sg)"/><ellipse id="av-br" cx="230" cy="207" rx="21" ry="0" fill="url(#av-sg)"/><ellipse cx="200" cy="258" rx="7" ry="5" fill="#b07838" opacity="0.4"/><ellipse id="av-cav" cx="200" cy="302" rx="33" ry="1" fill="#5a1a16"/><rect id="av-teeth" x="167" y="295" width="66" height="12" rx="3" fill="white" opacity="0"/><path id="av-lip-t" d="M 166 302 Q 183 295 200 297 Q 217 295 234 302" fill="#c08068" stroke="#a06050" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path id="av-lip-b" d="M 166 302 Q 200 310 234 302" fill="#c08068" stroke="#a06050" stroke-width="2" stroke-linecap="round"/></svg><video id="avatar" autoplay playsinline hidden aria-label="AI generated interviewer avatar"></video><audio id="interviewer-audio" autoplay></audio>
<div class="stage-bottom"><span>AI generated · Reviewed by a person</span></div>
</div><div class="stage-controls"><div class="stage-caption"><span class="dot" aria-hidden="true"></span><span id="connection-label">{"Microphone not connected" if realtime else "Text interview"}</span></div><div class="actions"><button id="start" type="button">Start or resume <span aria-hidden="true">→</span></button><button id="finish" class="danger" type="button" disabled hidden>End interview</button></div></div></div>
<div class="status-line"><span class="dot" aria-hidden="true"></span><div><p id="status" role="status">{"Start to meet the interviewer and discuss your professional background in voice and video." if realtime else "This is a text interview. Recording starts when you select Start."}</p><p id="media-status" role="status"></p></div></div>
<div class="actions" {'hidden' if not realtime else ''}><button id="connect-media" class="secondary" type="button" disabled>Reconnect interviewer</button><button id="disconnect-media" class="quiet" type="button" disabled>Disconnect audio/video</button><button id="mute" class="secondary" type="button" hidden aria-pressed="false">Mute microphone</button></div>
<p id="error" role="alert"></p>
<ol id="conversation" aria-live="polite" {"hidden" if realtime else ""}></ol>
<form id="answer" {"hidden" if realtime else ""}><label for="text">Your answer</label><textarea id="text" maxlength="12000" placeholder="Share a specific example from your experience…" required disabled></textarea><button type="submit" id="send" disabled>Send answer <span aria-hidden="true">→</span></button></form>
<form id="survey" hidden><p class="eyebrow">Thank you for your time</p><h2>How was your experience?</h2><label>Were the instructions clear? <select id="clarity">{options()}</select></label><label>Did you feel you were treated fairly? <select id="fairness">{options()}</select></label><label>Optional comment<textarea id="comment" maxlength="2000" placeholder="Anything you would like us to know?"></textarea></label><button type="submit">Send feedback</button></form>
</section><aside class="side-column" aria-label="Interview preparation">
<section class="side-card"><h2>The conversation</h2><div class="session-row"><span>Focus</span><strong>Product experience</strong></div><div class="session-row"><span>Format</span><strong>{"Voice & AI video" if tavus else "Voice & AI avatar" if (svg and realtime) else "Voice" if realtime else "Text"}</strong></div><div class="session-row"><span>Review</span><strong>Always human</strong></div><hr><p class="muted" style="font-size:12px;margin:0">Real examples are all you need. There is no perfect answer.</p></section>
<section class="side-card"><h2>A quick sound check</h2><ul class="check-list"><li><span class="check-mark" aria-hidden="true">✓</span>Find a quiet, comfortable spot</li><li><span class="check-mark" aria-hidden="true">✓</span>Headphones help prevent echo</li><li><span class="check-mark" aria-hidden="true">✓</span>Your camera is optional</li></ul><button id="devices" class="secondary" type="button">Test microphone & camera</button><video id="preview" muted playsinline hidden aria-label="Local camera preview"></video><p id="device-status" role="status"></p><meter id="mic-level" min="0" max="1" value="0" hidden aria-label="Microphone level"></meter></section>
<section class="language-card"><h3>Your words. Your language.</h3><p>Start in English or Spanish. Your interviewer will follow your language naturally.</p><div class="language-badges"><span>English</span><span>Español</span></div></section>
</aside></div>
<div class="room-note"><div><p>Your camera is never sent to the interviewer. Only your answers are saved as a transcript.</p>{voice_credit}</div><button id="text-mode" class="quiet" type="button" {"hidden" if not realtime else ""}>Prefer to type? <span aria-hidden="true">↗</span></button></div>
<details class="muted" style="font-size:11px;margin-top:16px"><summary>About this interview</summary><p style="font-size:12px;margin-top:10px">{media_notice}</p></details>
</div>
""", "room")


def options() -> str:
    return ''.join(f'<option value="{i}">{i} — {label}</option>' for i, label in [(1, "not at all"), (2, "a little"), (3, "somewhat"), (4, "quite a lot"), (5, "very much")])


CONSENT_JS = r"""
'use strict';
const form=document.querySelector('#consent'), error=document.querySelector('#error');
form.addEventListener('submit',async event=>{
 event.preventDefault(); error.textContent='';
 const button=form.querySelector('button'); button.disabled=true;
 try {
  const response=await fetch(form.dataset.action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accepted:document.querySelector('#accepted').checked})});
  const data=await response.json(); if(!response.ok) throw new Error(data.detail||'Could not save consent.');
  location.assign(data.room);
 }catch(e){error.textContent=e.message;button.disabled=false;}
});
"""

ROOM_JS = r"""
'use strict';
const room=document.querySelector('#room'), status=document.querySelector('#status'), error=document.querySelector('#error');
const start=document.querySelector('#start'), finish=document.querySelector('#finish'), text=document.querySelector('#text'), send=document.querySelector('#send');
let active=false, ended=false, stream=null, peer=null, microphone=null, heartbeat=null, mediaBusy=false, deviceTimer=null, meterTimer=null, audioContext=null, disconnectTimer=null;
let svgMode=false,svgCtx=null,svgAna=null,svgRaf=null,svgOpen=0,svgBlink=null;
const realtime=room.dataset.realtime==='true';
const connectMedia=document.querySelector('#connect-media'), disconnectMedia=document.querySelector('#disconnect-media');
function append(speaker,message){const item=document.createElement('li');item.className=speaker;item.textContent=(speaker==='candidate'?'You: ':'AI interviewer: ')+message;document.querySelector('#conversation').append(item);}
function controls(busy){start.disabled=busy||active||ended;start.hidden=active||ended;finish.hidden=!active;document.querySelector('#session-state').textContent=ended?'Interview complete':mediaBusy?'Connecting…':active?'Conversation in progress':'Ready when you are';document.querySelector('#connection-label').textContent=peer?'Microphone connected':realtime?'Microphone not connected':'Text interview';document.querySelector('#mute').hidden=!microphone;finish.disabled=busy||!active;text.disabled=busy||!active||!!peer;send.disabled=busy||!active||!!peer;connectMedia.disabled=busy||!active||!!peer||mediaBusy;disconnectMedia.disabled=!peer;}
async function post(path,body={}){const r=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Could not complete the request.');return data;}
function decision(d){if(d.text)append('interviewer',d.text);if(d.end_session){ended=true;active=false;document.querySelector('#stage-title').textContent='Thank you for sharing your story.';document.querySelector('#stage-hint').textContent='Your interview is complete. A person will review your answers.';if(!peer)stopMedia();status.textContent='Interview complete. A human reviewer will review your answers.';document.querySelector('#survey').hidden=false;}else{active=true;status.textContent='Interview recording is active. You can end it at any time.';}}
start.addEventListener('click',async()=>{controls(true);error.textContent='';try{const ac=new AudioContext();await ac.resume();ac.close();}catch(_){}try{const d=await post(room.dataset.start);decision(d.decision);if(realtime)await connect();}catch(e){error.textContent=e.message;}finally{controls(false);}});
document.querySelector('#answer').addEventListener('submit',async event=>{event.preventDefault();if(!active)return;controls(true);error.textContent='';const answer=text.value;try{const d=await post(room.dataset.session+'/turn',{text:answer});append('candidate',answer);text.value='';decision(d);}catch(e){error.textContent=e.message;}finally{controls(false);}});
finish.addEventListener('click',async()=>{controls(true);error.textContent='';try{decision(await post(room.dataset.session+'/finish'));}catch(e){error.textContent=e.message;}finally{controls(false);}});
document.querySelector('#survey').addEventListener('submit',async event=>{event.preventDefault();error.textContent='';try{await post(room.dataset.session+'/survey',{clarity:Number(document.querySelector('#clarity').value),fairness:Number(document.querySelector('#fairness').value),comment:document.querySelector('#comment').value});event.target.hidden=true;status.textContent='Thank you for your feedback.';}catch(e){error.textContent=e.message;}});
function stopDevices(){clearTimeout(deviceTimer);clearInterval(meterTimer);if(audioContext){audioContext.close();audioContext=null;}if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}const preview=document.querySelector('#preview');preview.hidden=true;preview.srcObject=null;document.querySelector('#mic-level').hidden=true;}
function deviceError(e){return ({NotAllowedError:'Permission denied. Allow the microphone or camera in site permissions and system privacy settings.',NotFoundError:'No device found. Check that it is connected.',NotReadableError:'The device is busy or blocked. Close other apps using it.'})[e.name]||'Could not open device: '+e.message;}
document.querySelector('#devices').addEventListener('click',async()=>{
 error.textContent='';stopDevices();const result=document.querySelector('#device-status');
 if(!window.isSecureContext||!navigator.mediaDevices){error.textContent='Open this room over HTTPS to test your devices.';return;}
 if(peer){result.textContent='The interview is using your microphone. Disconnect audio/video before testing.';return;}
 result.textContent='Testing microphone…';
 try{
  stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
  audioContext=new AudioContext();await audioContext.resume();const analyser=audioContext.createAnalyser();audioContext.createMediaStreamSource(stream).connect(analyser);const samples=new Uint8Array(analyser.fftSize);const meter=document.querySelector('#mic-level');meter.hidden=false;
  meterTimer=setInterval(()=>{analyser.getByteTimeDomainData(samples);meter.value=Math.min(1,Math.sqrt(samples.reduce((sum,v)=>sum+((v-128)/128)**2,0)/samples.length)*4);},100);
  result.textContent='Microphone connected: speak and check the level indicator. Requesting optional camera…';
  try{const camera=await navigator.mediaDevices.getUserMedia({audio:false,video:true});camera.getTracks().forEach(t=>stream.addTrack(t));const preview=document.querySelector('#preview');preview.srcObject=camera;preview.hidden=false;await preview.play();result.textContent='Microphone and camera connected. Speak to check the level and check your camera preview. Local test lasts 15 seconds.';}
  catch(e){result.textContent='Microphone connected; camera is optional. '+deviceError(e);}
  deviceTimer=setTimeout(()=>{stopDevices();result.textContent+=' Test complete.';},15000);
 }catch(e){stopDevices();result.textContent=deviceError(e);}
});
document.querySelector('#mute').addEventListener('click',()=>{if(!microphone)return;const button=document.querySelector('#mute');const muted=button.getAttribute('aria-pressed')!=='true';microphone.getAudioTracks().forEach(track=>track.enabled=!muted);button.setAttribute('aria-pressed',String(muted));button.textContent=muted?'Unmute microphone':'Mute microphone';document.querySelector('#connection-label').textContent=muted?'Microphone muted':'Microphone connected';});
function stopMedia(){stopSvgAnimation();svgMode=false;if(active&&!ended){document.querySelector('#stage-title').textContent='Ready to reconnect';document.querySelector('#stage-hint').textContent='Reconnect the interviewer or continue by text below.';}document.querySelector('#mute').setAttribute('aria-pressed','false');document.querySelector('#mute').textContent='Mute microphone';clearTimeout(disconnectTimer);clearInterval(heartbeat);heartbeat=null;if(microphone){microphone.getTracks().forEach(t=>t.stop());microphone=null;}if(peer){peer.close();peer=null;}document.querySelector('#avatar').hidden=true;document.querySelector('#avatar').srcObject=null;document.querySelector('#interviewer-audio').srcObject=null;document.querySelector('#media-status').textContent='Microphone disconnected.';controls(false);}
async function disconnect(){stopMedia();try{await post(room.dataset.session+'/media/close');}catch(e){error.textContent=e.message;}}
disconnectMedia.addEventListener('click',disconnect);
document.querySelector('#text-mode').addEventListener('click',async()=>{await disconnect();document.querySelector('#conversation').hidden=false;document.querySelector('#answer').hidden=false;});
connectMedia.addEventListener('click',connect);
async function connect(){
 error.textContent='';if(!active||peer||mediaBusy)return;
 if(!window.isSecureContext){error.textContent='Open this room over HTTPS to enable the microphone.';return;}
 stopDevices();mediaBusy=true;controls(false);document.querySelector('#stage-title').textContent='Meeting your interviewer…';document.querySelector('#stage-hint').textContent='Setting up a space for your conversation.';document.querySelector('#conversation').hidden=true;document.querySelector('#answer').hidden=true;document.querySelector('#media-status').textContent='Connecting interviewer audio and video…';
 try{
  await post(room.dataset.session+'/media/close');
  microphone=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
  const config=await post(room.dataset.session+'/media/config');
  peer=new RTCPeerConnection({...config,bundlePolicy:'max-bundle'});
  const current=peer;
  microphone.getAudioTracks().forEach(track=>current.addTrack(track,microphone));
  current.addTransceiver('video',{direction:'recvonly'});
  current.addTransceiver('video',{direction:'inactive'});
  const channel=current.createDataChannel('chat');
  channel.addEventListener('open',()=>{heartbeat=setInterval(()=>{if(channel.readyState==='open')channel.send('ping');},1000);});
  channel.addEventListener('message',event=>{try{const msg=JSON.parse(event.data);if(msg.type==='interview-turn'){append('candidate',msg.candidate);decision(msg.decision);controls(false);}else if(msg.type==='media-ready'){document.querySelector('#stage-title').textContent='Your interviewer is here';document.querySelector('#stage-hint').textContent='Listen, then share your experience in your own words.';document.querySelector('#media-status').textContent=msg.avatar?'Microphone active · voice and avatar connected.':'Microphone active · voice connected.';if(msg.avatar==='svg'){svgMode=true;startSvgBlink();}}else if(msg.type==='media-error'){error.textContent=msg.message;disconnect();}}catch(e){error.textContent='Invalid audio message.';}});
  current.addEventListener('track',async event=>{
    const media=new MediaStream([event.track]);
    const isAudio=event.track.kind==='audio';
    const target=document.querySelector(isAudio?'#interviewer-audio':'#avatar');
    target.srcObject=media;
    if(!isAudio){target.addEventListener('loadeddata',()=>{target.hidden=false;},{once:true});}
    if(!isAudio){try{await target.play();}catch(_){}return;}
    async function tryPlay(){
      try{
        await target.play();
        document.querySelector('#media-status').textContent='Audio connected · listening for the interviewer.';
        startSvgAnimation(target);
        if(channel.readyState==='open')channel.send(JSON.stringify({type:'audio-ready'}));
      }catch(e){
        document.querySelector('#media-status').textContent='Click anywhere on the page to start audio.';
        document.addEventListener('click',function retry(){document.removeEventListener('click',retry);tryPlay();},{once:true});
      }
    }
    await tryPlay();
  });
  current.addEventListener('connectionstatechange',()=>{if(current!==peer)return;clearTimeout(disconnectTimer);if(['failed','closed'].includes(current.connectionState))disconnect();else if(current.connectionState==='disconnected'){document.querySelector('#media-status').textContent='Connection interrupted. Reconnecting…';disconnectTimer=setTimeout(()=>{if(current===peer&&current.connectionState==='disconnected')disconnect();},8000);}});
  await current.setLocalDescription(await current.createOffer());
  if(current.iceGatheringState!=='complete')await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Could not prepare the audio connection. Check connectivity to the TURN server and reconnect.')),25000);current.addEventListener('icegatheringstatechange',()=>{if(current.iceGatheringState==='complete'){clearTimeout(timer);resolve();}});});
  const answer=await post(room.dataset.session+'/offer',{sdp:current.localDescription.sdp,type:'offer'});
  await current.setRemoteDescription({sdp:answer.sdp,type:answer.type});
 }catch(e){error.textContent=e.message;await disconnect();}finally{mediaBusy=false;controls(false);}
}
function startSvgAnimation(el){
 const svg=document.querySelector('#svg-avatar');
 if(!svg||svgCtx)return;
 try{
  svgCtx=new AudioContext();
  svgAna=svgCtx.createAnalyser();
  svgAna.fftSize=256;svgAna.smoothingTimeConstant=0.6;
  const src=svgCtx.createMediaElementSource(el);
  src.connect(svgAna);src.connect(svgCtx.destination);
 }catch(e){return;}
 const data=new Uint8Array(svgAna.frequencyBinCount);
 const cav=svg.querySelector('#av-cav'),lipB=svg.querySelector('#av-lip-b'),teeth=svg.querySelector('#av-teeth');
 function tick(){
  svgRaf=requestAnimationFrame(tick);
  svgAna.getByteFrequencyData(data);
  let sum=0;for(let i=2;i<10;i++)sum+=data[i];
  const amp=sum/(8*255);
  svgOpen+=(amp-svgOpen)*0.25;
  const ry=svgOpen*22;
  cav.setAttribute('ry',ry.toFixed(1));
  lipB.setAttribute('d','M 166 302 Q 200 '+(302+ry*1.2).toFixed(1)+' 234 302');
  if(teeth)teeth.setAttribute('opacity',Math.min(0.9,(Math.max(0,svgOpen-0.15)*3)).toFixed(2));
 }
 tick();
 svg.hidden=false;
}
function stopSvgAnimation(){
 if(svgRaf){cancelAnimationFrame(svgRaf);svgRaf=null;}
 if(svgCtx){svgCtx.close();svgCtx=null;svgAna=null;}
 svgOpen=0;stopSvgBlink();
 const svg=document.querySelector('#svg-avatar');
 if(svg)svg.hidden=true;
}
function startSvgBlink(){
 stopSvgBlink();
 const svg=document.querySelector('#svg-avatar');
 if(svg)svg.hidden=false;
 function blink(){
  svgBlink=setTimeout(()=>{
   const bl=document.querySelector('#av-bl'),br=document.querySelector('#av-br');
   if(!bl){svgBlink=null;return;}
   bl.setAttribute('ry','13');br.setAttribute('ry','13');
   setTimeout(()=>{bl.setAttribute('ry','0');br.setAttribute('ry','0');blink();},130);
  },2800+Math.random()*2500);
 }
 blink();
}
function stopSvgBlink(){if(svgBlink){clearTimeout(svgBlink);svgBlink=null;}}
window.addEventListener('pagehide',()=>{stopDevices();stopMedia();fetch(room.dataset.session+'/media/close',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',keepalive:true}).catch(()=>{});});
"""
