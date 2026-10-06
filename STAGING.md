# GitHub și Railway staging

Ținta este exclusiv mediul `staging` din proiectul Railway `MRT Dental AI Staging`. Verificarea prin operații de citire a identificat acest mediu, fără servicii. Nu a fost creat sau modificat niciun serviciu Railway.

## Commit

- Branch de publicare: `main`, în repository-ul `DrMarcut-MRT/mrt-dental-ai`, conectat ca `origin`. Istoricul și arhiva existente pe GitHub sunt păstrate; nu se folosește push forțat.
- Codul, testele și configurația staging sunt pregătite în indexul Git original. Excepția de încredere pentru folder și backendul HTTPS OpenSSL se aplică doar comenzilor curente. Nu au fost schimbate permisiunile Windows sau configurația Git globală.
- `.env`, variantele sale, cheile/certificatele private, bazele de date, fișierele generate, cache-urile și `recovery` sunt excluse. `.env.example` conține doar valori demonstrative și câmpuri goale pentru cheile AI.
- `python tools/check_sensitive.py` verifică exact conținutul din index, fără a afișa valori de chei. Scanarea prin tipare nu garantează detectarea oricărui secret sau a datelor personale arbitrare.
- Mesaj propus: `Complete MRT Dental AI v5 workflows and prepare Railway staging`.
- CI rulează testele și scanarea, fără publicare sau deploy.

## Serviciul staging după alegerea repository-ului

1. Selectează explicit proiectul `MRT Dental AI Staging` și mediul `staging` în orice operație Railway.
2. Numai după autorizarea explicită a deploy-ului, creează un serviciu dedicat în mediul Railway `staging` și conectează branch-ul `main` din `DrMarcut-MRT/mrt-dental-ai`. Conectarea sursei poate declanșa imediat un build/deploy. Acest repository nu trebuie conectat la servicii de producție.
3. Configurează o singură replică și un volum staging nou, independent, montat la `/data`. Nu reutiliza volumul sau variabilele producției.
4. Setează `DATA_DIR=/data/data`, `MEDIA_DIR=/data/media` și un `SECRET_KEY` nou, aleator, de minimum 32 de caractere, în variabilele Railway. Nu introduce secretul în Git sau în raport.
5. Pentru prima verificare fără costuri AI, lasă `OPENAI_API_KEY` și `FAL_KEY` goale. Funcțiile AI vor returna o eroare de configurare până la configurarea unor chei dedicate staging.
6. Railway furnizează `PORT` și `RAILWAY_ENVIRONMENT_NAME`. `railway.json` pornește `python deploy/start_staging.py`. Launcher-ul refuză alte medii și configurațiile lipsă; Gunicorn folosește un worker și un thread.
7. Verifică build-ul, `/health`, UI și persistența după restart. Integrarea AI reală și efectul anulării asupra facturării se verifică separat.

În staging, aplicația cere autentificare HTTP Basic pentru interfață, fișiere și API. Configurează `STAGING_AUTH_USERNAME` și un `STAGING_AUTH_PASSWORD` aleator de minimum 32 de caractere numai în variabilele Railway. Parola nu se salvează în Git sau în rapoarte; administratorul o poate vedea în panoul de variabile Railway. Deschide numai adresa HTTPS și introdu datele în dialogul browserului. `/health` rămâne accesibil doar pentru citire fără autentificare, pentru verificarea Railway. Pornirea staging este refuzată dacă lipsesc datele de autentificare. Cererile de modificare din alte origini sunt refuzate; răspunsurile nu sunt memorate în cache.

Protecția este pentru un cont staging comun, fără roluri, administrare de utilizatori sau audit individual. Folosește inițial doar date demonstrative. Cheile AI rămân goale până la autorizarea integrărilor reale. JSON nu oferă tranzacții între fișiere și nu suportă în siguranță replici/workeri multipli. Evită suprapunerea a două instanțe care scriu pe același volum în timpul redeploy-ului.

## Verificare

Testele locale păstrează cele 8 teste originale și blochează apelurile externe. Launcher-ul staging este verificat prin teste unitare. Build-ul Railpack și Gunicorn nu au fost executate aici pe Windows; verificarea Gunicorn pe Linux este inclusă în CI. Push-ul pe GitHub poate porni CI, dar workflow-ul nu face deploy. Publicarea codului și deployment-ul Railway sunt operații separate; nu a fost autorizat deploy-ul.

Documentație oficială:
- [Config as code](https://docs.railway.com/config-as-code/reference)
- [Environments](https://docs.railway.com/environments)
- [Variables reference](https://docs.railway.com/variables/reference)
- [Healthchecks](https://docs.railway.com/deployments/healthchecks)
