import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="TIA X World Cup 26",
    page_icon=":trophy:",
    layout="wide",
)

LIVE_TABLE_URL = "https://www.thesportsdb.com/api/v1/json/123/lookuptable.php?l=4429&s=2026"
LIVE_SEASON_GAMES_URL = "https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id=4429&s=2026"
DATA_DIR = Path(__file__).resolve().parent
DENMARK_TZ = ZoneInfo("Europe/Copenhagen")

TEAM_ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Cote d'Ivoire": "Ivory Coast",
    "Czech Republic": "Czechia",
    "CÃ´te d'Ivoire": "Ivory Coast",
    "CuraÃ§ao": "Curacao",
    "Curaçao": "Curacao",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "TÃ¼rkiye": "Turkiye",
    "Türkiye": "Turkiye",
    "Turkey": "Turkiye",
    "USA": "United States",
    "United States of America": "United States",
}

TEAM_FLAGS = {
    "Algeria": "dz",
    "Argentina": "ar",
    "Australia": "au",
    "Austria": "at",
    "Belgium": "be",
    "Bosnia and Herzegovina": "ba",
    "Brazil": "br",
    "Bolivia": "bo",
    "Canada": "ca",
    "Cape Verde": "cv",
    "Colombia": "co",
    "Croatia": "hr",
    "Curacao": "cw",
    "Czechia": "cz",
    "DR Congo": "cd",
    "Denmark": "dk",
    "Ecuador": "ec",
    "Egypt": "eg",
    "England": "gb-eng",
    "France": "fr",
    "Ghana": "gh",
    "Germany": "de",
    "Haiti": "ht",
    "Iran": "ir",
    "Iraq": "iq",
    "Italy": "it",
    "Ivory Coast": "ci",
    "Japan": "jp",
    "Jamaica": "jm",
    "Jordan": "jo",
    "Mexico": "mx",
    "Morocco": "ma",
    "Netherlands": "nl",
    "New Caledonia": "nc",
    "New Zealand": "nz",
    "North Macedonia": "mk",
    "Northern Ireland": "gb-nir",
    "Norway": "no",
    "Panama": "pa",
    "Paraguay": "py",
    "Poland": "pl",
    "Portugal": "pt",
    "Qatar": "qa",
    "Republic of Ireland": "ie",
    "Romania": "ro",
    "Saudi Arabia": "sa",
    "Scotland": "gb-sct",
    "Senegal": "sn",
    "South Africa": "za",
    "South Korea": "kr",
    "Spain": "es",
    "Suriname": "sr",
    "Sweden": "se",
    "Switzerland": "ch",
    "Slovakia": "sk",
    "Tunisia": "tn",
    "Turkiye": "tr",
    "United States": "us",
    "Uruguay": "uy",
    "Ukraine": "ua",
    "Uzbekistan": "uz",
    "Wales": "gb-wls",
}

OFFICIAL_GROUPS = {
    "Group A": [
        "Mexico",
        "South Korea",
        "South Africa",
        "Czechia",
    ],
    "Group B": [
        "Canada",
        "Switzerland",
        "Qatar",
        "Bosnia and Herzegovina",
    ],
    "Group C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "Group D": [
        "United States",
        "Paraguay",
        "Australia",
        "Turkiye",
    ],
    "Group E": ["Germany", "Ecuador", "Ivory Coast", "Curacao"],
    "Group F": [
        "Netherlands",
        "Japan",
        "Tunisia",
        "Sweden",
    ],
    "Group G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "Group H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "Group I": [
        "France",
        "Senegal",
        "Norway",
        "Iraq",
    ],
    "Group J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "Group K": [
        "Portugal",
        "Colombia",
        "Uzbekistan",
        "DR Congo",
    ],
    "Group L": ["England", "Croatia", "Panama", "Ghana"],
}

PLAYOFF_MATCHES = [
    {"round": "Round of 32", "match": 73, "date": "2026-06-28", "city": "Los Angeles Stadium", "team_1": "2A", "team_2": "2B"},
    {"round": "Round of 32", "match": 74, "date": "2026-06-29", "city": "Boston Stadium", "team_1": "1E", "team_2": "3P1E"},
    {"round": "Round of 32", "match": 75, "date": "2026-06-29", "city": "Estadio Monterrey", "team_1": "1F", "team_2": "2C"},
    {"round": "Round of 32", "match": 76, "date": "2026-06-29", "city": "Houston Stadium", "team_1": "1C", "team_2": "2F"},
    {"round": "Round of 32", "match": 77, "date": "2026-06-30", "city": "New York New Jersey Stadium", "team_1": "1I", "team_2": "3P1I"},
    {"round": "Round of 32", "match": 78, "date": "2026-06-30", "city": "Dallas Stadium", "team_1": "2E", "team_2": "2I"},
    {"round": "Round of 32", "match": 79, "date": "2026-06-30", "city": "Mexico City Stadium", "team_1": "1A", "team_2": "3P1A"},
    {"round": "Round of 32", "match": 80, "date": "2026-07-01", "city": "Atlanta Stadium", "team_1": "1L", "team_2": "3P1L"},
    {"round": "Round of 32", "match": 81, "date": "2026-07-01", "city": "San Francisco Bay Area Stadium", "team_1": "1D", "team_2": "3P1D"},
    {"round": "Round of 32", "match": 82, "date": "2026-07-01", "city": "Seattle Stadium", "team_1": "1G", "team_2": "3P1G"},
    {"round": "Round of 32", "match": 83, "date": "2026-07-02", "city": "Toronto Stadium", "team_1": "2K", "team_2": "2L"},
    {"round": "Round of 32", "match": 84, "date": "2026-07-02", "city": "Los Angeles Stadium", "team_1": "1H", "team_2": "2J"},
    {"round": "Round of 32", "match": 85, "date": "2026-07-02", "city": "BC Place Vancouver", "team_1": "1B", "team_2": "3P1B"},
    {"round": "Round of 32", "match": 86, "date": "2026-07-03", "city": "Miami Stadium", "team_1": "1J", "team_2": "2H"},
    {"round": "Round of 32", "match": 87, "date": "2026-07-03", "city": "Kansas City Stadium", "team_1": "1K", "team_2": "3P1K"},
    {"round": "Round of 32", "match": 88, "date": "2026-07-03", "city": "Dallas Stadium", "team_1": "2D", "team_2": "2G"},
    {"round": "Round of 16", "match": 89, "date": "2026-07-04", "city": "Philadelphia Stadium", "team_1": "W74", "team_2": "W77"},
    {"round": "Round of 16", "match": 90, "date": "2026-07-04", "city": "Houston Stadium", "team_1": "W73", "team_2": "W75"},
    {"round": "Round of 16", "match": 91, "date": "2026-07-05", "city": "New York New Jersey Stadium", "team_1": "W76", "team_2": "W78"},
    {"round": "Round of 16", "match": 92, "date": "2026-07-05", "city": "Mexico City Stadium", "team_1": "W79", "team_2": "W80"},
    {"round": "Round of 16", "match": 93, "date": "2026-07-06", "city": "Dallas Stadium", "team_1": "W83", "team_2": "W84"},
    {"round": "Round of 16", "match": 94, "date": "2026-07-06", "city": "Seattle Stadium", "team_1": "W81", "team_2": "W82"},
    {"round": "Round of 16", "match": 95, "date": "2026-07-07", "city": "Atlanta Stadium", "team_1": "W86", "team_2": "W88"},
    {"round": "Round of 16", "match": 96, "date": "2026-07-07", "city": "BC Place Vancouver", "team_1": "W85", "team_2": "W87"},
    {"round": "Quarter-finals", "match": 97, "date": "2026-07-09", "city": "Boston Stadium", "team_1": "W89", "team_2": "W90"},
    {"round": "Quarter-finals", "match": 98, "date": "2026-07-10", "city": "Los Angeles Stadium", "team_1": "W93", "team_2": "W94"},
    {"round": "Quarter-finals", "match": 99, "date": "2026-07-11", "city": "Miami Stadium", "team_1": "W91", "team_2": "W92"},
    {"round": "Quarter-finals", "match": 100, "date": "2026-07-11", "city": "Kansas City Stadium", "team_1": "W95", "team_2": "W96"},
    {"round": "Semi-finals", "match": 101, "date": "2026-07-14", "city": "Dallas Stadium", "team_1": "W97", "team_2": "W98"},
    {"round": "Semi-finals", "match": 102, "date": "2026-07-15", "city": "Atlanta Stadium", "team_1": "W99", "team_2": "W100"},
    {"round": "Third Place", "match": 103, "date": "2026-07-18", "city": "Miami Stadium", "team_1": "L101", "team_2": "L102"},
    {"round": "Final", "match": 104, "date": "2026-07-19", "city": "New York New Jersey Stadium", "team_1": "W101", "team_2": "W102"},
]

THIRD_PLACE_SLOT_POOLS = {
    "1A": "CEFHI",
    "1B": "EFGIJ",
    "1D": "BEFIJ",
    "1E": "ABCDF",
    "1G": "AEHIJ",
    "1I": "CDFGH",
    "1K": "DEIJL",
    "1L": "EHIJK",
}

THIRD_PLACE_COMBINATION_MAP = {
    "EFGHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "F", "1G": "H", "1I": "G", "1K": "L", "1L": "K"},
    "DFGHIJKL": {"1A": "H", "1B": "G", "1D": "I", "1E": "D", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "DEGHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "D", "1G": "H", "1I": "G", "1K": "L", "1L": "K"},
    "DEFHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "DEFGIJKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "D", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "DEFGHJKL": {"1A": "E", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "DEFGHIKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "DEFGHIJL": {"1A": "E", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "I"},
    "DEFGHIJK": {"1A": "E", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "I", "1L": "K"},
    "CFGHIJKL": {"1A": "H", "1B": "G", "1D": "I", "1E": "C", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "CEGHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "C", "1G": "H", "1I": "G", "1K": "L", "1L": "K"},
    "CEFHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "C", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CEFGIJKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "C", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "CEFGHJKL": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CEFGHIKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "C", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CEFGHIJL": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "F", "1K": "L", "1L": "I"},
    "CEFGHIJK": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "F", "1K": "I", "1L": "K"},
    "CDGHIJKL": {"1A": "H", "1B": "G", "1D": "I", "1E": "C", "1G": "J", "1I": "D", "1K": "L", "1L": "K"},
    "CDFHIJKL": {"1A": "C", "1B": "J", "1D": "I", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CDFGIJKL": {"1A": "C", "1B": "G", "1D": "I", "1E": "D", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "CDFGHJKL": {"1A": "C", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CDFGHIKL": {"1A": "C", "1B": "G", "1D": "I", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CDFGHIJL": {"1A": "C", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "I"},
    "CDFGHIJK": {"1A": "C", "1B": "G", "1D": "J", "1E": "D", "1G": "H", "1I": "F", "1K": "I", "1L": "K"},
    "CDEHIJKL": {"1A": "E", "1B": "J", "1D": "I", "1E": "C", "1G": "H", "1I": "D", "1K": "L", "1L": "K"},
    "CDEGIJKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "C", "1G": "J", "1I": "D", "1K": "L", "1L": "K"},
    "CDEGHJKL": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "D", "1K": "L", "1L": "K"},
    "CDEGHIKL": {"1A": "E", "1B": "G", "1D": "I", "1E": "C", "1G": "H", "1I": "D", "1K": "L", "1L": "K"},
    "CDEGHIJL": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "D", "1K": "L", "1L": "I"},
    "CDEGHIJK": {"1A": "E", "1B": "G", "1D": "J", "1E": "C", "1G": "H", "1I": "D", "1K": "I", "1L": "K"},
    "CDEFIJKL": {"1A": "C", "1B": "J", "1D": "E", "1E": "D", "1G": "I", "1I": "F", "1K": "L", "1L": "K"},
    "CDEFHJKL": {"1A": "C", "1B": "J", "1D": "E", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CDEFHIKL": {"1A": "C", "1B": "E", "1D": "I", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "K"},
    "CDEFHIJL": {"1A": "C", "1B": "J", "1D": "E", "1E": "D", "1G": "H", "1I": "F", "1K": "L", "1L": "I"},
    "CDEFHIJK": {"1A": "C", "1B": "J", "1D": "E", "1E": "D", "1G": "H", "1I": "F", "1K": "I", "1L": "K"},
    "CDEFGJKL": {"1A": "C", "1B": "G", "1D": "E", "1E": "D", "1G": "J", "1I": "F", "1K": "L", "1L": "K"},
    "CDEFGIKL": {"1A": "C", "1B": "G", "1D": "E", "1E": "D", "1G": "I", "1I": "F", "1K": "L", "1L": "K"},
    "CDEFGIJL": {"1A": "C", "1B": "G", "1D": "E", "1E": "D", "1G": "J", "1I": "F", "1K": "L", "1L": "I"},
    "CDEFGIJK": {"1A": "C", "1B": "G", "1D": "E", "1E": "D", "1G": "J", "1I": "F", "1K": "I", "1L": "K"},
}

BALANCED_OWNER_OVERRIDES = {
    "Austria": "Player 2",
    "Czechia": "Player 11",
    "England": "Player 5",
    "Ghana": "Player 3",
    "Jordan": "Player 7",
    "Qatar": "Player 4",
    "Saudi Arabia": "Player 6",
    "Scotland": "Player 9",
    "South Africa": "Player 7",
    "Sweden": "Player 1",
}

FALLBACK_STANDINGS = [
    {"group": "A", "team": "France", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 2, "gd": 2, "points": 3},
    {"group": "A", "team": "Spain", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 1, "gd": 1, "points": 3},
    {"group": "A", "team": "Argentina", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 0, "gd": -1, "points": 0},
    {"group": "A", "team": "England", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 0, "gd": -2, "points": 0},
    {"group": "B", "team": "Portugal", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 3, "gd": 2, "points": 3},
    {"group": "B", "team": "Brazil", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 2, "gd": 1, "points": 3},
    {"group": "B", "team": "Netherlands", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 1, "gd": -1, "points": 0},
    {"group": "B", "team": "Germany", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 1, "gd": -2, "points": 0},
    {"group": "C", "team": "Croatia", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 0, "gd": 0, "points": 1},
    {"group": "C", "team": "Belgium", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 0, "gd": 0, "points": 1},
    {"group": "C", "team": "Morocco", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 0, "gd": 0, "points": 1},
    {"group": "C", "team": "United States", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 0, "gd": 0, "points": 1},
]

FALLBACK_FIXTURES = [
    {"date": "2026-06-14", "time": "19:00", "home_team": "France", "away_team": "Spain", "city": "Mexico City", "score": "-"},
    {"date": "2026-06-14", "time": "22:00", "home_team": "Argentina", "away_team": "England", "city": "Los Angeles", "score": "-"},
    {"date": "2026-06-15", "time": "19:00", "home_team": "Portugal", "away_team": "Brazil", "city": "Dallas", "score": "-"},
    {"date": "2026-06-15", "time": "22:00", "home_team": "Netherlands", "away_team": "Germany", "city": "New York", "score": "-"},
    {"date": "2026-06-16", "time": "19:00", "home_team": "Croatia", "away_team": "Belgium", "city": "Toronto", "score": "-"},
    {"date": "2026-06-16", "time": "22:00", "home_team": "Morocco", "away_team": "United States", "city": "Seattle", "score": "-"},
]

POINTS_RULES = [
    {"Rule": "Match win", "Points": "3"},
    {"Rule": "Match draw", "Points": "1"},
    {"Rule": "Match loss", "Points": "0"},
    {"Rule": "Goal scored", "Points": "1"},
    {"Rule": "Owner total", "Points": "Match points + goals scored across all owned teams"},
]


def render_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(197, 233, 255, 0.85), transparent 35%),
                    radial-gradient(circle at top right, rgba(255, 225, 181, 0.9), transparent 30%),
                    linear-gradient(180deg, #f6f8fc 0%, #eef2f8 100%);
            }
            .block-container {
                padding-top: 1.75rem;
                padding-bottom: 2rem;
            }
            .section-title {
                font-size: 1.35rem;
                font-weight: 700;
                color: #0f172a;
                margin-top: 0.35rem;
                margin-bottom: 0.65rem;
            }
            .title-wrap h1 {
                font-size: 2.6rem;
                color: #0f172a;
                margin-bottom: 1rem;
            }
            .table-card {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 18px;
                padding: 0.35rem 0.35rem 0.15rem;
                box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
                overflow: hidden;
            }
            .group-card {
                background: rgba(255, 255, 255, 0.94);
                border: 2px solid rgba(59, 130, 246, 0.28);
                border-radius: 18px;
                box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
                margin-bottom: 1.2rem;
                overflow: hidden;
            }
            .group-card h3 {
                margin: 0;
                padding: 0.9rem 1rem 0.7rem;
                font-size: 1rem;
                color: #0f172a;
                border-bottom: 1px solid rgba(148, 163, 184, 0.22);
                background: linear-gradient(180deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.95));
            }
            table.custom-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.94rem;
            }
            table.custom-table th {
                text-align: left;
                font-weight: 700;
                font-size: 0.82rem;
                color: #475569;
                background: rgba(241, 245, 249, 0.9);
                padding: 0.72rem 0.8rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            }
            table.custom-table td {
                padding: 0.72rem 0.8rem;
                border-bottom: 1px solid rgba(226, 232, 240, 0.85);
                color: #0f172a;
                vertical-align: middle;
            }
            table.custom-table tr:last-child td {
                border-bottom: none;
            }
            .flag-cell {
                white-space: nowrap;
            }
            .flag-icon {
                width: 22px;
                height: 16px;
                object-fit: cover;
                border-radius: 3px;
                box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.10);
                vertical-align: middle;
            }
            .num-cell {
                text-align: right;
            }
            div[data-testid="stButton"] > button {
                min-height: 2rem;
                padding: 0.1rem 0.45rem;
                border-radius: 10px;
                border: 1px solid rgba(148, 163, 184, 0.35);
                background: rgba(255, 255, 255, 0.96);
                color: #0f172a;
                font-size: 0.9rem;
                font-weight: 700;
                box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
            }
            div[data-testid="stButton"] > button:disabled {
                color: rgba(15, 23, 42, 0.35);
                background: rgba(255, 255, 255, 0.7);
            }
            .fixture-date-label {
                color: #0f172a;
                font-weight: 700;
                font-size: 0.98rem;
                line-height: 2rem;
                text-align: left;
                padding-left: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def canonical_team_name(team_name: Optional[str]) -> str:
    if not team_name:
        return "-"
    return TEAM_ALIASES.get(team_name, team_name)


def team_flag(team_name: str) -> str:
    return TEAM_FLAGS.get(canonical_team_name(team_name), canonical_team_name(team_name))


def flag_icon(team_name: str) -> str:
    canonical_name = canonical_team_name(team_name)
    country_code = TEAM_FLAGS.get(canonical_name)
    if not country_code:
        return ""
    return (
        f'<img class="flag-icon" src="https://flagcdn.com/24x18/{country_code}.png" '
        f'alt="{canonical_name} flag" title="{canonical_name}">'
    )


def format_team_with_flag(team_name: str) -> str:
    canonical_name = canonical_team_name(team_name)
    icon = flag_icon(canonical_name)
    return f"{icon} {canonical_name}".strip()


def render_html_table(dataframe: pd.DataFrame, numeric_columns: set[str], table_class: str = "table-card") -> None:
    headers = "".join(f"<th>{column}</th>" for column in dataframe.columns)
    body_rows = []

    for _, row in dataframe.iterrows():
        cells = []
        for column in dataframe.columns:
            value = row[column]
            classes = []
            if column in numeric_columns:
                classes.append("num-cell")
            if column in {"Teams", "Flag", "Team 1 (Owner)", "Team 2 (Owner)", "Team 1", "Team 2"}:
                classes.append("flag-cell")
            class_attr = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{class_attr}>{value}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    wrapper_open = f'<div class="{table_class}">' if table_class else ""
    wrapper_close = "</div>" if table_class else ""
    st.markdown(
        f"""
        {wrapper_open}
            <table class="custom-table">
                <thead><tr>{headers}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
        {wrapper_close}
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_owners() -> pd.DataFrame:
    owners = pd.read_csv(DATA_DIR / "owners.csv")
    owners["team"] = owners["team"].apply(canonical_team_name)
    return owners.sort_values(["player", "team"]).reset_index(drop=True)


def apply_balanced_owner_overrides(owners: pd.DataFrame) -> pd.DataFrame:
    balanced_owners = owners.copy()
    balanced_owners["player"] = balanced_owners.apply(
        lambda row: BALANCED_OWNER_OVERRIDES.get(row["team"], row["player"]),
        axis=1,
    )
    return balanced_owners.sort_values(["player", "team"]).reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_denmark_kickoff(date_value: Optional[str], time_value: Optional[str]) -> tuple[str, str]:
    if not date_value:
        return "-", "-"
    if not time_value:
        return date_value, "-"

    raw_time = time_value.replace("Z", "+00:00")
    try:
        kickoff = datetime.fromisoformat(f"{date_value}T{raw_time}")
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        kickoff = kickoff.astimezone(DENMARK_TZ)
        return kickoff.strftime("%Y-%m-%d"), kickoff.strftime("%H:%M")
    except ValueError:
        return date_value, time_value[:5]


def fallback_standings() -> pd.DataFrame:
    return pd.DataFrame(FALLBACK_STANDINGS)


def parse_standings_payload(payload: dict) -> pd.DataFrame:
    rows = payload.get("table") or []
    parsed_rows = []

    for row in rows:
        parsed_rows.append(
            {
                "group": row.get("strGroup") or row.get("strDescription") or "Table",
                "team": canonical_team_name(row.get("strTeam") or row.get("name") or "-"),
                "played": int(row.get("intPlayed") or row.get("played") or 0),
                "won": int(row.get("intWin") or row.get("win") or 0),
                "drawn": int(row.get("intDraw") or row.get("draw") or 0),
                "lost": int(row.get("intLoss") or row.get("loss") or 0),
                "gf": int(row.get("intGoalsFor") or row.get("goalsfor") or 0),
                "gd": int(row.get("intGoalDifference") or row.get("goaldifference") or 0),
                "points": int(row.get("intPoints") or row.get("points") or 0),
            }
        )

    return pd.DataFrame(parsed_rows)


def load_standings() -> tuple[pd.DataFrame, bool]:
    try:
        payload = fetch_json(LIVE_TABLE_URL)
        standings = parse_standings_payload(payload)
        if not standings.empty:
            return standings, True
    except (URLError, TimeoutError, OSError, ValueError):
        pass
    return fallback_standings(), False


def build_owner_league_table(owners: pd.DataFrame, standings: pd.DataFrame) -> pd.DataFrame:
    merged = owners.merge(standings[["team", "points", "gf"]], on="team", how="left")
    merged["points"] = merged["points"].fillna(0).astype(int)
    merged["gf"] = merged["gf"].fillna(0).astype(int)
    merged["owner_points"] = merged["points"] + merged["gf"]

    league_table = (
        merged.groupby("player", as_index=False)
        .agg(
            Teams=("team", lambda teams: " ".join(flag_icon(team) for team in sorted(teams))),
            Points=("owner_points", "sum"),
        )
        .rename(columns={"player": "Owner"})
        .sort_values(["Points", "Owner"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return league_table[["Owner", "Teams", "Points"]]


def build_group_tables(standings: pd.DataFrame, owner_lookup: dict[str, str]) -> dict[str, pd.DataFrame]:
    standings_lookup = (
        standings.set_index("team")[["played", "won", "drawn", "lost", "gf", "gd", "points"]].to_dict("index")
        if not standings.empty
        else {}
    )

    tables = {}
    for group_name, teams in OFFICIAL_GROUPS.items():
        group_rows = []
        for team_name in teams:
            team_stats = standings_lookup.get(team_name, {})
            group_rows.append(
                {
                    "Flag": flag_icon(team_name),
                    "Team": canonical_team_name(team_name),
                    "Owner": owner_lookup.get(team_name, "Unassigned"),
                    "P": int(team_stats.get("played", 0)),
                    "W": int(team_stats.get("won", 0)),
                    "D": int(team_stats.get("drawn", 0)),
                    "L": int(team_stats.get("lost", 0)),
                    "GD": int(team_stats.get("gd", 0)),
                    "Pts": int(team_stats.get("points", 0)),
                }
            )

        group_table = pd.DataFrame(group_rows).sort_values(
            ["Pts", "GD", "W", "Team"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        tables[group_name] = group_table

    return tables


def build_group_rankings(standings: pd.DataFrame) -> dict[str, list[str]]:
    standings_lookup = (
        standings.set_index("team")[["played", "won", "drawn", "lost", "gf", "gd", "points"]].to_dict("index")
        if not standings.empty
        else {}
    )

    group_rankings = {}
    for group_name, teams in OFFICIAL_GROUPS.items():
        group_rows = []
        for team_name in teams:
            team_stats = standings_lookup.get(team_name)
            if not team_stats:
                group_rows = []
                break
            group_rows.append(
                {
                    "team": team_name,
                    "played": int(team_stats.get("played", 0)),
                    "points": int(team_stats.get("points", 0)),
                    "gd": int(team_stats.get("gd", 0)),
                    "gf": int(team_stats.get("gf", 0)),
                }
            )

        if len(group_rows) != 4 or any(row["played"] < 3 for row in group_rows):
            continue

        ranked_rows = sorted(
            group_rows,
            key=lambda row: (-row["points"], -row["gd"], -row["gf"], row["team"]),
        )
        group_rankings[group_name] = [row["team"] for row in ranked_rows]

    return group_rankings


def build_third_place_slot_assignments(
    standings: pd.DataFrame,
    group_rankings: dict[str, list[str]],
) -> dict[str, str]:
    if len(group_rankings) != len(OFFICIAL_GROUPS):
        return {}

    standings_lookup = (
        standings.set_index("team")[["points", "gd", "gf"]].to_dict("index")
        if not standings.empty
        else {}
    )

    third_place_rows = []
    for group_name, ranked_teams in group_rankings.items():
        third_team = ranked_teams[2]
        team_stats = standings_lookup.get(third_team)
        if not team_stats:
            return {}
        third_place_rows.append(
            {
                "group_letter": group_name[-1],
                "team": third_team,
                "points": int(team_stats.get("points", 0)),
                "gd": int(team_stats.get("gd", 0)),
                "gf": int(team_stats.get("gf", 0)),
            }
        )

    ranked_third_places = sorted(
        third_place_rows,
        key=lambda row: (-row["points"], -row["gd"], -row["gf"], row["group_letter"]),
    )
    qualified_group_letters = "".join(sorted(row["group_letter"] for row in ranked_third_places[:8]))
    return THIRD_PLACE_COMBINATION_MAP.get(qualified_group_letters, {})


def resolve_playoff_slot(
    slot_code: str,
    group_rankings: dict[str, list[str]],
    third_place_assignments: dict[str, str],
) -> str:
    if re.fullmatch(r"[12][A-L]", slot_code):
        position = int(slot_code[0]) - 1
        group_name = f"Group {slot_code[1]}"
        if group_name in group_rankings:
            return format_team_with_flag(group_rankings[group_name][position])
        suffix = "st" if slot_code[0] == "1" else "nd"
        return f"{slot_code[0]}{suffix} of {group_name}"

    if re.fullmatch(r"3[A-L]+", slot_code):
        groups = [f"Group {group_letter}" for group_letter in slot_code[1:]]
        if len(groups) == 1 and groups[0] in group_rankings:
            return format_team_with_flag(group_rankings[groups[0]][2])
        return f"Best 3rd from {' / '.join(groups)}"

    if re.fullmatch(r"3P1[A-L]", slot_code):
        winner_slot = slot_code[2:]
        pool_letters = THIRD_PLACE_SLOT_POOLS[winner_slot]
        assigned_group_letter = third_place_assignments.get(winner_slot)
        if assigned_group_letter:
            group_name = f"Group {assigned_group_letter}"
            if group_name in group_rankings:
                return format_team_with_flag(group_rankings[group_name][2])
        return f"Best 3rd from {' / '.join(f'Group {group_letter}' for group_letter in pool_letters)}"

    if re.fullmatch(r"W\d{2,3}", slot_code):
        return f"Winner of Match {slot_code[1:]}"

    if re.fullmatch(r"L\d{2,3}", slot_code):
        return f"Loser of Match {slot_code[1:]}"

    return slot_code


def build_playoff_tables(
    standings: pd.DataFrame,
    group_rankings: dict[str, list[str]],
) -> dict[str, pd.DataFrame]:
    round_tables: dict[str, list[dict]] = {}
    third_place_assignments = build_third_place_slot_assignments(standings, group_rankings)

    for match in PLAYOFF_MATCHES:
        round_tables.setdefault(match["round"], []).append(
            {
                "Match": match["match"],
                "Date": match["date"],
                "Team 1": resolve_playoff_slot(match["team_1"], group_rankings, third_place_assignments),
                "Team 2": resolve_playoff_slot(match["team_2"], group_rankings, third_place_assignments),
                "City": match["city"],
            }
        )

    return {round_name: pd.DataFrame(rows) for round_name, rows in round_tables.items()}


def parse_games_payload(payload: dict, owner_lookup: dict[str, str]) -> pd.DataFrame:
    rows = payload.get("events") or []
    parsed_rows = []

    for row in rows:
        home_team = canonical_team_name(row.get("strHomeTeam") or "-")
        away_team = canonical_team_name(row.get("strAwayTeam") or "-")
        date_value, time_value = parse_denmark_kickoff(row.get("dateEvent"), row.get("strTime"))
        home_score = row.get("intHomeScore")
        away_score = row.get("intAwayScore")

        parsed_rows.append(
            {
                "Date": date_value,
                "Time (Denmark)": time_value,
                "Team 1 (Owner)": f"{format_team_with_flag(home_team)} ({owner_lookup.get(home_team, 'Unassigned')})",
                "Team 2 (Owner)": f"{format_team_with_flag(away_team)} ({owner_lookup.get(away_team, 'Unassigned')})",
                "City": row.get("strCity") or row.get("strVenue") or "-",
                "Score": "-" if home_score is None or away_score is None else f"{home_score}-{away_score}",
            }
        )

    return pd.DataFrame(parsed_rows)


def fallback_games(owner_lookup: dict[str, str]) -> pd.DataFrame:
    games = pd.DataFrame(FALLBACK_FIXTURES)
    games["Team 1 (Owner)"] = games["home_team"].apply(
        lambda team: f"{format_team_with_flag(team)} ({owner_lookup.get(team, 'Unassigned')})"
    )
    games["Team 2 (Owner)"] = games["away_team"].apply(
        lambda team: f"{format_team_with_flag(team)} ({owner_lookup.get(team, 'Unassigned')})"
    )
    games = games.rename(
        columns={
            "date": "Date",
            "time": "Time (Denmark)",
            "city": "City",
            "score": "Score",
        }
    )
    return games[["Date", "Time (Denmark)", "Team 1 (Owner)", "Team 2 (Owner)", "City", "Score"]]


def load_upcoming_fixtures(owner_lookup: dict[str, str]) -> tuple[pd.DataFrame, bool]:
    try:
        payload = fetch_json(LIVE_SEASON_GAMES_URL)
        fixtures = parse_games_payload(payload, owner_lookup)
        if not fixtures.empty:
            today_denmark = datetime.now(DENMARK_TZ).strftime("%Y-%m-%d")
            upcoming_only = fixtures[fixtures["Date"] >= today_denmark].copy()
            if not upcoming_only.empty:
                return upcoming_only.sort_values(["Date", "Time (Denmark)"]).reset_index(drop=True), True
    except (URLError, TimeoutError, OSError, ValueError):
        pass
    return fallback_games(owner_lookup), False


render_styles()

owners = load_owners()
owners = apply_balanced_owner_overrides(owners)
owner_lookup = dict(zip(owners["team"], owners["player"]))
standings, live_table_loaded = load_standings()
owner_league_table = build_owner_league_table(owners, standings)
group_tables = build_group_tables(standings, owner_lookup)
group_rankings = build_group_rankings(standings)
playoff_tables = build_playoff_tables(standings, group_rankings)
upcoming_fixtures, live_fixtures_loaded = load_upcoming_fixtures(owner_lookup)

st.markdown('<div class="title-wrap"><h1>TIA X World Cup 26</h1></div>', unsafe_allow_html=True)

left_column, right_column = st.columns([1.55, 1])

with left_column:
    st.markdown('<div class="section-title">League Table</div>', unsafe_allow_html=True)
    render_html_table(owner_league_table, {"Points"})

with right_column:
    st.markdown('<div class="section-title">Points Rules</div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(POINTS_RULES),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rule": st.column_config.TextColumn(width="medium"),
            "Points": st.column_config.TextColumn(width="medium"),
        },
    )

st.markdown('<div class="section-title">Upcoming Fixtures</div>', unsafe_allow_html=True)

fixture_dates = sorted(upcoming_fixtures["Date"].dropna().unique().tolist())

if fixture_dates:
    max_index = len(fixture_dates) - 1
    if "fixture_date_index" not in st.session_state:
        st.session_state.fixture_date_index = 0
    st.session_state.fixture_date_index = max(0, min(st.session_state.fixture_date_index, max_index))

    previous_column, next_column, date_column, _spacer = st.columns([0.42, 0.42, 1.8, 7.36])
    with previous_column:
        previous_clicked = st.button(
            "◀",
            key="fixture_previous_date",
            disabled=st.session_state.fixture_date_index == 0,
            use_container_width=True,
        )
    with next_column:
        next_clicked = st.button(
            "▶",
            key="fixture_next_date",
            disabled=st.session_state.fixture_date_index == max_index,
            use_container_width=True,
        )

    if previous_clicked and st.session_state.fixture_date_index > 0:
        st.session_state.fixture_date_index -= 1
    if next_clicked and st.session_state.fixture_date_index < max_index:
        st.session_state.fixture_date_index += 1

    selected_fixture_date = fixture_dates[st.session_state.fixture_date_index]
    with date_column:
        st.markdown(
            f"<div class='fixture-date-label'>{selected_fixture_date}</div>",
            unsafe_allow_html=True,
        )

    daily_games = upcoming_fixtures[upcoming_fixtures["Date"] == selected_fixture_date].reset_index(drop=True)
    render_html_table(daily_games, set())
else:
    st.info("No fixtures available.")

st.markdown('<div class="section-title">Group Tables</div>', unsafe_allow_html=True)

group_names = list(group_tables.keys())

if group_names:
    for start_index in range(0, len(group_names), 3):
        row_columns = st.columns(3)
        for column, group_name in zip(row_columns, group_names[start_index:start_index + 3]):
            with column:
                st.markdown(f'<div class="group-card"><h3>{group_name}</h3>', unsafe_allow_html=True)
                render_html_table(group_tables[group_name], {"P", "W", "D", "L", "GD", "Pts"}, table_class="")
                st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No group standings available.")

st.markdown('<div class="section-title">Playoffs</div>', unsafe_allow_html=True)

for round_name, round_table in playoff_tables.items():
    st.markdown(f"<div style='font-weight:700; color:#0f172a; margin:0.4rem 0 0.55rem 0;'>{round_name}</div>", unsafe_allow_html=True)
    render_html_table(round_table, {"Match"}, table_class="table-card")

st.caption(
    "Live standings and fixtures attempt to load from TheSportsDB's public World Cup feed. The app falls back to local sample data when that feed is unavailable."
)
