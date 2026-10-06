# MRT Dental AI v5 — working copy

Copie de dezvoltare separată de aplicația live din Railway.

## Ce include
- Content Studio: briefuri persistente în fișiere JSON
- Propuneri AI: generare, editare, revizuire și aprobare
- Aprobare -> Bibliotecă de conținut persistentă
- Media: generare imagine/video și bibliotecă media
- Dictare/transcriere RO
- configurare exclusiv prin variabile de mediu pentru cheile API
- scrieri JSON atomice pentru reducerea riscului de fișiere parțial scrise

## Configurare
Copiază `.env.example` în mediul de rulare și setează cheile ca variabile de mediu. Nu comite cheile API în Git.

## Pornire
`pip install -r requirements.txt`
`python run.py`

## Testare
`pip install -r requirements-dev.txt`

`python -m pytest -q`

Pentru verificarea clientului de dictare cu microfon și răspunsuri simulate (necesită Node.js):

`node --test tests/test_dictation.cjs`

Testele includ validarea briefurilor, protecția la salvarea unei propuneri inexistente și fluxul aprobare -> bibliotecă.

## Notă
Această arhivă nu modifică și nu face deploy în Railway.

## v5 hardening
- `/health` raportează versiunea, ora UTC și dacă integrarea AI/media este configurată, fără a expune chei.
- Răspunsuri JSON coerente pentru 404/405/500.
- Test de integrare pentru fluxul complet brief → generare → editare → aprobare → bibliotecă, cu AI mock-uit (fără apel extern).

## Completări operaționale
- Interfață în română: briefuri, generare, editare, revizuire, aprobare și biblioteca textelor.
- Video: verificare manuală a statusului, descărcarea rezultatului și anulare confirmată de furnizor. Un eșec temporar la preluare poate fi reîncercat. Anularea eșuată nu schimbă statusul local și împiedică ștergerea unui video în curs.
- Biblioteca media: previzualizare, player video, descărcare, filtre și salvare explicită. Pentru compatibilitate, `/api/library` continuă să returneze toate rezultatele finalizate; filtrul „Salvate” folosește marcajul `saved`.
- Dictare pentru indicațiile brief-ului, descrierea media și textul propunerii. Microfonul pornește doar la apăsarea butonului. Necesită HTTPS sau localhost, permisiune de microfon și browser cu MediaRecorder. Înregistrarea este limitată la două minute/20 MB; cererile la 25 MB.
- Ștergerea unui brief elimină și propunerea și textul aprobat asociat. Interfața cere confirmare explicită. Fișierele media sunt independente și nu sunt șterse odată cu brief-ul.
- Editarea sau revizuirea unui text aprobat îl readuce la ciornă. Biblioteca păstrează ultima versiune aprobată până la o nouă aprobare și o semnalează în interfață.

## API suplimentar
- `GET /api/media` — toate cererile și rezultatele media.
- `POST /api/media/<id>/refresh` — verifică și finalizează un video.
- `POST /api/media/<id>/cancel` — anulează un video în curs.
- `POST /api/media/<id>/save` — marchează media finalizată ca salvată.
- `DELETE /api/media/<id>` — șterge media; anulează mai întâi un video în curs.
- `DELETE /api/content/briefs/<id>` — șterge brief-ul și textele asociate.

## Limite și verificare
Testele Python blochează conexiunile externe; furnizorii sunt simulați. Testele nu confirmă disponibilitatea modelelor sau a parametrilor la furnizori, facturarea, redarea unui MP4 real ori microfonul pe dispozitive reale. Codul `recovery` rămâne separat și nu este importat automat.

În staging, interfața și API-urile cer autentificare HTTP Basic prin HTTPS; configurează STAGING_AUTH_USERNAME și STAGING_AUTH_PASSWORD în Railway. Healthcheck-ul rămâne public pentru citire. Vezi STAGING.md pentru configurare și limite. Stocarea JSON nu asigură tranzacții între fișiere sau protecție între mai mulți workeri; lock-ul media protejează doar un proces. Pentru date persistente în hosting sunt necesare directoare pe un volum persistent. Variabilele de mediu trebuie setate în mediul de rulare; `python run.py` nu încarcă automat `.env`.
