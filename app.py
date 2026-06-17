import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
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
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_API_TOKEN", "").strip()
DATA_DIR = Path(__file__).resolve().parent
CHAT_MESSAGES_PATH = DATA_DIR / "chat_messages.jsonl"
DENMARK_TZ = ZoneInfo("Europe/Copenhagen")
CHAT_OWNER_STATE_KEY = "chat_selected_owner"
REFRESH_INTERVAL_SECONDS = 30
WIKIPEDIA_API_TEMPLATE = "https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles={title}"

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

WIKIPEDIA_GROUP_PAGE_TITLES = {
    group_name: f"2026_FIFA_World_Cup_{group_name.replace(' ', '_')}"
    for group_name in OFFICIAL_GROUPS
}

TEAM_CODE_TO_NAME = {
    "ALG": "Algeria",
    "ARG": "Argentina",
    "AUS": "Australia",
    "AUT": "Austria",
    "BEL": "Belgium",
    "BIH": "Bosnia and Herzegovina",
    "BRA": "Brazil",
    "CAN": "Canada",
    "COD": "DR Congo",
    "COL": "Colombia",
    "CPV": "Cape Verde",
    "CIV": "Ivory Coast",
    "CRO": "Croatia",
    "CUW": "Curacao",
    "CZE": "Czechia",
    "ECU": "Ecuador",
    "EGY": "Egypt",
    "ENG": "England",
    "FRA": "France",
    "GER": "Germany",
    "GHA": "Ghana",
    "HTI": "Haiti",
    "IRQ": "Iraq",
    "IRN": "Iran",
    "JOR": "Jordan",
    "JPN": "Japan",
    "KOR": "South Korea",
    "KSA": "Saudi Arabia",
    "MAR": "Morocco",
    "MEX": "Mexico",
    "NED": "Netherlands",
    "NOR": "Norway",
    "NZL": "New Zealand",
    "PAN": "Panama",
    "PAR": "Paraguay",
    "POR": "Portugal",
    "QAT": "Qatar",
    "RSA": "South Africa",
    "SCO": "Scotland",
    "SEN": "Senegal",
    "ESP": "Spain",
    "SUI": "Switzerland",
    "SWE": "Sweden",
    "TUN": "Tunisia",
    "TUR": "Turkiye",
    "URU": "Uruguay",
    "USA": "United States",
    "UZB": "Uzbekistan",
}

VENUE_TIMEZONES = {
    "Arrowhead Stadium": ZoneInfo("America/Chicago"),
    "AT&T Stadium": ZoneInfo("America/Chicago"),
    "BC Place": ZoneInfo("America/Vancouver"),
    "BMO Field": ZoneInfo("America/Toronto"),
    "Estadio Akron": ZoneInfo("America/Mexico_City"),
    "Estadio Azteca": ZoneInfo("America/Mexico_City"),
    "Estadio BBVA": ZoneInfo("America/Monterrey"),
    "Gillette Stadium": ZoneInfo("America/New_York"),
    "Hard Rock Stadium": ZoneInfo("America/New_York"),
    "Levi's Stadium": ZoneInfo("America/Los_Angeles"),
    "Lincoln Financial Field": ZoneInfo("America/New_York"),
    "Lumen Field": ZoneInfo("America/Los_Angeles"),
    "Mercedes-Benz Stadium": ZoneInfo("America/New_York"),
    "MetLife Stadium": ZoneInfo("America/New_York"),
    "NRG Stadium": ZoneInfo("America/Chicago"),
    "SoFi Stadium": ZoneInfo("America/Los_Angeles"),
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
                padding-left: 1.1rem;
                padding-right: 1.1rem;
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
            .table-scroll {
                width: 100%;
                overflow-x: auto;
                overflow-y: hidden;
                -webkit-overflow-scrolling: touch;
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
            table.custom-table th.num-cell {
                text-align: right;
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
            .flag-tooltip {
                position: relative;
                display: inline-flex;
                align-items: center;
                margin-right: 0.2rem;
            }
            .flag-tooltip:last-child {
                margin-right: 0;
            }
            .flag-tooltip::after {
                content: attr(data-tooltip);
                position: absolute;
                left: 50%;
                bottom: calc(100% + 6px);
                transform: translateX(-50%);
                background: rgba(15, 23, 42, 0.96);
                color: #fff;
                padding: 0.28rem 0.45rem;
                border-radius: 6px;
                font-size: 0.74rem;
                line-height: 1.1;
                white-space: nowrap;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.12s ease;
                z-index: 20;
            }
            .flag-tooltip:hover::after {
                opacity: 1;
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
            .chat-feed {
                background: linear-gradient(180deg, rgba(241, 245, 249, 0.96), rgba(226, 232, 240, 0.92));
                border: 1px solid rgba(148, 163, 184, 0.26);
                border-radius: 18px;
                box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
                max-height: 340px;
                overflow-y: auto;
                padding: 0.25rem 0;
            }
            .chat-message {
                padding: 0.8rem 0.95rem;
                border-bottom: 1px solid rgba(226, 232, 240, 0.85);
                background: rgba(248, 250, 252, 0.68);
            }
            .chat-message:last-child {
                border-bottom: none;
            }
            .chat-meta {
                color: #475569;
                font-size: 0.76rem;
                margin-bottom: 0.28rem;
            }
            .chat-body {
                color: #0f172a;
                font-size: 0.93rem;
                line-height: 1.45;
                word-break: break-word;
            }
            .chat-empty {
                color: #64748b;
                font-size: 0.9rem;
                padding: 0.95rem 1rem;
            }
            .chat-field-label {
                color: #334155;
                font-size: 0.8rem;
                font-weight: 700;
                margin: 0 0 0.35rem 0.1rem;
            }
            div[data-testid="stForm"] {
                background: linear-gradient(180deg, rgba(241, 245, 249, 0.96), rgba(226, 232, 240, 0.92));
                border: 1px solid rgba(148, 163, 184, 0.26);
                border-radius: 18px;
                box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
                padding: 0.8rem 0.8rem 0.35rem;
            }
            div[data-testid="stForm"] form,
            div[data-testid="stForm"] fieldset {
                border: none !important;
                background: transparent !important;
                padding: 0 !important;
                margin: 0 !important;
                min-width: 0 !important;
            }
            div[data-testid="stForm"] legend {
                display: none !important;
            }
            div[data-baseweb="select"] span,
            div[data-baseweb="select"] input,
            div[data-baseweb="select"] div,
            div[data-baseweb="select"] * {
                color: #000 !important;
            }
            div[role="listbox"] div {
                color: #000 !important;
            }
            div[data-testid="stTextArea"] label,
            div[data-testid="stTextArea"] textarea {
                color: #000 !important;
            }
            div[data-baseweb="select"] > div,
            div[data-testid="stTextArea"] textarea {
                background: rgba(248, 250, 252, 0.86) !important;
                border: 1px solid rgba(148, 163, 184, 0.3) !important;
            }
            div[data-testid="stDataFrame"] {
                overflow-x: auto;
            }
            @media (max-width: 900px) {
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 1.35rem;
                    padding-left: 0.8rem;
                    padding-right: 0.8rem;
                }
                .title-wrap h1 {
                    font-size: 1.9rem;
                    line-height: 1.08;
                    margin-bottom: 0.8rem;
                }
                .section-title {
                    font-size: 1.15rem;
                    margin-bottom: 0.55rem;
                }
                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap;
                    gap: 0.85rem !important;
                }
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                    min-width: 100% !important;
                    flex: 1 1 100% !important;
                }
                .table-card,
                .group-card,
                .chat-feed,
                div[data-testid="stForm"] {
                    border-radius: 16px;
                }
                table.custom-table {
                    min-width: 680px;
                    font-size: 0.86rem;
                }
                table.custom-table th,
                table.custom-table td {
                    padding: 0.64rem 0.68rem;
                }
                .group-card h3 {
                    padding: 0.75rem 0.85rem 0.65rem;
                }
                .fixture-date-label {
                    padding-left: 0;
                    line-height: 1.35;
                }
                .chat-feed {
                    max-height: 280px;
                }
                div[data-testid="stButton"] > button {
                    min-height: 2.15rem;
                }
            }
            @media (max-width: 560px) {
                .title-wrap h1 {
                    font-size: 1.65rem;
                }
                .section-title {
                    font-size: 1.05rem;
                }
                table.custom-table {
                    min-width: 620px;
                    font-size: 0.82rem;
                }
                table.custom-table th,
                table.custom-table td {
                    padding: 0.58rem 0.6rem;
                }
                .chat-feed {
                    max-height: 240px;
                }
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
        f'<span class="flag-tooltip" data-tooltip="{canonical_name}">'
        f'<img class="flag-icon" src="https://flagcdn.com/24x18/{country_code}.png" '
        f'alt="{canonical_name} flag">'
        f"</span>"
    )


def format_team_with_flag(team_name: str) -> str:
    canonical_name = canonical_team_name(team_name)
    icon = flag_icon(canonical_name)
    return f"{icon} {canonical_name}".strip()


def render_html_table(dataframe: pd.DataFrame, numeric_columns: set[str], table_class: str = "table-card") -> None:
    headers = "".join(
        (f'<th class="num-cell">{column}</th>' if column in numeric_columns else f"<th>{column}</th>")
        for column in dataframe.columns
    )
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
            <div class="table-scroll">
                <table class="custom-table">
                    <thead><tr>{headers}</tr></thead>
                    <tbody>{''.join(body_rows)}</tbody>
                </table>
            </div>
        {wrapper_close}
        """,
        unsafe_allow_html=True,
    )


def build_chat_owner_options(owners: pd.DataFrame) -> list[str]:
    return sorted(owners["player"].unique().tolist())


@st.cache_data(show_spinner=False)
def load_owners(file_mtime: float) -> pd.DataFrame:
    owners_path = DATA_DIR / "owners.csv"
    last_error = None

    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            owners = pd.read_csv(owners_path, encoding=encoding)
            break
        except UnicodeDecodeError as error:
            last_error = error
    else:
        raise last_error

    owners["team"] = owners["team"].apply(canonical_team_name)
    return owners.sort_values(["player", "team"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def fetch_json(url: str, day_key: str, auth_token: str = "", unfold_goals: bool = False) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    if auth_token:
        headers["X-Auth-Token"] = auth_token
    if unfold_goals:
        headers["X-Unfold-Goals"] = "true"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=8) as response:
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


def current_refresh_key(interval_seconds: int) -> str:
    now = datetime.now(DENMARK_TZ)
    return f"{now.strftime('%Y-%m-%d')}-{int(now.timestamp() // interval_seconds)}"


def wikipedia_api_url(page_title: str) -> str:
    return WIKIPEDIA_API_TEMPLATE.format(title=quote(page_title))


def strip_wiki_markup(value: str) -> str:
    cleaned = value.replace("&nbsp;", " ")
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", cleaned)
    cleaned = re.sub(r"\[\[([^\]]+)\]\]", r"\1", cleaned)
    return re.sub(r"\s+", " ", html.unescape(cleaned)).strip(" ,")


def extract_wiki_field(block: str, field_name: str) -> str:
    match = re.search(
        rf"\|{re.escape(field_name)}=(.*?)(?=\n\|[A-Za-z0-9_]+=|\Z)",
        block,
        flags=re.S,
    )
    return match.group(1).strip() if match else ""


def parse_wikipedia_score(score_value: str, goals_1: str, goals_2: str) -> tuple[Optional[int], Optional[int]]:
    if not score_value or "Match " in score_value:
        return None, None

    score_token = re.sub(r"[{}]", "", score_value.rsplit("|", 1)[-1]).strip()
    explicit_score = re.search(r"(\d+)[^\d]+(\d+)", score_token)
    if explicit_score:
        return int(explicit_score.group(1)), int(explicit_score.group(2))

    compact_token = re.sub(r"\s+", "", score_token)
    if compact_token.isdigit():
        if len(compact_token) == 2:
            return int(compact_token[0]), int(compact_token[1])
        if len(compact_token) >= 3:
            return int(compact_token[:-1]), int(compact_token[-1])

    goals_1_total = len(re.findall(r"\{\{goal\|", goals_1 or ""))
    goals_2_total = len(re.findall(r"\{\{goal\|", goals_2 or ""))
    if goals_1_total or goals_2_total:
        return goals_1_total, goals_2_total

    return None, None


def parse_wikipedia_time_to_denmark(date_value: str, time_value: str, venue_value: str) -> tuple[str, str]:
    cleaned_time = strip_wiki_markup(time_value).replace("a.m.", "AM").replace("p.m.", "PM")
    cleaned_time = cleaned_time.replace("a.m", "AM").replace("p.m", "PM").upper()
    cleaned_time = re.sub(r"\s+UTC.*$", "", cleaned_time).strip()

    venue_timezone = None
    for venue_name, timezone_name in VENUE_TIMEZONES.items():
        if venue_name in venue_value:
            venue_timezone = timezone_name
            break

    if not cleaned_time or venue_timezone is None:
        return date_value, "-"

    try:
        local_kickoff = datetime.strptime(f"{date_value} {cleaned_time}", "%Y-%m-%d %I:%M %p").replace(
            tzinfo=venue_timezone
        )
        denmark_kickoff = local_kickoff.astimezone(DENMARK_TZ)
        return denmark_kickoff.strftime("%Y-%m-%d"), denmark_kickoff.strftime("%H:%M")
    except ValueError:
        return date_value, "-"


def load_chat_messages() -> list[dict]:
    if not CHAT_MESSAGES_PATH.exists():
        return []

    messages = []
    with CHAT_MESSAGES_PATH.open("r", encoding="utf-8") as chat_file:
        for line in chat_file:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return messages


def append_chat_message(owner_name: str, message: str) -> None:
    CHAT_MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(DENMARK_TZ).isoformat(timespec="seconds"),
        "owner": owner_name,
        "message": message.strip(),
    }
    with CHAT_MESSAGES_PATH.open("a", encoding="utf-8") as chat_file:
        chat_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def render_chat_feed(messages: list[dict]) -> None:
    if not messages:
        st.markdown('<div class="chat-feed"><div class="chat-empty">No messages yet.</div></div>', unsafe_allow_html=True)
        return

    recent_messages = messages[-30:]
    message_html = []
    for entry in recent_messages:
        owner_name = entry.get("owner", "Unassigned")
        timestamp = entry.get("timestamp", "")
        message_text = html.escape(entry.get("message", ""))
        display_time = timestamp.replace("T", " ")[:16] if timestamp else ""
        message_html.append(
            f'<div class="chat-message">'
            f'<div class="chat-meta">{html.escape(owner_name)} · {html.escape(display_time)}</div>'
            f'<div class="chat-body">{message_text}</div>'
            f'</div>'
        )

    st.markdown(f'<div class="chat-feed">{"".join(message_html)}</div>', unsafe_allow_html=True)


def fallback_standings() -> pd.DataFrame:
    rows = []
    for group_name, teams in OFFICIAL_GROUPS.items():
        group_letter = group_name.split()[-1]
        for team_name in teams:
            rows.append(
                {
                    "group": group_letter,
                    "team": team_name,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "gd": 0,
                    "points": 0,
                }
            )
    return pd.DataFrame(rows)


def parse_wikipedia_group_page(wikitext: str, group_name: str) -> list[dict]:
    match_pattern = re.compile(
        r"<section begin=(?P<section>[A-Z]\d+)\s*/>\{\{#invoke:football box\|main(?P<body>.*?)\}\}<section end=(?P=section)\s*/>",
        flags=re.S,
    )
    parsed_matches = []

    for match in match_pattern.finditer(wikitext):
        block = match.group("body")
        team_1_code = re.search(r"\|([A-Z]{3})\}\}$", extract_wiki_field(block, "team1"))
        team_2_code = re.search(r"\|([A-Z]{3})\}\}$", extract_wiki_field(block, "team2"))

        if not team_1_code or not team_2_code:
            continue

        team_1 = TEAM_CODE_TO_NAME.get(team_1_code.group(1))
        team_2 = TEAM_CODE_TO_NAME.get(team_2_code.group(1))
        if not team_1 or not team_2:
            continue

        date_match = re.search(r"\{\{Start date\|(\d{4})\|(\d{1,2})\|(\d{1,2})\}\}", extract_wiki_field(block, "date"))
        if not date_match:
            continue

        date_value = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        time_value = extract_wiki_field(block, "time")
        venue_value = strip_wiki_markup(extract_wiki_field(block, "stadium"))
        score_value = extract_wiki_field(block, "score")
        goals_1 = extract_wiki_field(block, "goals1")
        goals_2 = extract_wiki_field(block, "goals2")
        home_score, away_score = parse_wikipedia_score(score_value, goals_1, goals_2)
        denmark_date, denmark_time = parse_wikipedia_time_to_denmark(date_value, time_value, venue_value)

        parsed_matches.append(
            {
                "group": group_name.split()[-1],
                "date": denmark_date,
                "time": denmark_time,
                "home_team": canonical_team_name(team_1),
                "away_team": canonical_team_name(team_2),
                "city": venue_value or "-",
                "home_score": home_score,
                "away_score": away_score,
            }
        )

    return parsed_matches


@st.cache_data(show_spinner=False)
def load_wikipedia_group_stage_data(day_key: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = []
    for group_name, page_title in WIKIPEDIA_GROUP_PAGE_TITLES.items():
        payload = fetch_json(wikipedia_api_url(page_title), day_key)
        pages = payload.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        revisions = page.get("revisions") or []
        if not revisions:
            continue

        wikitext = revisions[0].get("*", "")
        if not wikitext:
            continue

        matches.extend(parse_wikipedia_group_page(wikitext, group_name))

    matches_dataframe = pd.DataFrame(matches)
    if matches_dataframe.empty:
        return fallback_standings(), pd.DataFrame()

    standings_rows = []
    for group_name, teams in OFFICIAL_GROUPS.items():
        group_letter = group_name.split()[-1]
        group_matches = matches_dataframe[
            (matches_dataframe["group"] == group_letter)
            & matches_dataframe["home_score"].notna()
            & matches_dataframe["away_score"].notna()
        ]

        for team_name in teams:
            team_matches = group_matches[
                (group_matches["home_team"] == team_name) | (group_matches["away_team"] == team_name)
            ]
            played = len(team_matches)
            won = drawn = lost = gf = ga = 0

            for _, match_row in team_matches.iterrows():
                is_home_team = match_row["home_team"] == team_name
                team_goals = int(match_row["home_score"] if is_home_team else match_row["away_score"])
                opponent_goals = int(match_row["away_score"] if is_home_team else match_row["home_score"])
                gf += team_goals
                ga += opponent_goals
                if team_goals > opponent_goals:
                    won += 1
                elif team_goals == opponent_goals:
                    drawn += 1
                else:
                    lost += 1

            standings_rows.append(
                {
                    "group": group_letter,
                    "team": team_name,
                    "played": played,
                    "won": won,
                    "drawn": drawn,
                    "lost": lost,
                    "gf": gf,
                    "gd": gf - ga,
                    "points": won * 3 + drawn,
                }
            )

    return pd.DataFrame(standings_rows), matches_dataframe


def build_fixture_table_from_matches(matches: pd.DataFrame, owner_lookup: dict[str, str]) -> pd.DataFrame:
    if matches.empty:
        return pd.DataFrame(columns=["Date", "Time (Denmark)", "Team 1 (Owner)", "Team 2 (Owner)", "City", "Score"])

    fixtures = matches.copy()
    fixtures["Team 1 (Owner)"] = fixtures["home_team"].apply(
        lambda team: f"{format_team_with_flag(team)} ({owner_lookup.get(team, 'Unassigned')})"
    )
    fixtures["Team 2 (Owner)"] = fixtures["away_team"].apply(
        lambda team: f"{format_team_with_flag(team)} ({owner_lookup.get(team, 'Unassigned')})"
    )
    fixtures["Score"] = fixtures.apply(
        lambda row: "-"
        if pd.isna(row["home_score"]) or pd.isna(row["away_score"])
        else f"{int(row['home_score'])}-{int(row['away_score'])}",
        axis=1,
    )
    fixtures = fixtures.rename(
        columns={
            "date": "Date",
            "time": "Time (Denmark)",
            "city": "City",
        }
    )
    return fixtures[["Date", "Time (Denmark)", "Team 1 (Owner)", "Team 2 (Owner)", "City", "Score"]]


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


def parse_football_data_standings_payload(payload: dict) -> pd.DataFrame:
    standings_rows = []

    for standings_block in payload.get("standings") or []:
        group_name = standings_block.get("group") or "GROUP_STAGE"
        group_letter = group_name.replace("GROUP_", "")
        for row in standings_block.get("table") or []:
            team_data = row.get("team") or {}
            standings_rows.append(
                {
                    "group": group_letter,
                    "team": canonical_team_name(team_data.get("name") or "-"),
                    "played": int(row.get("playedGames") or 0),
                    "won": int(row.get("won") or 0),
                    "drawn": int(row.get("draw") or 0),
                    "lost": int(row.get("lost") or 0),
                    "gf": int(row.get("goalsFor") or 0),
                    "gd": int(row.get("goalDifference") or 0),
                    "points": int(row.get("points") or 0),
                }
            )

    return pd.DataFrame(standings_rows)


def parse_football_data_matches_payload(payload: dict, owner_lookup: dict[str, str]) -> pd.DataFrame:
    fixture_rows = []

    for row in payload.get("matches") or []:
        home_team = canonical_team_name((row.get("homeTeam") or {}).get("name") or "-")
        away_team = canonical_team_name((row.get("awayTeam") or {}).get("name") or "-")

        utc_date = row.get("utcDate") or ""
        date_value = utc_date[:10] if len(utc_date) >= 10 else "-"
        time_value = utc_date[11:19] if len(utc_date) >= 19 else None
        denmark_date, denmark_time = parse_denmark_kickoff(date_value, time_value)

        score = row.get("score") or {}
        regular_time = score.get("regularTime") or {}
        home_score = regular_time.get("home")
        away_score = regular_time.get("away")

        fixture_rows.append(
            {
                "Date": denmark_date,
                "Time (Denmark)": denmark_time,
                "Team 1 (Owner)": f"{format_team_with_flag(home_team)} ({owner_lookup.get(home_team, 'Unassigned')})",
                "Team 2 (Owner)": f"{format_team_with_flag(away_team)} ({owner_lookup.get(away_team, 'Unassigned')})",
                "City": row.get("venue") or "-",
                "Score": "-" if home_score is None or away_score is None else f"{home_score}-{away_score}",
            }
        )

    return pd.DataFrame(fixture_rows)


def load_football_data_standings(day_key: str) -> tuple[pd.DataFrame, bool]:
    if not FOOTBALL_DATA_TOKEN:
        return pd.DataFrame(), False

    try:
        payload = fetch_json(
            f"{FOOTBALL_DATA_BASE_URL}/competitions/WC/standings?season=2026",
            day_key,
            auth_token=FOOTBALL_DATA_TOKEN,
        )
        standings = parse_football_data_standings_payload(payload)
        if not standings.empty:
            return standings, True
    except (URLError, TimeoutError, OSError, ValueError):
        pass

    return pd.DataFrame(), False


def load_football_data_fixtures(owner_lookup: dict[str, str], day_key: str) -> tuple[pd.DataFrame, bool]:
    if not FOOTBALL_DATA_TOKEN:
        return pd.DataFrame(), False

    try:
        payload = fetch_json(
            f"{FOOTBALL_DATA_BASE_URL}/competitions/WC/matches?season=2026",
            day_key,
            auth_token=FOOTBALL_DATA_TOKEN,
            unfold_goals=True,
        )
        fixtures = parse_football_data_matches_payload(payload, owner_lookup)
        if not fixtures.empty:
            return fixtures, True
    except (URLError, TimeoutError, OSError, ValueError):
        pass

    return pd.DataFrame(), False


def load_standings(day_key: str) -> tuple[pd.DataFrame, bool]:
    football_data_standings, football_data_loaded = load_football_data_standings(day_key)
    if football_data_loaded:
        return football_data_standings, True

    wiki_standings, wiki_matches = load_wikipedia_group_stage_data(day_key)
    if not wiki_matches.empty:
        return wiki_standings, True

    try:
        payload = fetch_json(LIVE_TABLE_URL, day_key)
        standings = parse_standings_payload(payload)
        if not standings.empty:
            return standings, True
    except (URLError, TimeoutError, OSError, ValueError):
        pass
    return fallback_standings(), False


def build_owner_league_table(owners: pd.DataFrame, standings: pd.DataFrame) -> pd.DataFrame:
    merged = owners.merge(standings[["team", "won", "drawn", "lost", "gf", "points"]], on="team", how="left")
    merged["won"] = merged["won"].fillna(0).astype(int)
    merged["drawn"] = merged["drawn"].fillna(0).astype(int)
    merged["lost"] = merged["lost"].fillna(0).astype(int)
    merged["points"] = merged["points"].fillna(0).astype(int)
    merged["gf"] = merged["gf"].fillna(0).astype(int)
    merged["owner_points"] = merged["points"] + merged["gf"]

    league_table = (
        merged.groupby("player", as_index=False)
        .agg(
            Teams=("team", lambda teams: " ".join(flag_icon(team) for team in sorted(teams))),
            W=("won", "sum"),
            D=("drawn", "sum"),
            L=("lost", "sum"),
            GF=("gf", "sum"),
            Points=("owner_points", "sum"),
        )
        .rename(columns={"player": "Owner"})
        .sort_values(["Points", "GF", "W", "Owner"], ascending=[False, False, False, True])
        .reset_index(drop=True)
    )
    return league_table[["Owner", "Teams", "W", "D", "L", "GF", "Points"]]


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


def format_team_or_placeholder(value: str, owner_lookup: dict[str, str], include_owner: bool) -> str:
    if value in owner_lookup:
        formatted_team = format_team_with_flag(value)
        return f"{formatted_team} ({owner_lookup[value]})" if include_owner else formatted_team
    return value


def resolve_playoff_slot_raw(
    slot_code: str,
    group_rankings: dict[str, list[str]],
    third_place_assignments: dict[str, str],
) -> str:
    if re.fullmatch(r"[12][A-L]", slot_code):
        position = int(slot_code[0]) - 1
        group_name = f"Group {slot_code[1]}"
        if group_name in group_rankings:
            return group_rankings[group_name][position]
        suffix = "st" if slot_code[0] == "1" else "nd"
        return f"{slot_code[0]}{suffix} of {group_name}"

    if re.fullmatch(r"3[A-L]+", slot_code):
        groups = [f"Group {group_letter}" for group_letter in slot_code[1:]]
        if len(groups) == 1 and groups[0] in group_rankings:
            return group_rankings[groups[0]][2]
        return f"Best 3rd from {' / '.join(groups)}"

    if re.fullmatch(r"3P1[A-L]", slot_code):
        winner_slot = slot_code[2:]
        pool_letters = THIRD_PLACE_SLOT_POOLS[winner_slot]
        assigned_group_letter = third_place_assignments.get(winner_slot)
        if assigned_group_letter:
            group_name = f"Group {assigned_group_letter}"
            if group_name in group_rankings:
                return group_rankings[group_name][2]
        return f"Best 3rd from {' / '.join(f'Group {group_letter}' for group_letter in pool_letters)}"

    if re.fullmatch(r"W\d{2,3}", slot_code):
        return f"Winner of Match {slot_code[1:]}"

    if re.fullmatch(r"L\d{2,3}", slot_code):
        return f"Loser of Match {slot_code[1:]}"

    return slot_code


def build_playoff_tables(
    standings: pd.DataFrame,
    group_rankings: dict[str, list[str]],
    owner_lookup: dict[str, str],
) -> dict[str, pd.DataFrame]:
    round_tables: dict[str, list[dict]] = {}
    third_place_assignments = build_third_place_slot_assignments(standings, group_rankings)

    for match in PLAYOFF_MATCHES:
        raw_team_1 = resolve_playoff_slot_raw(match["team_1"], group_rankings, third_place_assignments)
        raw_team_2 = resolve_playoff_slot_raw(match["team_2"], group_rankings, third_place_assignments)
        round_tables.setdefault(match["round"], []).append(
            {
                "Match": match["match"],
                "Date": match["date"],
                "Team 1": format_team_or_placeholder(raw_team_1, owner_lookup, include_owner=False),
                "Team 2": format_team_or_placeholder(raw_team_2, owner_lookup, include_owner=False),
                "City": match["city"],
            }
        )

    return {round_name: pd.DataFrame(rows) for round_name, rows in round_tables.items()}


def build_playoff_fixture_table(
    standings: pd.DataFrame,
    group_rankings: dict[str, list[str]],
    owner_lookup: dict[str, str],
) -> pd.DataFrame:
    third_place_assignments = build_third_place_slot_assignments(standings, group_rankings)
    rows = []

    for match in PLAYOFF_MATCHES:
        raw_team_1 = resolve_playoff_slot_raw(match["team_1"], group_rankings, third_place_assignments)
        raw_team_2 = resolve_playoff_slot_raw(match["team_2"], group_rankings, third_place_assignments)
        rows.append(
            {
                "Date": match["date"],
                "Time (Denmark)": "-",
                "Team 1 (Owner)": format_team_or_placeholder(raw_team_1, owner_lookup, include_owner=True),
                "Team 2 (Owner)": format_team_or_placeholder(raw_team_2, owner_lookup, include_owner=True),
                "City": match["city"],
                "Score": "-",
            }
        )

    return pd.DataFrame(rows)


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
    del owner_lookup
    return pd.DataFrame(columns=["Date", "Time (Denmark)", "Team 1 (Owner)", "Team 2 (Owner)", "City", "Score"])


def load_upcoming_fixtures(owner_lookup: dict[str, str], day_key: str) -> tuple[pd.DataFrame, bool]:
    football_data_fixtures, football_data_loaded = load_football_data_fixtures(owner_lookup, day_key)
    if football_data_loaded:
        today_denmark = datetime.now(DENMARK_TZ).strftime("%Y-%m-%d")
        upcoming_football_data = football_data_fixtures[football_data_fixtures["Date"] >= today_denmark].copy()
        if not upcoming_football_data.empty:
            return upcoming_football_data.sort_values(["Date", "Time (Denmark)", "City"]).reset_index(drop=True), True

    _wiki_standings, wiki_matches = load_wikipedia_group_stage_data(day_key)
    if not wiki_matches.empty:
        wikipedia_fixtures = build_fixture_table_from_matches(wiki_matches, owner_lookup)
        today_denmark = datetime.now(DENMARK_TZ).strftime("%Y-%m-%d")
        upcoming_wikipedia = wikipedia_fixtures[wikipedia_fixtures["Date"] >= today_denmark].copy()
        if not upcoming_wikipedia.empty:
            return upcoming_wikipedia.sort_values(["Date", "Time (Denmark)", "City"]).reset_index(drop=True), True

    try:
        payload = fetch_json(LIVE_SEASON_GAMES_URL, day_key)
        fixtures = parse_games_payload(payload, owner_lookup)
        if not fixtures.empty:
            today_denmark = datetime.now(DENMARK_TZ).strftime("%Y-%m-%d")
            upcoming_only = fixtures[fixtures["Date"] >= today_denmark].copy()
            if not upcoming_only.empty:
                return upcoming_only.sort_values(["Date", "Time (Denmark)"]).reset_index(drop=True), True
    except (URLError, TimeoutError, OSError, ValueError):
        pass
    return fallback_games(owner_lookup), False


def load_live_dashboard_data(owners: pd.DataFrame, owner_lookup: dict[str, str]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    refresh_key = current_refresh_key(REFRESH_INTERVAL_SECONDS)
    standings, _live_table_loaded = load_standings(refresh_key)
    owner_league_table = build_owner_league_table(owners, standings)
    group_tables = build_group_tables(standings, owner_lookup)
    group_rankings = build_group_rankings(standings)
    playoff_tables = build_playoff_tables(standings, group_rankings, owner_lookup)
    playoff_fixtures = build_playoff_fixture_table(standings, group_rankings, owner_lookup)
    upcoming_fixtures, _live_games_loaded = load_upcoming_fixtures(owner_lookup, refresh_key)
    upcoming_fixtures = (
        pd.concat([upcoming_fixtures, playoff_fixtures], ignore_index=True)
        .sort_values(["Date", "Time (Denmark)", "City"])
        .reset_index(drop=True)
    )
    return owner_league_table, group_tables, playoff_tables, upcoming_fixtures


render_styles()

owners_file_mtime = (DATA_DIR / "owners.csv").stat().st_mtime
owners = load_owners(owners_file_mtime)
owner_lookup = dict(zip(owners["team"], owners["player"]))
chat_owner_options = build_chat_owner_options(owners)
chat_messages = load_chat_messages()

st.markdown('<div class="title-wrap"><h1>TIA X World Cup 26</h1></div>', unsafe_allow_html=True)

left_column, right_column = st.columns([1.55, 1])

@st.fragment(run_every=f"{REFRESH_INTERVAL_SECONDS}s")
def render_league_fragment() -> None:
    owner_league_table, _group_tables, _playoff_tables, _upcoming_fixtures = load_live_dashboard_data(owners, owner_lookup)
    st.markdown('<div class="section-title">League Table</div>', unsafe_allow_html=True)
    render_html_table(owner_league_table, {"W", "D", "L", "GF", "Points"})


@st.fragment(run_every=f"{REFRESH_INTERVAL_SECONDS}s")
def render_schedule_fragment() -> None:
    _owner_league_table, group_tables, playoff_tables, upcoming_fixtures = load_live_dashboard_data(owners, owner_lookup)

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

with left_column:
    render_league_fragment()

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
    st.markdown('<div class="section-title">Team Chat</div>', unsafe_allow_html=True)
    chat_compose_column, chat_feed_column = st.columns([0.92, 1.28])

    with chat_compose_column:
        if CHAT_OWNER_STATE_KEY not in st.session_state and chat_owner_options:
            st.session_state[CHAT_OWNER_STATE_KEY] = chat_owner_options[0]

        with st.form("team_chat_form", clear_on_submit=True):
            st.markdown('<div class="chat-field-label">Select your name</div>', unsafe_allow_html=True)
            selected_chat_owner = st.selectbox(
                "Select your name",
                chat_owner_options,
                key=CHAT_OWNER_STATE_KEY,
                label_visibility="collapsed",
            )
            st.markdown('<div class="chat-field-label">Message</div>', unsafe_allow_html=True)
            chat_message = st.text_area("Message", height=130, max_chars=400, label_visibility="collapsed")
            chat_submitted = st.form_submit_button("Send", use_container_width=True)

        if chat_submitted:
            if chat_message.strip():
                append_chat_message(selected_chat_owner, chat_message)
                st.rerun()
            else:
                st.warning("Enter a message before sending.")

    with chat_feed_column:
        render_chat_feed(chat_messages)

render_schedule_fragment()

st.caption(
    f"Owner assignments are read directly from owners.csv. If `FOOTBALL_DATA_API_TOKEN` is set, the app uses football-data.org's `WC` competition endpoints first; otherwise it falls back to Wikipedia group pages and then TheSportsDB. Data refreshes every {REFRESH_INTERVAL_SECONDS} seconds. Playoff rows remain template placeholders until knockout pairings are known."
)
