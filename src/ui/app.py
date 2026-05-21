"""Interfaccia Streamlit per il Serie A Predictor."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.prediction.predict import predict_match
from src.scraper.odds_live import get_upcoming_odds, get_mock_odds
from src.db.storage import init_db, save_prediction, set_result, get_all_predictions, get_roi_stats, get_pending_predictions, save_odds_cache, load_odds_cache
from src.db.update_results import auto_update_results
from config.config import ODDS_API_KEY, DATA_PROCESSED, DATA_EXPORTS, MODELS_DIR

init_db()

st.set_page_config(page_title="Serie A Predictor", page_icon="⚽", layout="wide")
st.title("⚽ Serie A Predictor")
st.caption("Predizioni basate sulle quote dei bookmaker")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Impostazioni")
    use_mock = st.toggle("Usa dati di esempio (no API key)", value=not bool(ODDS_API_KEY))
    use_kelly = st.toggle(
        "Kelly criterion",
        value=False,
        help="ON: suggerisce quanto scommettere in base all'edge stimato (Kelly). OFF: flat betting (importo fisso)",
    )
    bankroll = None
    if use_kelly:
        bankroll = st.number_input(
            "Bankroll (€)", min_value=10, value=100, step=10,
            help="Il tuo capitale totale da cui calcolare la frazione Kelly",
        )
    st.divider()
    st.subheader("Stato sistema")
    model_ok = (MODELS_DIR / "model.joblib").exists()
    data_ok  = (DATA_PROCESSED / "dataset.csv").exists()
    st.write("🟢 Modello" if model_ok else "🔴 Modello non trovato")
    st.write("🟢 Dataset" if data_ok else "🔴 Dataset non trovato")
    if data_ok:
        df_info = pd.read_csv(DATA_PROCESSED / "dataset.csv")
        st.write(f"📊 {len(df_info)} partite nel dataset")

# ── Tab principali ────────────────────────────────────────────────────────────
tab_pred, tab_manual, tab_update, tab_history = st.tabs(["🔮 Predizioni giornata", "✏️ Inserimento manuale", "🔄 Aggiorna dataset", "📊 Storico"])

# ── Tab 1: Predizioni automatiche ────────────────────────────────────────────
with tab_pred:
    st.subheader("Prossima giornata Serie A")

    if not model_ok:
        st.error("Modello non trovato. Esegui prima il training.")
        st.stop()

    cached_matches, cached_at = load_odds_cache()

    col_btn, col_warn = st.columns([1, 3])
    with col_btn:
        load_clicked = st.button("🔄 Carica quote", type="primary", help="Scarica le quote della prossima giornata di Serie A tramite The Odds API")
    with col_warn:
        if cached_at and not use_mock:
            from datetime import datetime, timezone
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at.replace(" ", "T") + "+00:00")).total_seconds() / 3600
            if age_h > 6:
                st.warning(f"⚠️ Quote vecchie ({int(age_h)}h fa) — consigliamo di ricaricare")
            else:
                st.caption(f"📦 Cache aggiornata {int(age_h * 60)}min fa")

    if load_clicked:
        with st.spinner("Recupero quote..."):
            try:
                if use_mock:
                    matches = get_mock_odds()
                else:
                    matches = get_upcoming_odds()
                    save_odds_cache(matches)
                st.session_state["matches"] = matches
            except Exception as e:
                st.error(f"Errore: {e}")

    matches = st.session_state.get("matches", [])
    if not matches:
        st.info("Clicca 'Carica quote' per vedere le predizioni.")
    else:
        results = []
        for m in matches:
            try:
                pred = predict_match(m["home_team"], m["away_team"], m["odds"])
                # Quota media bookmaker per l'esito predetto
                suffix = pred["prediction"]
                bk_odds = [v for k, v in m["odds"].items() if k.endswith(suffix) and v > 1]
                avg_odds = round(sum(bk_odds) / len(bk_odds), 2) if bk_odds else None

                save_prediction(
                    home_team=m["home_team"],
                    away_team=m["away_team"],
                    prediction=pred["prediction"],
                    prob_h=pred["probs"]["H"],
                    prob_d=pred["probs"]["D"],
                    prob_a=pred["probs"]["A"],
                    value_bet=pred.get("value_bet", False),
                    avg_odds=avg_odds,
                    match_date=m.get("commence_time", "")[:10],
                )
                # Kelly criterion: f = (p*b - (1-p)) / b  dove b = quota - 1
                kelly_stake = None
                if pred.get("value_bet") and avg_odds and avg_odds > 1:
                    p = pred["probs"][pred["prediction"]]
                    b = avg_odds - 1
                    f = (p * b - (1 - p)) / b
                    kelly_stake = round(max(f, 0) * bankroll, 2) if use_kelly else None

                results.append({
                    "Casa":        m["home_team"],
                    "Trasferta":   m["away_team"],
                    "Predizione":  pred["prediction_label"],
                    "P(Casa) %":   f"{pred['probs']['H']*100:.1f}",
                    "P(Pareggio) %": f"{pred['probs']['D']*100:.1f}",
                    "P(Trasferta) %": f"{pred['probs']['A']*100:.1f}",
                    "Confidenza %": f"{pred['confidence']*100:.1f}",
                    "Bookmaker":   len(m["odds"]) // 3,
                    "Value Bet":   "✅" if pred.get("value_bet") else "",
                    **( {"Scommetti (€)": f"{kelly_stake:.2f}" if kelly_stake else ""} if use_kelly else {} ),
                })
            except Exception as e:
                st.warning(f"{m['home_team']} vs {m['away_team']}: {e}")

        if results:
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True, hide_index=True)
            caption = "✅ Value Bet: prob trasferta > 45% e varianza bookmaker bassa (ROI storico +10% su 5 stagioni)"
            if use_kelly:
                caption += f" | 💰 Kelly criterion attivo (bankroll: {bankroll}€)"
            st.caption(caption)

            export_cols = ["Casa", "Trasferta", "Predizione", "P(Casa) %", "P(Pareggio) %", "P(Trasferta) %", "Confidenza %", "Value Bet"]
            if use_kelly and "Scommetti (€)" in df_results.columns:
                export_cols.append("Scommetti (€)")
            csv_bytes = df_results[export_cols].to_csv(index=False).encode("utf-8")

            # Salva su disco in data/exports/
            from datetime import datetime
            DATA_EXPORTS.mkdir(parents=True, exist_ok=True)
            export_filename = f"predizioni_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            export_path = DATA_EXPORTS / export_filename
            export_path.write_bytes(csv_bytes)

            st.download_button(
                "📥 Esporta predizioni CSV",
                data=csv_bytes,
                file_name=export_filename,
                mime="text/csv",
                help=f"Scarica il CSV (salvato anche in data/exports/{export_filename})",
            )
            st.caption(f"💾 Salvato anche in `data/exports/{export_filename}`")

# ── Tab 2: Inserimento manuale ────────────────────────────────────────────────
with tab_manual:
    st.subheader("Inserisci quote manualmente")
    col1, col2 = st.columns(2)
    with col1:
        home = st.text_input("Squadra casa", "Inter")
        away = st.text_input("Squadra trasferta", "Milan")
    with col2:
        st.write("**Quote Bet365**")
        b365h = st.number_input("1 (casa)", min_value=1.01, value=2.10, step=0.05)
        b365d = st.number_input("X (pareggio)", min_value=1.01, value=3.40, step=0.05)
        b365a = st.number_input("2 (trasferta)", min_value=1.01, value=3.20, step=0.05)

    with st.expander("Aggiungi altri bookmaker (opzionale)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            whh = st.number_input("WH 1", min_value=0.0, value=0.0, step=0.05)
            whd = st.number_input("WH X", min_value=0.0, value=0.0, step=0.05)
            wha = st.number_input("WH 2", min_value=0.0, value=0.0, step=0.05)
        with c2:
            psh = st.number_input("PS 1", min_value=0.0, value=0.0, step=0.05)
            psd = st.number_input("PS X", min_value=0.0, value=0.0, step=0.05)
            psa = st.number_input("PS 2", min_value=0.0, value=0.0, step=0.05)

    if st.button("🔮 Predici", type="primary", help="Calcola la predizione (1/X/2) e il filtro value bet per la partita inserita"):
        odds = {"B365H": b365h, "B365D": b365d, "B365A": b365a}
        if whh > 1: odds.update({"WHH": whh, "WHD": whd, "WHA": wha})
        if psh > 1: odds.update({"PSH": psh, "PSD": psd, "PSA": psa})
        try:
            pred = predict_match(home, away, odds)
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Predizione", pred["prediction_label"])
            col_b.metric(f"P({home})", f"{pred['probs']['H']*100:.1f}%")
            col_c.metric("P(Pareggio)", f"{pred['probs']['D']*100:.1f}%")
            col_d.metric(f"P({away})", f"{pred['probs']['A']*100:.1f}%")
        except Exception as e:
            st.error(f"Errore: {e}")

# ── Tab 3: Aggiorna dataset ───────────────────────────────────────────────────
with tab_update:
    st.subheader("Aggiorna dataset e ri-addestra il modello")
    st.info(
        "Dopo ogni giornata puoi scaricare i nuovi risultati e ri-addestrare il modello "
        "per includere le partite più recenti."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Scarica nuovi dati storici", help="Scarica i CSV aggiornati da football-data.co.uk (ultime 5 stagioni). Necessario prima di ri-addestrare il modello"):
            with st.spinner("Download CSV..."):
                try:
                    from src.scraper.download_historical import download_all
                    paths = download_all()
                    st.success(f"Scaricati {len(paths)} file")
                except Exception as e:
                    st.error(f"Errore download: {e}")

    with col2:
        if st.button("🏋️ Ri-addestra modello", help="Ri-addestra il modello XGBoost includendo le partite più recenti. Esegui prima 'Scarica nuovi dati storici'"):
            with st.spinner("Training in corso..."):
                try:
                    from src.training.train import run as train_run
                    # Forza ricalcolo del dataset
                    processed_path = DATA_PROCESSED / "dataset.csv"
                    if processed_path.exists():
                        processed_path.unlink()
                    train_run()
                    st.success("Modello aggiornato!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore training: {e}")

# ── Tab 4: Storico ────────────────────────────────────────────────────────────
with tab_history:
    st.subheader("Storico predizioni")

    if st.button("🔄 Aggiorna risultati", type="primary", help="Cerca nei CSV storici i risultati reali delle partite già giocate e li registra automaticamente nel database"):
        with st.spinner("Cerco risultati nei CSV..."):
            r = auto_update_results()
        if r["updated"] == 0 and r["still_missing"] == 0:
            st.info("Nessuna predizione in attesa di risultato.")
        else:
            if r["updated"]:
                st.success(f"Aggiornati {r['updated']} risultati.")
            if r["still_missing"]:
                st.warning(f"{r['still_missing']} partite non ancora nei CSV (probabilmente non ancora giocate o CSV non aggiornato).")
            with st.expander("Dettagli"):
                for d in r["details"]:
                    st.write(d)
        st.rerun()

    st.divider()

    rows = get_all_predictions()
    if not rows:
        st.info("Nessuna predizione salvata. Carica le quote dalla tab 'Predizioni giornata'.")
    else:
        df_hist = pd.DataFrame(rows)

        # Sezione ROI value bet
        stats = get_roi_stats()
        if stats["n"] > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Value bet con risultato", stats["n"])
            c2.metric("Win rate", f"{stats['win_rate']*100:.1f}%")
            roi_val = stats["roi"]
            c3.metric("ROI reale", f"{roi_val*100:.1f}%" if roi_val is not None else "—",
                      delta_color="normal")
            st.divider()

        # Tabella con possibilità di registrare risultato
        st.write("**Registra risultato reale** (per le partite già giocate)")
        pending = df_hist[df_hist["result"].isna()]
        if not pending.empty:
            sel = st.selectbox(
                "Seleziona partita",
                options=pending["id"].tolist(),
                format_func=lambda i: next(
                    f"{r['home_team']} vs {r['away_team']} ({r['match_date'] or r['created_at']})"
                    for r in rows if r["id"] == i
                ),
            )
            res = st.radio("Risultato reale", ["H", "D", "A"], horizontal=True)
            if st.button("💾 Salva risultato"):
                set_result(sel, res)
                st.success("Risultato salvato!")
                st.rerun()

        st.divider()
        # Tabella completa
        display_cols = ["match_date", "home_team", "away_team", "prediction",
                        "prob_h", "prob_d", "prob_a", "value_bet", "avg_odds", "result"]
        st.dataframe(
            df_hist[display_cols].rename(columns={
                "match_date": "Data", "home_team": "Casa", "away_team": "Trasferta",
                "prediction": "Pred", "prob_h": "P(H)", "prob_d": "P(D)", "prob_a": "P(A)",
                "value_bet": "VB", "avg_odds": "Quota", "result": "Risultato",
            }),
            use_container_width=True, hide_index=True,
        )
