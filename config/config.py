"""Configurazione Serie A — usa betting-core."""
import os
from pathlib import Path
from dotenv import load_dotenv
from betting_core import PredictorConfig

load_dotenv()

cfg = PredictorConfig(
    name="Serie A",
    csv_prefix="serie_a",
    seasons=["1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"],
    download_url="https://www.football-data.co.uk/mmz4281/{season}/I1.csv",
    odds_api_url="https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds",
    odds_api_key=os.getenv("ODDS_API_KEY", ""),
    base_dir=Path(__file__).parent.parent,
    streamlit_port=8501,
    api_port=8001,
    api_key=os.getenv("API_KEY", ""),
)
