# Come nasce Serie A Predictor

Questo documento racconta il percorso dall'idea iniziale all'implementazione, per poter riprendere il lavoro in futuro sapendo esattamente da dove veniamo e dove stiamo andando.

---

## L'idea originale

L'idea nasce da una riflessione sui siti di scommesse: i bookmaker usano modelli avanzati e sofisticati per stimare le probabilità di ogni esito. Se sbagliassero sistematicamente, perderebbero denaro. Quindi le loro quote sono già una stima molto accurata della realtà.

La domanda iniziale era: *"Posso addestrare un modello che prende le quote come input e mi dice qual è la probabilità che esca 1, X o 2?"*

### Il ragionamento discusso

Dopo riflessione, abbiamo chiarito alcuni punti importanti:

1. **Le quote già contengono la probabilità** — una quota di 2.00 implica ~50% di probabilità. Il modello rischierebbe di imparare solo quello che le quote già dicono.

2. **Il vig (overround)** — la somma delle probabilità implicite di 1+X+2 è sempre >100% (es. 105%). Questo è il margine del bookmaker. Va rimosso per avere probabilità pulite.

3. **Dove c'è valore reale** — la cosa interessante non è la singola quota, ma la **convergenza e divergenza tra bookmaker diversi**. Quando tutti concordano, il segnale è forte. Quando divergono, c'è incertezza o informazione asimmetrica. Questo pattern potrebbe essere predittivo.

4. **Conclusione** — vale la pena costruirlo e testarlo sui dati storici. Solo i dati diranno se c'è un pattern reale.

---

## Le scelte tecniche

### Dati storici
Abbiamo scelto **football-data.co.uk** perché:
- Gratuito
- Dati dal 1993 ad oggi
- CSV pronti con quote di 5-10 bookmaker per partita
- Serie A inclusa (file `I1.csv`)

### Quote live
**The Odds API** perché:
- Aggrega 40+ bookmaker
- Ha endpoint per Serie A
- Piano gratuito con 500 richieste/mese

### Stack Python
- **XGBoost** — robusto su dataset tabellari di medie dimensioni
- **Streamlit** — UI nel browser senza scrivere frontend
- **joblib** — serializzazione modello

---

## Come è stato costruito (sessione del 08/05/2026)

### Fase 1 — Struttura progetto
Creata la struttura directory sotto `/home/egiabot/PROJECT/seriea-predictor/`:
```
config/, data/raw/, data/processed/, models/, src/scraper/, src/training/, src/prediction/, src/ui/, notebooks/
```

File creati: `requirements.txt`, `.env.example`, `config/config.py`

### Fase 2 — Dati storici
Creato `src/scraper/download_historical.py` che scarica i CSV da football-data.co.uk.

Scaricate 5 stagioni (2020/21 → 2024/25) → **1900 partite** in `data/raw/`.

### Fase 3 — Virtualenv
Creato in `/home/egiabot/venvs/seriea-predictor/` (separato dal progetto, come da preferenza).
Installate tutte le dipendenze da `requirements.txt`.

### Fase 4 — Preprocessing
Creato `src/training/preprocess.py`.

Feature engineering:
- Quote grezze di ogni bookmaker (B365, WH, PS, IW, VC)
- Probabilità implicite normalizzate (vig rimosso)
- Deviazione standard tra bookmaker
- Divergenza massima tra bookmaker
- Numero di bookmaker disponibili

Output: `data/processed/dataset.csv` con 1898 partite e 23 feature.

### Fase 5 — Training
Creato `src/training/train.py`.

Modello: **XGBoost** con cross-validation 5-fold stratificata.

Risultati:
- **CV Accuracy: 51.1% ± 1.9%**
- Baseline casuale: 33%
- Modello salvato in `models/model.joblib`

### Fase 6 — Prediction
Creato `src/prediction/predict.py` con:
- Caricamento modello con cache in memoria
- Funzione `predict(odds)` → probabilità H/D/A
- Funzione `predict_match(home, away, odds)` → risultato con etichette leggibili

### Fase 7 — Quote live
Creato `src/scraper/odds_live.py` con:
- `get_upcoming_odds()` — chiama The Odds API per le prossime partite
- `get_mock_odds()` — dati di esempio per testare senza API key

### Fase 8 — UI Streamlit
Creato `src/ui/app.py` con 3 tab:
1. **Predizioni giornata** — carica quote automaticamente e mostra predizioni
2. **Inserimento manuale** — inserisci quote a mano per una partita
3. **Aggiorna dataset** — scarica nuovi dati e ri-addestra con un click

---

## Sessione del 11/05/2026 — Value Betting

### Analisi value betting
Creato `notebooks/analisi_value_betting.py`:
- Calibrazione bookmaker per fascia di probabilità
- Effetto della varianza (std) tra bookmaker sull'affidabilità
- Backtest flat betting su griglia di soglie

**Scoperta principale**: tutti i segmenti con ROI positivo riguardano la trasferta (A). Il filtro operativo scelto: `prob_A > 0.45 AND std_A < 0.0417` → ROI +10.2% su 393 partite storiche.

### Analisi tendenze stagionali
Creato `src/analysis/team_tendencies.py` e `notebooks/analisi_tendenze_stagionali.py`:
- Prima metà stagione → classifica squadre (high_win/high_draw/high_loss)
- Seconda metà → verifica persistenza e backtest combinato

**Risultato**: il segnale stagionale non aggiunge edge rispetto al filtro base (le quote già incorporano la forma della squadra). Si usa solo il filtro base.

### Modifiche al codice
- `preprocess.py` — preserva `date`, `home_team`, `away_team` nel dataset
- `train.py` — esclude le nuove colonne dalle feature
- `predict.py` — `predict_match()` restituisce `value_bet: bool`
- `app.py` — colonna "Value Bet ✅" nella tabella predizioni

Documento di dettaglio: `AnalisiValueBetting.md`

---

## Sessione del 14/05/2026 — Quote live + Persistenza SQLite

### Quote live attivate
- Inserita API key reale in `.env` (The Odds API, piano free 500 req/mese)
- Trovato e corretto bug critico in `predict.py`: le quote live venivano passate raw al modello senza calcolare le feature derivate (prob, std, divergence). Aggiunta `build_features_from_odds()` che fa lo stesso preprocessing del training.
- Testato con 10 partite reali della giornata 17/05/2026 → predizioni sensate e differenziate
- 1 value bet identificata: Pisa vs Napoli → A

### Sessione del 14/05/2026 — Stabilità ROI + Kelly criterion

#### Verifica stabilità ROI per stagione
Aggiunta sezione 7 in `notebooks/analisi_value_betting.py`.

Risultato: ROI positivo in **tutte e 5 le stagioni** (da +1.9% a +16.6%) → il segnale è robusto, non è un artefatto di 1-2 stagioni anomale.

#### Kelly criterion
Aggiunto toggle **"Kelly criterion"** nella sidebar dell'app:
- OFF (default): flat betting, nessuna colonna aggiuntiva
- ON: appare campo **Bankroll (€)** e colonna **"Scommetti (€)"** nella tabella, calcolata solo per le value bet
- Formula: `f = (p × b - (1-p)) / b` dove `p` = probabilità stimata, `b` = quota - 1

---

### Persistenza SQLite
Creato `src/db/storage.py` con:
- `init_db()` — crea la tabella `predictions` al primo avvio
- `save_prediction()` — salva predizione con quote, probabilità, value_bet flag
- `set_result()` — registra il risultato reale dopo la partita
- `get_all_predictions()` — lista completa
- `get_roi_stats()` — calcola win rate e ROI reale sulle value bet con risultato registrato

Aggiornato `app.py`:
- Tab 1: predizioni salvate automaticamente nel DB ad ogni caricamento quote
- Tab 4 "📊 Storico": tabella completa + widget per registrare risultato reale + metriche ROI live

---

## Stato attuale (14/05/2026)

| Componente | Stato |
|---|---|
| Download dati storici | ✅ Funzionante |
| Preprocessing | ✅ Funzionante (include date/squadre) |
| Training modello | ✅ Funzionante (51.1% CV accuracy) |
| Inferenza + Value Bet filter | ✅ Funzionante |
| Analisi value betting | ✅ Completata (vedi AnalisiValueBetting.md) |
| Quote live (API) | ✅ Funzionante con API key reale |
| UI Streamlit | ✅ Funzionante con colonna Value Bet |
| Persistenza SQLite | ✅ Funzionante (predizioni + risultati + ROI reale) |

---

## Sessione del 22/05/2026 — Strategia Mista + Analisi Ciclicità

### Obiettivo
Studiare una politica di scommesse basata su budget fisso (1€/partita):
- **N_safe** partite sull'esito più probabile
- **N_jolly** partite sulla quota più alta (evento raro)

### Dati estesi a 9 stagioni
Scaricati i CSV delle stagioni 1617, 1718, 1819, 1920 da football-data.co.uk.
Totale: 3420 partite su 9 stagioni (2016/17 → 2024/25).
I CSV extra sono caricati direttamente dal notebook senza toccare il dataset processato del progetto.

### Analisi backtest (`notebooks/analisi_strategia_mista.py`)

**Risultato principale**: la strategia 10-safe + 1-jolly ha ROI positivo aggregato (+10%), ma con forte variabilità stagionale:

| Stagione | ROI (10+1, jolly>5€) |
|---|---|
| 1617 | +2.7% |
| 1718 | +2.3% |
| 1819 | +23.3% |
| 1920 | +19.9% |
| 2021 | +28.6% (COVID) |
| 2122 | +11.3% |
| 2223 | +0.9% |
| 2324 | +1.0% |
| 2425 | +1.2% |

**Ipotesi ciclicità**: il segnale è forte nel periodo 2019–2022 (probabile cambio modelli bookmaker) e si azzera nelle ultime 3 stagioni. Il mercato si riallinea periodicamente.

**Filtro gap probabilità**: escludere le partite con gap < 15% tra prob_max e prob_seconda migliora l'accuratezza ma non recupera l'edge nelle ultime stagioni.

**Strategia ottimale robusta** (ultime 3 stagioni): `n_safe=9, n_jolly=1, min_gap=0.15, min_q_jolly=5.0` → ROI +4.5%, 240 scommesse.

### Implementazione nel progetto

**`src/db/storage.py`**: aggiunta tabella `strategia_mista` con funzioni:
- `save_strategia_mista()` — salva le scommesse della giornata
- `get_strategia_mista()` — lista completa
- `set_result_strategia()` — registra risultato reale
- `get_roi_strategia()` — calcola ROI, filtrabile per stagione

**`src/ui/app.py`**: nuovo tab **🎯 Strategia Mista** con:
- Segnali giornata: 9 safe + 1 jolly calcolati dalle quote live
- Monitor ROI stagionale progressivo
- Alert 🔥 "stagione calda" se ROI ≥ 8% con ≥ 20 scommesse
- Storico scommesse + registrazione risultati reali

---

## Stato attuale (22/05/2026)

| Componente | Stato |
|---|---|
| Download dati storici | ✅ Funzionante |
| Preprocessing | ✅ Funzionante (include date/squadre) |
| Training modello | ✅ Funzionante (51.1% CV accuracy) |
| Inferenza + Value Bet filter | ✅ Funzionante |
| Analisi value betting | ✅ Completata (vedi AnalisiValueBetting.md) |
| Quote live (API) | ✅ Funzionante con API key reale |
| UI Streamlit | ✅ 5 tab (+ Strategia Mista) |
| Persistenza SQLite | ✅ Funzionante (predizioni + risultati + strategia mista) |
| Strategia Mista | ✅ Backtest 9 stagioni + monitor ROI + alert stagione calda |

---

## Prossimi passi possibili

1. **Monitorare la stagione 2025/26** — il monitor ROI nel tab Strategia Mista dirà se siamo in una nuova stagione "calda"
2. **Riaddestrare con 9 stagioni** — valutare se aggiungere le stagioni 1617-1920 al training migliora l'accuratezza del modello ML
3. **App Android** — seconda idea discussa, da sviluppare separatamente

---

## Come riprendere il lavoro

```bash
# Attiva il virtualenv
source /home/egiabot/venvs/seriea-predictor/bin/activate

# Vai nella directory del progetto
cd /home/egiabot/PROJECT/seriea-predictor

# Avvia l'app
PYTHONPATH=. streamlit run src/ui/app.py
```

Per ri-addestrare il modello con dati aggiornati:
```bash
PYTHONPATH=. python src/scraper/download_historical.py
PYTHONPATH=. python src/training/train.py
```
