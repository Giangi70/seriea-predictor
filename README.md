# Serie A Predictor

Predice l'esito (1/X/2) delle partite di Serie A usando le quote dei bookmaker come feature di input per un modello ML.

## Idea di base

I bookmaker usano modelli avanzati per stimare le probabilità di ogni esito. Questo progetto parte dall'assunzione che le loro quote siano già la migliore stima disponibile, e cerca di trovare pattern aggiuntivi nella **distribuzione e convergenza delle quote tra bookmaker diversi** che possano essere predittivi.

## Stack

| Componente | Tecnologia |
|---|---|
| Linguaggio | Python 3.11+ |
| ML | XGBoost + scikit-learn |
| UI | Streamlit |
| Database locale | SQLite |
| Quote live | The Odds API |
| Dati storici | football-data.co.uk |

## Struttura progetto

```
seriea-predictor/
├── config/
│   └── config.py           # Configurazione centralizzata (path, bookmaker, API)
├── data/
│   ├── raw/                # CSV storici da football-data.co.uk
│   └── processed/          # Dataset pulito pronto per il training
├── models/
│   └── model.joblib        # Modello addestrato (XGBoost + LabelEncoder + feature list)
├── notebooks/
│   ├── analisi_value_betting.py        # Backtest filtro value bet
│   ├── analisi_tendenze_stagionali.py  # Analisi tendenze per squadra
│   └── analisi_strategia_mista.py     # Backtest strategia 9-safe+1-jolly su 9 stagioni
├── src/
│   ├── scraper/
│   │   ├── download_historical.py  # Scarica CSV storici (5 stagioni)
│   │   └── odds_live.py            # Quote in tempo reale via The Odds API
│   ├── training/
│   │   ├── preprocess.py           # Feature engineering dai CSV
│   │   └── train.py                # Training XGBoost + cross-validation
│   ├── prediction/
│   │   └── predict.py              # Inferenza su nuove partite
│   ├── analysis/
│   │   └── team_tendencies.py      # Tendenze stagionali per squadra
│   ├── db/
│   │   ├── storage.py              # SQLite: predizioni, risultati, strategia mista
│   │   └── update_results.py       # Match automatico predizioni → risultati CSV
│   └── ui/
│       └── app.py                  # App Streamlit (5 tab)
├── .env.example            # Template variabili d'ambiente
├── requirements.txt        # Dipendenze Python
└── README.md
```

## Avvio rapido

```bash
./start.sh
```

Lo script:
1. Attiva il virtualenv
2. Scarica i dati storici se non presenti
3. Addestra il modello se non presente
4. Avvia l'app su `http://localhost:8501`

---

## Setup manuale

### 1. Virtualenv

Il virtualenv si trova in `/home/egiabot/venvs/seriea-predictor/`.

Per attivarlo:
```bash
source /home/egiabot/venvs/seriea-predictor/bin/activate
```

Per ricrearlo da zero:
```bash
python3 -m venv /home/egiabot/venvs/seriea-predictor
/home/egiabot/venvs/seriea-predictor/bin/pip install -r requirements.txt
```

### 2. Variabili d'ambiente

```bash
cp .env.example .env
# Edita .env e inserisci la tua ODDS_API_KEY
```

Ottieni una API key gratuita su [the-odds-api.com](https://the-odds-api.com/) (500 richieste/mese gratuite).

### 3. Scarica dati storici

```bash
PYTHONPATH=. python src/scraper/download_historical.py
```

Scarica 5 stagioni di Serie A (2020/21 → 2024/25) da football-data.co.uk in `data/raw/`.

### 4. Addestra il modello

```bash
PYTHONPATH=. python src/training/train.py
```

Esegue preprocessing + training XGBoost con cross-validation 5-fold. Salva il modello in `models/model.joblib`.

### 5. Avvia l'interfaccia

```bash
cd /home/egiabot/PROJECT/seriea-predictor
PYTHONPATH=. streamlit run src/ui/app.py
```

Apre l'app nel browser su `http://localhost:8501`.

## Utilizzo dell'app

L'app ha 5 sezioni:

### 🔮 Predizioni giornata
Carica automaticamente le quote della prossima giornata via The Odds API e mostra le predizioni per ogni partita con le probabilità di 1/X/2.

Senza API key, usa il toggle **"Usa dati di esempio"** per testare con partite mock.

### ✏️ Inserimento manuale
Inserisci le quote a mano per una singola partita. Supporta Bet365, William Hill, Pinnacle. Più bookmaker inserisci, più accurata è la predizione.

### 🔄 Aggiorna dataset
Dopo ogni giornata:
1. Clicca **"Scarica nuovi dati storici"** per aggiornare i CSV
2. Clicca **"Ri-addestra modello"** per includere le nuove partite

### 📊 Storico
Tabella completa delle predizioni salvate con possibilità di registrare il risultato reale e calcolare il ROI live sulle value bet.

### 🎯 Strategia Mista
Implementa la strategia **9-safe + 1-jolly** derivata dall'analisi backtest su 9 stagioni:
- **9 scommesse safe**: le 9 partite con gap di probabilità più alto (esito più probabile)
- **1 scommessa jolly**: la partita con la quota più alta (≥ 5.0)
- **Filtro gap**: esclude le partite incerte (gap prob < 15%)
- **Monitor ROI stagionale**: accumula i risultati reali e calcola il ROI progressivo
- **Alert stagione calda** 🔥: avvisa se il ROI stagionale supera l'8% (segnale che il mercato potrebbe aver perso efficienza)

## Feature del modello

Per ogni partita vengono calcolate:

| Feature | Descrizione |
|---|---|
| `B365H/D/A`, `WHH/D/A`, ... | Quote grezze di ogni bookmaker |
| `prob_H/D/A` | Probabilità implicite medie (normalizzate, vig rimosso) |
| `std_H/D/A` | Deviazione standard delle quote tra bookmaker |
| `divergence` | Divergenza massima tra bookmaker (segnale di incertezza) |
| `n_bookmakers` | Numero di bookmaker disponibili |

## Performance

Testato su 5 stagioni di Serie A (1898 partite):

- **Cross-validation accuracy: ~51%** (5-fold stratificato)
- Baseline casuale: 33% (3 classi)
- Baseline bookmaker: ~50-55%

Il modello è in linea con la letteratura accademica su questo tipo di predizioni.

## Dati storici

Fonte: [football-data.co.uk](https://www.football-data.co.uk/italym.php)

CSV gratuiti con quote di: Bet365, William Hill, Pinnacle, Interwetten, VC Bet e altri dal 1993 ad oggi.

Formato colonne principali:
- `FTR` — risultato finale (H/D/A)
- `B365H/D/A` — quote Bet365
- `WHH/D/A` — quote William Hill
- `PSH/D/A` — quote Pinnacle
