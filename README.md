# Serie A Predictor

Predice l'esito (1/X/2) delle partite di **Serie A italiana** usando le quote dei bookmaker come feature per un modello ML (XGBoost).

Parte dell'ecosistema [Betting](https://github.com/Giangi70/betting-core) multi-sport.

## Quick Start

```bash
# 1. Clona il progetto
git clone https://github.com/Giangi70/seriea-predictor
cd seriea-predictor

# 2. Crea il virtualenv e installa le dipendenze
#    (betting-core viene scaricato automaticamente da GitHub)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configura la API key (opzionale — senza key usa i dati mock)
cp .env.example .env
# Edita .env e inserisci la tua ODDS_API_KEY
# Ottieni una key gratuita su https://the-odds-api.com (500 req/mese)

# 4. Avvia
./start.sh
```

L'app si apre su **http://localhost:8501**

Lo `start.sh` scarica automaticamente i dati storici e addestra il modello al primo avvio.

## API REST (per il betting-agent)

Oltre alla UI Streamlit, il predictor espone una **API REST FastAPI** interrogabile da programma.

```bash
# avvio API (porta 8001)
./start_api.sh
```

L'API parte su **http://localhost:8001** — documentazione interattiva su **http://localhost:8001/docs**.

### Endpoint

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/health` | Stato servizio: modello caricato, dataset presente, auth richiesta |
| GET | `/predictions` | Predizioni 1/X/2 della giornata (richiede quote live) |
| GET | `/signals` | Segnali strategia mista (safe + jolly) + flag stagione calda |
| GET | `/roi` | ROI stagionale corrente + `stagione_calda` |

### Autenticazione

Opzionale. Se imposti `API_KEY` nel file `.env`, ogni endpoint (tranne `/health`) richiede
l'header `X-API-Key: <chiave>`. Senza `API_KEY` l'auth è disattivata (comodo in locale).

```bash
curl http://localhost:8001/roi                              # auth disattivata
curl -H "X-API-Key: la_tua_chiave" http://localhost:8001/roi  # auth attiva
```

> `/predictions` e `/signals` richiedono le quote live: senza `ODDS_API_KEY` rispondono 503.
> La logica dell'API vive in `betting-core` (`betting_core/api.py`), condivisa da tutti i predictor.

## Dati

- **Storici**: [football-data.co.uk](https://www.football-data.co.uk) — 9 stagioni (2016/17→2024/25), ~3400 partite
- **Quote live**: [The Odds API](https://the-odds-api.com) — endpoint `soccer_italy_serie_a`
- **CV accuracy modello**: ~51%

## Funzionalità

| Tab | Descrizione |
|---|---|
| 🔮 Predizioni giornata | Quote live → predizioni 1/X/2 con probabilità |
| ✏️ Inserimento manuale | Inserisci quote a mano per una singola partita |
| 🔄 Aggiorna dataset | Scarica nuovi dati e ri-addestra il modello |
| 📊 Storico | Predizioni passate, risultati reali, ROI value bet |
| 🎯 Strategia Mista | Segnali 9-safe+1-jolly con monitor ROI stagionale |

## Ecosistema

Questo progetto fa parte di un ecosistema multi-sport:

| Progetto | Campionato | Porta |
|---|---|---|
| [seriea-predictor](https://github.com/Giangi70/seriea-predictor) | Serie A Italia | 8501 |
| [serieb-predictor](https://github.com/Giangi70/serieb-predictor) | Serie B Italia | 8502 |
| [laliga2-predictor](https://github.com/Giangi70/laliga2-predictor) | La Liga 2 Spagna | 8503 |
| [bundesliga2-predictor](https://github.com/Giangi70/bundesliga2-predictor) | Bundesliga 2 Germania | 8504 |
| [betting-core](https://github.com/Giangi70/betting-core) | Libreria condivisa | — |
