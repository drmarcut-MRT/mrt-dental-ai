'use strict';
(() => {
  let active = null;
  const MAX_BYTES = 20 * 1024 * 1024;
  window.attachDictation = (root) => {
    root.querySelectorAll('textarea').forEach(target => {
      if (target.dataset.dictation) return;
      target.dataset.dictation = '1';
      const controls = document.createElement('div'); controls.className = 'actions';
      const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary'; button.textContent = 'Dictează în română';
      const status = document.createElement('span'); status.className = 'muted'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
      controls.append(button, status); target.parentElement.after(controls);
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !window.isSecureContext) {
        button.disabled = true; status.textContent = 'Dictarea necesită HTTPS sau localhost și un browser compatibil.'; return;
      }
      button.addEventListener('click', async () => {
        if (active?.button === button && active.recorder?.state === 'recording') { active.recorder.stop(); return; }
        if (active) { status.textContent = 'Încheie dictarea curentă înainte de a porni alta.'; return; }
        const session = {button, recorder: null, stream: null, timer: null, failed: false}; active = session;
        button.disabled = true; status.textContent = 'Permite accesul la microfon…';
        const cleanup = () => {
          clearTimeout(session.timer); session.stream?.getTracks().forEach(track => track.stop());
        };
        const reset = () => { cleanup(); if (active === session) active = null; button.disabled = false; button.textContent = 'Dictează în română'; button.setAttribute('aria-pressed', 'false'); };
        try {
          session.stream = await navigator.mediaDevices.getUserMedia({audio: true});
          const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
          session.recorder = new MediaRecorder(session.stream, mime ? {mimeType: mime} : {});
          const recorder = session.recorder; const chunks = []; let total = 0;
          recorder.ondataavailable = event => {
            if (event.data.size) { total += event.data.size; chunks.push(event.data); }
            if (total > MAX_BYTES && !session.failed) { session.failed = true; status.textContent = 'Înregistrarea depășește limita de 20 MB.'; if (recorder.state === 'recording') recorder.stop(); }
          };
          recorder.onerror = () => {
            session.failed = true; status.textContent = 'Înregistrarea audio a eșuat.';
            if (recorder.state === 'recording') recorder.stop(); reset();
          };
          recorder.onstop = async () => {
            cleanup(); button.disabled = true; button.textContent = 'Se transcrie…';
            try {
              if (session.failed) return;
              const blob = new Blob(chunks, {type: recorder.mimeType || mime || 'audio/webm'});
              if (blob.size < 100) throw new Error('Nu s-a înregistrat audio utilizabil.');
              const type = blob.type; const extension = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
              const data = new FormData(); data.append('audio', blob, 'dictare.' + extension);
              status.textContent = 'Se transcrie în română…';
              const response = await fetch('/api/transcribe', {method: 'POST', body: data});
              const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Transcrierea a eșuat.');
              if (!result.text?.trim()) throw new Error('Nu s-a detectat text în înregistrare.');
              if (!target.isConnected) throw new Error('Câmpul a fost închis. Repetă dictarea în câmpul dorit.');
              target.value = target.value.trimEnd() + (target.value.trim() ? '\n' : '') + result.text.trim();
              target.dispatchEvent(new Event('input', {bubbles: true})); status.textContent = 'Text adăugat. Verifică transcrierea înainte de salvare.';
            } catch (error) { status.textContent = error.message; } finally { reset(); }
          };
          recorder.start(250); button.disabled = false; button.textContent = 'Oprește și transcrie'; button.setAttribute('aria-pressed', 'true');
          status.textContent = 'Înregistrare în curs — maximum două minute.';
          session.timer = setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, 120000);
        } catch (error) { status.textContent = error.name === 'NotAllowedError' ? 'Accesul la microfon nu a fost permis.' : 'Microfonul nu poate fi pornit.'; reset(); }
      });
    });
  };
  window.addEventListener('pagehide', () => {
    if (!active) return;
    active.failed = true; clearTimeout(active.timer); active.stream?.getTracks().forEach(track => track.stop());
    if (active.recorder?.state === 'recording') active.recorder.stop();
  });
})();
