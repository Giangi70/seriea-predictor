# Deploy — UI online su Streamlit Community Cloud

Guida operativa per pubblicare la **UI del predictor** su un URL pubblico,
accessibile da qualsiasi browser (anche smartphone). Costo: **0 €/mese**.

Modello scelto: **Streamlit Community Cloud + repo GitHub + URL `*.streamlit.app`**.
Stesso spirito del deploy del Grifo su Cloudflare: *repo GitHub → la piattaforma builda →
URL pubblico → ogni push aggiorna*. La differenza è che Streamlit Cloud **esegue** l'app
Python (il Grifo era statico e bastava Cloudflare Pages).

---

## Perché modello e dati sono versionati

In locale `start.sh` scarica i CSV e addestra il modello al primo avvio. Su Streamlit Cloud
l'app parte da un **clone pulito del repo** e il filesystem è effimero: non si può dipendere
dal training al boot (lento e fragile). Quindi, per il deploy, nel repo **sono versionati**:

- `models/model.joblib` — il modello già addestrato (~1,4 MB)
- `data/processed/dataset.csv` — il dataset pronto (~0,4 MB)
- `data/raw/*.csv` — i CSV storici (servono alla tab "Aggiorna risultati")

Così l'app è autonoma: apri l'URL e funziona subito, senza attese.
(Questo è lo stesso principio del Grifo, dove `data/` è versionato ed è online al push.)

---

## Setup Streamlit Cloud (una tantum)

1. L'app è già su GitHub: `https://github.com/Giangi70/seriea-predictor`
2. Vai su **https://share.streamlit.io** e accedi con GitHub.
3. **Create app** → **Deploy a public app from GitHub**.
4. Compila:

   | Campo | Valore |
   |-------|--------|
   | Repository | `Giangi70/seriea-predictor` |
   | Branch | `main` |
   | Main file path | `src/ui/app.py` |

5. (Opzionale) **Advanced settings** → **Secrets**: se vuoi le quote live, incolla
   ```
   ODDS_API_KEY = "la_tua_chiave"
   ```
   Senza, l'app usa i dati mock (toggle "Usa dati di esempio" già attivo di default).

6. **Deploy**. In 1-2 minuti l'app è online su un URL tipo
   `https://seriea-predictor.streamlit.app`.

---

## Flusso a regime

Dopo il setup, ogni push aggiorna l'app automaticamente:

```
modifichi → git push → Streamlit Cloud ribuilda → online in ~1-2 min
```

Se riaddestri il modello in locale, ricommitta `models/model.joblib` e
`data/processed/dataset.csv` prima del push.

---

## Limiti noti (importanti)

| Limite | Dettaglio | Impatto |
|--------|-----------|---------|
| **SQLite non persiste** | Il DB (`*.db`) è escluso dal repo e il filesystem cloud è effimero | Puoi *consultare* predizioni e segnali; lo **storico ROI** e il salvataggio risultati hanno senso solo in locale (o con un DB esterno, passo futuro) |
| **App "dorme"** | Dopo inattività l'app va in sleep | Il **primo accesso** dopo una pausa impiega ~30 sec a risvegliarsi, poi è veloce |
| **Quote live** | Richiedono `ODDS_API_KEY` nei Secrets | Senza, si usa il mock (va bene per guardare il funzionamento) |

Nessuno di questi impedisce l'obiettivo "mi collego e guardo le predizioni".

---

## Verifica pre-deploy (locale)

Simula l'ambiente cloud eseguendo dalla root del repo:

```bash
cd /home/egiabot/PROJECT/seriea-predictor
source /home/egiabot/venvs/seriea-predictor/bin/activate
streamlit run src/ui/app.py
# → http://localhost:8501  (deve partire senza "modello non trovato")
```

Se parte in locale da un clone con modello+dataset versionati, funzionerà identico online.
