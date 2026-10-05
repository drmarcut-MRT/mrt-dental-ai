'use strict';
const $ = (selector) => document.querySelector(selector);
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
function notice(message, error = false) { $('#notice').textContent = message; $('#notice').classList.toggle('error', error); }
async function api(url, options = {}) {
  const response = await fetch(url, options);
  const body = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(body?.error || 'Operațiunea nu a reușit.');
  return body;
}
const json = (method, data) => ({method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
async function busy(button, action) { button.disabled = true; try { await action(); } catch (error) { notice(error.message, true); } finally { button.disabled = false; } }
function action(label, handler, className = 'secondary') {
  const button = node('button', label, className); button.type = 'button';
  button.addEventListener('click', () => busy(button, handler)); return button;
}
function empty(container, label) { container.replaceChildren(node('p', label, 'muted')); }
async function loadContent() {
  const [briefs, proposals, library] = await Promise.all([api('/api/content/briefs'), api('/api/content/proposals'), api('/api/content/library')]);
  const list = $('#brief-list'); list.replaceChildren();
  for (const brief of [...briefs].reverse()) {
    const card = node('article', undefined, 'card'); card.append(node('h3', brief.topic), node('p', `${brief.platform} · ${brief.format}`, 'muted'), node('p', brief.instructions, 'text'));
    const proposal = proposals[brief.id]; const actions = node('div', undefined, 'actions');
    actions.append(action(proposal ? 'Regenerează text' : 'Generează text', async () => {
      if (proposal && !confirm('Înlocuiești propunerea curentă cu o generare nouă?')) return;
      await api(`/api/content/proposals/${brief.id}/generate`, {method: 'POST'}); await loadContent(); notice('Text generat. Verifică și editează înainte de aprobare.');
    }));
    if (proposal) {
      const label = node('label', 'Textul propunerii'); const editor = node('textarea'); editor.rows = 8; editor.value = proposal.content; label.append(editor);
      card.append(node('p', proposal.status === 'final' ? 'Aprobat' : 'Ciornă', 'muted'), label);
      const revisionLabel = node('label', 'Modificare cerută'); const instruction = node('input'); revisionLabel.append(instruction); card.append(revisionLabel);
      actions.append(action('Salvează text', async () => { await api(`/api/content/proposals/${brief.id}`, json('PUT', {content: editor.value})); await loadContent(); notice('Text salvat.'); }));
      actions.append(action('Revizuiește cu AI', async () => {
        if (!instruction.value.trim()) throw new Error('Scrie modificarea cerută.');
        await api(`/api/content/proposals/${brief.id}`, json('PUT', {content: editor.value}));
        await api(`/api/content/proposals/${brief.id}/revise`, json('POST', {instruction: instruction.value})); await loadContent(); notice('Text revizuit.');
      }));
      actions.append(action('Aprobă în bibliotecă', async () => {
        if (!editor.value.trim()) throw new Error('Textul nu poate fi gol.');
        await api(`/api/content/proposals/${brief.id}`, json('PUT', {content: editor.value}));
        await api(`/api/content/proposals/${brief.id}/finalize`, {method: 'POST'}); await loadContent(); notice('Text aprobat și salvat în bibliotecă.');
      }));
    }
    actions.append(action('Șterge brief', async () => {
      if (!confirm('Ștergi definitiv brief-ul, propunerea și textul aprobat asociat din bibliotecă?')) return;
      await api(`/api/content/briefs/${brief.id}`, {method: 'DELETE'}); await loadContent(); notice('Brief și textele asociate șterse.');
    }, 'danger'));
    card.append(actions); list.append(card);
  }
  if (!briefs.length) empty(list, 'Nu există încă briefuri.');
  const lib = $('#content-library'); lib.replaceChildren();
  for (const item of [...library].reverse()) {
    const card = node('article', undefined, 'card'); card.append(node('h3', item.title), node('p', item.content, 'text'));
    if (proposals[item.brief_id]?.status !== 'final') card.append(node('p', 'Ultima versiune aprobată. Propunerea curentă necesită aprobare.', 'muted'));
    lib.append(card);
  }
  if (!library.length) empty(lib, 'Nu există texte aprobate.');
  window.attachDictation(list);
}
async function loadMedia() {
  const jobs = await api('/api/media'); const jobsList = $('#media-jobs'); jobsList.replaceChildren();
  for (const job of [...jobs].reverse()) {
    if (!['pending', 'processing', 'failed', 'cancelled'].includes(job.status)) continue;
    const card = node('article', undefined, 'card');
    const statuses = {pending: 'În coadă', processing: 'Se generează', failed: 'Generare eșuată', cancelled: 'Anulat'};
    card.append(node('p', job.prompt, 'text'), node('p', statuses[job.status], 'muted'));
    if (job.last_error) card.append(node('p', job.last_error));
    if (['pending', 'processing'].includes(job.status)) {
      const controls = node('div', undefined, 'actions');
      controls.append(action('Verifică statusul', async () => { try { await api(`/api/media/${job.id}/refresh`, {method: 'POST'}); } finally { await loadMedia(); } }));
      controls.append(action('Anulează video', async () => { await api(`/api/media/${job.id}/cancel`, {method: 'POST'}); await loadMedia(); notice('Anulare confirmată de furnizor.'); })); card.append(controls);
    }
    card.append(deleteMediaButton(job)); jobsList.append(card);
  }
  const rows = await api('/api/library'); const list = $('#media-library'); list.replaceChildren();
  const filter = $('#media-filter').value;
  const visible = rows.filter(row => filter === 'all' || (filter === 'saved' ? row.saved : row.kind === filter));
  for (const row of [...visible].reverse()) {
    const card = node('article', undefined, 'card'); card.append(node('h3', row.kind === 'video' ? 'Video' : 'Imagine'), node('p', row.prompt, 'text'));
    if (row.filename) {
      const src = '/uploads/' + encodeURIComponent(row.filename);
      const preview = node(row.kind === 'video' ? 'video' : 'img'); preview.src = src;
      if (row.kind === 'video') { preview.controls = true; preview.preload = 'metadata'; preview.playsInline = true; }
      else { preview.alt = row.prompt || 'Imagine generată'; preview.loading = 'lazy'; }
      card.append(preview);
      const download = node('a', 'Descarcă fișierul'); download.href = src; download.download = row.filename; card.append(download);
    }
    const controls = node('div', undefined, 'actions');
    if (row.saved) card.append(node('p', 'Salvat în bibliotecă', 'muted'));
    else controls.append(action('Salvează în bibliotecă', async () => { await api(`/api/media/${row.id}/save`, {method: 'POST'}); await loadMedia(); notice('Media salvată în bibliotecă.'); }));
    controls.append(deleteMediaButton(row)); card.append(controls); list.append(card);
  }
  if (!visible.length) empty(list, 'Nu există media pentru filtrul ales.');
}
function deleteMediaButton(row) {
  return action('Șterge media', async () => {
    if (!confirm('Ștergi definitiv acest fișier? Un video în curs va fi anulat mai întâi.')) return;
    await api(`/api/media/${row.id}`, {method: 'DELETE'}); await loadMedia(); notice('Media ștearsă.');
  }, 'danger');
}
$('#media-filter').addEventListener('change', () => loadMedia().catch(error => notice(error.message, true)));
$('#refresh-library').addEventListener('click', event => busy(event.currentTarget, loadMedia));
$('#brief-form').addEventListener('submit', (event) => {
  event.preventDefault(); const form = event.currentTarget;
  busy(form.querySelector('button[type=submit]'), async () => { await api('/api/content/briefs', json('POST', Object.fromEntries(new FormData(form)))); form.reset(); await loadContent(); notice('Brief salvat.'); });
});
$('#media-form select[name=kind]').addEventListener('change', (event) => { $('#video-options').hidden = event.target.value !== 'video'; });
$('#media-form').addEventListener('submit', (event) => {
  event.preventDefault(); const form = event.currentTarget;
  busy(form.querySelector('button[type=submit]'), async () => {
    notice('Generare în curs…'); const result = await api('/api/media/generate', {method: 'POST', body: new FormData(form)});
    const card = node('article', undefined, 'card'); card.append(node('p', result.prompt), node('p', result.status === 'ready' ? 'Finalizat' : 'Video trimis în coadă.')); $('#media-jobs').prepend(card);
    await loadMedia(); notice(result.status === 'ready' ? 'Imagine generată.' : 'Cerere video trimisă.');
  });
});
Promise.all([loadContent(), loadMedia()]).catch(error => notice(error.message, true));
window.attachDictation(document);
