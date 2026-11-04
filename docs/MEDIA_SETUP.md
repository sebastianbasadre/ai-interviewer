# Demo audio and avatar

## Verified state

The room opens a WebRTC channel authenticated by the session cookie. Pipecat 1.15.0
receives microphone audio, Silero detects turns, and local Whisper detects language
without forcing Spanish. Piper originally used `en_US-lessac-high` for English and
`es_AR-daniela-high` for Spanish; the current female voice configuration is below.
Both modalities share the phase engine and text persistence. The initial report was
mock without numeric scores; optional real scoring is described in REPORTS.md.
The candidate's camera is not requested for the interview. This demo stores no audio
or video files, as stated in consent. Pilot audiovisual recording remains pending;
it is not claimed as implemented.

TavusVideoService is an optional stage between TTS and transport output. Without an API
key, Face, PAL Echo and explicit enablement, it is not instantiated and consumes no
minutes. An authorized real test was verified: Chrome received Anna video at 1280x720
and audio, Whisper transcribed a synthetic answer, and the engine advanced to warmup.
After closure, the Tavus API confirmed `ended`. No formal latency/synchronization
measurement exists. Media failures close the channel and allow text continuation;
automatic Tavus-to-audio fallback is not yet verified. Do not use this state for real
candidate interviews.

## Setup

Run in WSL2 with Python 3.12, from the project root:

```bash
python -m pip install -e '.[test,media]'
python -m pytest
```

Configure `.env` without printing values. Local demo example:

```dotenv
APP_MODE=mock
AVATAR_MODE=mock
REALTIME_ENABLED=true
TAVUS_ENABLED=false
TTS_PROVIDER=piper
PIPER_VOICE=es_AR-daniela-high
PIPER_ENGLISH_VOICE=en_GB-jenny_dioco-medium
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
MEDIA_MAX_MINUTES=3
PUBLIC_BASE_URL=https://192.168.2.6:8443
LISTEN_PORT=8443
TLS_CERT_FILE=/private/path/server.crt
TLS_KEY_FILE=/private/path/server.key
TURN_URL=turn:192.168.2.6:3479?transport=tcp
```

Startup prepares local models; the first run downloads weights. Preparation errors
disable media while keeping text available. `/admin/health` reports `media_ready` and
still requires `X-Admin-Key`. SDKs are not imported in text-only mode.

This configuration limits media to one global connection and three minutes per connection.
Tavus also receives `properties.max_call_duration`, bounded by remaining interview time,
`MEDIA_MAX_MINUTES` and `TAVUS_MAX_MINUTES_PER_SESSION`. Disconnecting media preserves
the original interview deadline rather than resetting the 30-minute maximum. There is
no cumulative global Tavus spending reservation: keep it disabled until the test budget
is agreed and monitored.

## HTTPS and WSL NAT

The launcher listens only on loopback. Windows homelab portproxy forwards
`192.168.2.6:8443` to `127.0.0.1:8443` and `:3479` to `127.0.0.1:3479`. Firewall:
TCP 8443/3479 from `192.168.2.0/24` only. HTTP port 8000 runs
`python -m ai_interviewer.redirect`, redirecting browsers to HTTPS while preserving
invitation paths without access logging.

The development certificate includes IP and localhost SANs. No root authority was
installed on devices: browsers may warn until the certificate is explicitly trusted.
Use a hostname and trusted certificate for stable deployment. Certificates/keys remain
under `data/tls/`, outside Git.

System Coturn 4.5.2 serves TURN over TCP 3479 with temporary HMAC credentials issued only
to authenticated sessions. `TURN_SHARED_SECRET` matches coturn's `static-auth-secret`
and is never sent to browsers. Browsers use `relay` to traverse WSL NAT. UDP relay ports
49160–49200 stay inside WSL; do not expose that range to the LAN. The initial demo
configuration and PID were under `data/`. Restarting WSL may change its relay IP;
update `relay-ip` and restart coturn if needed. The initial demo processes were not
registered as system startup services.

Operational correction: the system coturn service now uses the application's TURN
configuration. An earlier mismatched system configuration prevented authenticated
ICE relay allocation even though the TCP port was reachable. Chrome relay gathering
was verified after correcting the configuration. The browser allows up to 25 seconds
for ICE preparation.

## Configure and repeat an avatar test

1. Set `TAVUS_API_KEY`, `TAVUS_FACE_ID` and `TAVUS_PAL_ID` in `.env`; do not paste them
   into chats. Create the PAL with `pipeline_mode: "echo"`: Tavus only renders Piper
   speech and does not control the script. Do not use a full conversational PAL.
   Create it using `POST /v2/pals` with this body:

   ```json
   {"pal_name": "AI Interviewer Echo", "pipeline_mode": "echo", "default_face_id": "rc9cff32ceba"}
   ```

   `TAVUS_REPLICA_ID` is accepted as a legacy alias when `TAVUS_FACE_ID` is empty;
   Face takes precedence when both are set. The alias adapts existing configuration,
   not account resources; it does not automatically convert or verify them.
2. Agree estimated minutes and cost with the owner before enabling Tavus (G4).
3. Set `AVATAR_MODE=tavus`, `TAVUS_ENABLED=true` and restart the runtime.
4. Create a new invitation. `media-tavus-v1` consent explains that Tavus receives the
   synthetic interviewer voice. Text/local-audio consent does not authorize this new
   recipient; existing interviews are not silently converted.
5. Connect the microphone and check speech, video, synchronization, interruption and
   remote closure. Record actual duration/usage. End or disconnect after the test.

Verified sources: installed code and the official Pipecat v1.15.0 example:
https://github.com/pipecat-ai/pipecat/blob/v1.15.0/examples/video-avatar/video-avatar-tavus-video-service.py

## Face/PAL compatibility

The pinned SDK still uses `replica_id` and `persona_id` in its constructor and REST calls.
`pipeline/tavus_compat.py` adapts only its HTTP session without modifying the SDK:

- `POST /v2/conversations` sends `face_id`, `pal_id`, duration limit and recording disabled.
- `GET /v2/personas/{id}` becomes `GET /v2/pals/{id}`; return `pal_name` to the SDK as
  `persona_name`, without propagating PAL prompts or tool keys.
- `POST /v2/conversations/{id}/end` retains the current endpoint.

Pipecat still handles `conversation.echo` audio, interruptions, video and cleanup.
The adapter permits only those endpoints and disables HTTP redirects. Tests exercise
real Pipecat 1.15 clients/constructors against a session double, without network or cost.
This verifies software compatibility, not the G4 live-video test.

Verified REST contract: https://docs.tavus.io/openapi.yaml.
Echo guide: https://docs.tavus.io/sections/conversational-video-interface/echo-mode.

## Language and continuity update (2026-11-04)

Consent, room and review interfaces use English. Audiovisual interviews start in English
and locally detect English/Spanish answers using langdetect. Short or ambiguous answers
retain the previous language. "Spanish please" and "English please" change language
without advancing the phase. Language is reconstructed from the transcript on resume.
Questions use fixed translations; detection neither changes the rubric nor lets a model
control phases.

Voices download/load during media preparation. VAD waits for 0.8 seconds of silence;
noise detection alone does not interrupt TTS. Only a recognized transcription triggers
interruption. The browser tolerates up to eight seconds of transient disconnection.
Closing speech plays before media shutdown.

The test environment's Tavus budget remains one minute per connection until explicitly
extended, enforced by both provider and local process. Local test without Tavus:
22 seconds of WebRTC, 1036 received frames, 667 containing audio, with an English opening.
This does not replace a Tavus test on the user's network. Historical reports and citations
retain their original content.

## Female interviewer voice

English uses `PIPER_ENGLISH_VOICE=en_GB-jenny_dioco-medium`; Spanish retains
`PIPER_VOICE=es_AR-daniela-high`. Both are local Piper voices. English voice selection
is configurable rather than hardcoded. The room credits Jenny (Dioco), as required by
the dataset license: https://github.com/dioco-group/jenny-tts-dataset .
Voice changes apply to new media connections. The avatar provider is unchanged.
