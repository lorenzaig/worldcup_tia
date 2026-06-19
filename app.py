import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(
    page_title="TIA X World Cup 26",
    page_icon=":trophy:",
    layout="wide",
)

FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
DATA_DIR = Path(__file__).resolve().parent
CHAT_MESSAGES_PATH = DATA_DIR / "chat_messages.jsonl"
DENMARK_TZ = ZoneInfo("Europe/Copenhagen")
CHAT_OWNER_STATE_KEY = "chat_selected_owner"
REFRESH_INTERVAL_SECONDS = 15 * 60
REFRESH_NONCE_STATE_KEY = "live_refresh_nonce"
REFRESH_KEY_STATE_KEY = "live_refresh_key"
LAST_REFRESH_STATE_KEY = "live_last_refreshed_at"


def load_football_data_token() -> str:
    env_token = os.getenv("FOOTBALL_DATA_API_TOKEN", "").strip()
    if env_token:
        return env_token

    try:
        return str(st.secrets.get("FOOTBALL_DATA_API_TOKEN", "")).strip()
    except StreamlitSecretNotFoundError:
        return ""


FOOTBALL_DATA_TOKEN = load_football_data_token()

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
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
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


POINTS_RULES = [
    {"Rule": "Match win", "Points": "3"},
    {"Rule": "Match draw", "Points": "1"},
    {"Rule": "Match loss", "Points": "0"},
    {"Rule": "Goal scored", "Points": "1"},
    {"Rule": "Owner total", "Points": "Match points + goals scored across all owned teams"},
]

STANDINGS_COLUMNS = ["group", "team", "played", "won", "drawn", "lost", "gf", "gd", "points"]
OWNER_LEAGUE_COLUMNS = ["Owner", "Teams", "W", "D", "L", "GF", "Points"]
FIXTURE_COLUMNS = ["Date", "Time (Denmark)", "Team 1 (Owner)", "Team 2 (Owner)", "City", "Score"]
MATCH_COLUMNS = ["date", "time", "group", "home_team", "away_team", "city", "home_score", "away_score"]


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
            .refresh-note {
                color: #475569;
                font-size: 0.78rem;
                font-weight: 700;
                line-height: 1.25;
                margin-top: 0.35rem;
                margin-bottom: 0.35rem;
                text-align: right;
            }
            .refresh-note span {
                color: #0f172a;
                font-size: 0.9rem;
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
                .refresh-note {
                    text-align: left;
                    margin-top: 0;
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
    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return {}


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


def current_refresh_key(interval_seconds: int, manual_nonce: int = 0) -> str:
    now = datetime.now(DENMARK_TZ)
    refresh_bucket = int(now.timestamp() // interval_seconds)
    return f"{now.strftime('%Y-%m-%d')}-{refresh_bucket}-{manual_nonce}"


def get_live_refresh_key() -> str:
    manual_nonce = int(st.session_state.get(REFRESH_NONCE_STATE_KEY, 0))
    refresh_key = current_refresh_key(REFRESH_INTERVAL_SECONDS, manual_nonce)
    if st.session_state.get(REFRESH_KEY_STATE_KEY) != refresh_key:
        st.session_state[REFRESH_KEY_STATE_KEY] = refresh_key
        st.session_state[LAST_REFRESH_STATE_KEY] = datetime.now(DENMARK_TZ)
    return refresh_key


def request_manual_refresh() -> None:
    st.session_state[REFRESH_NONCE_STATE_KEY] = int(st.session_state.get(REFRESH_NONCE_STATE_KEY, 0)) + 1
    st.session_state.pop(REFRESH_KEY_STATE_KEY, None)
    st.session_state[LAST_REFRESH_STATE_KEY] = datetime.now(DENMARK_TZ)
    fetch_json.clear()


def format_last_refreshed_at() -> str:
    last_refreshed_at = st.session_state.get(LAST_REFRESH_STATE_KEY)
    if isinstance(last_refreshed_at, datetime):
        return last_refreshed_at.strftime("%Y-%m-%d %H:%M:%S %Z")
    return "Updating now"


def live_unavailable_message(data_type: str) -> str:
    if not FOOTBALL_DATA_TOKEN:
        return f"Set FOOTBALL_DATA_API_TOKEN as an environment variable or Streamlit secret to load live {data_type}."
    return f"Live {data_type} are unavailable from football-data.org right now."


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


def empty_standings() -> pd.DataFrame:
    return pd.DataFrame(columns=STANDINGS_COLUMNS)


def empty_matches() -> pd.DataFrame:
    return pd.DataFrame(columns=MATCH_COLUMNS)


def group_letter_from_api(group_name: Optional[str]) -> str:
    return (group_name or "").replace("GROUP_", "").strip()


def build_team_group_lookup(matches: pd.DataFrame) -> dict[str, str]:
    if matches.empty or "group" not in matches.columns:
        return {}

    group_lookup = {}
    for _, match in matches.iterrows():
        group_name = str(match.get("group") or "").strip()
        if not group_name:
            continue

        for team_column in ("home_team", "away_team"):
            team_name = canonical_team_name(match.get(team_column))
            if team_name and team_name != "-":
                group_lookup.setdefault(team_name, group_name)

    return group_lookup


def apply_group_lookup_to_standings(standings: pd.DataFrame, group_lookup: dict[str, str]) -> pd.DataFrame:
    if standings.empty:
        return standings

    live_standings = standings.copy()
    live_standings["group"] = live_standings["group"].fillna("").astype(str).str.strip()
    if group_lookup:
        missing_group = live_standings["group"] == ""
        live_standings.loc[missing_group, "group"] = (
            live_standings.loc[missing_group, "team"].map(group_lookup).fillna("")
        )

    return live_standings


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


def parse_football_data_standings_payload(payload: dict) -> pd.DataFrame:
    standings_rows = []

    for standings_block in payload.get("standings") or []:
        table_type = str(standings_block.get("type") or "").upper()
        if table_type and table_type != "TOTAL":
            continue

        group_letter = group_letter_from_api(standings_block.get("group"))
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

    standings = pd.DataFrame(standings_rows, columns=STANDINGS_COLUMNS)
    return standings.drop_duplicates(subset=["group", "team"], keep="first").reset_index(drop=True)


def parse_football_data_matches_payload(payload: dict) -> pd.DataFrame:
    match_rows = []

    for row in payload.get("matches") or []:
        home_team = canonical_team_name((row.get("homeTeam") or {}).get("name") or "-")
        away_team = canonical_team_name((row.get("awayTeam") or {}).get("name") or "-")

        utc_date = row.get("utcDate") or ""
        date_value = utc_date[:10] if len(utc_date) >= 10 else "-"
        time_value = utc_date[11:19] if len(utc_date) >= 19 else None
        denmark_date, denmark_time = parse_denmark_kickoff(date_value, time_value)

        score = row.get("score") or {}
        regular_time = score.get("regularTime") or {}
        full_time = score.get("fullTime") or {}
        home_score = regular_time.get("home")
        away_score = regular_time.get("away")
        if home_score is None or away_score is None:
            home_score = full_time.get("home")
            away_score = full_time.get("away")

        match_rows.append(
            {
                "date": denmark_date,
                "time": denmark_time,
                "group": group_letter_from_api(row.get("group")),
                "home_team": home_team,
                "away_team": away_team,
                "city": row.get("venue") or "-",
                "home_score": home_score,
                "away_score": away_score,
            }
        )

    return pd.DataFrame(match_rows, columns=MATCH_COLUMNS)


def load_football_data_matches(day_key: str) -> tuple[pd.DataFrame, bool]:
    if not FOOTBALL_DATA_TOKEN:
        return empty_matches(), False

    try:
        payload = fetch_json(
            f"{FOOTBALL_DATA_BASE_URL}/competitions/WC/matches?season=2026",
            day_key,
            auth_token=FOOTBALL_DATA_TOKEN,
            unfold_goals=True,
        )
        matches = parse_football_data_matches_payload(payload)
        if not matches.empty:
            return matches, True
    except (URLError, TimeoutError, OSError, ValueError):
        pass

    return empty_matches(), False

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
    matches, matches_loaded = load_football_data_matches(day_key)
    if matches_loaded and not matches.empty:
        fixtures = build_fixture_table_from_matches(matches, owner_lookup)
        if not fixtures.empty:
            return fixtures, True

    return empty_fixtures(), False

def load_standings(day_key: str) -> tuple[pd.DataFrame, bool]:
    return load_football_data_standings(day_key)

def build_owner_league_table(owners: pd.DataFrame, standings: pd.DataFrame) -> pd.DataFrame:
    merged = owners.merge(standings[["team", "won", "drawn", "lost", "gf", "points"]], on="team", how="inner")
    if merged.empty:
        return pd.DataFrame(columns=OWNER_LEAGUE_COLUMNS)

    merged["won"] = merged["won"].astype(int)
    merged["drawn"] = merged["drawn"].astype(int)
    merged["lost"] = merged["lost"].astype(int)
    merged["points"] = merged["points"].astype(int)
    merged["gf"] = merged["gf"].astype(int)
    merged["owner_points"] = merged["points"] + merged["gf"]

    league_table = (
        merged.groupby("player", as_index=False)
        .agg(
            Teams=("team", lambda teams: " ".join(flag_icon(team) for team in sorted(pd.unique(teams)))),
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
    if standings.empty:
        return {}

    live_standings = standings.copy()
    live_standings["group"] = live_standings["group"].fillna("").astype(str).str.strip()
    live_standings = live_standings.drop_duplicates(subset=["group", "team"], keep="first")
    if (live_standings["group"] == "").all():
        return {}

    live_standings.loc[live_standings["group"] == "", "group"] = "Ungrouped"
    tables = {}

    for group_name, group_rows in live_standings.groupby("group", sort=True):
        table_rows = []
        for _, team_stats in group_rows.iterrows():
            team_name = canonical_team_name(team_stats["team"])
            table_rows.append(
                {
                    "Flag": flag_icon(team_name),
                    "Team": team_name,
                    "Owner": owner_lookup.get(team_name, "Unassigned"),
                    "P": int(team_stats["played"]),
                    "W": int(team_stats["won"]),
                    "D": int(team_stats["drawn"]),
                    "L": int(team_stats["lost"]),
                    "GD": int(team_stats["gd"]),
                    "Pts": int(team_stats["points"]),
                }
            )

        group_table = pd.DataFrame(table_rows).sort_values(
            ["Pts", "GD", "W", "Team"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        tables[f"Group {group_name}"] = group_table

    return tables


def empty_fixtures() -> pd.DataFrame:
    return pd.DataFrame(columns=FIXTURE_COLUMNS)


def load_upcoming_fixtures(owner_lookup: dict[str, str], day_key: str) -> tuple[pd.DataFrame, bool]:
    football_data_fixtures, football_data_loaded = load_football_data_fixtures(owner_lookup, day_key)
    if football_data_loaded and not football_data_fixtures.empty:
        return football_data_fixtures.sort_values(["Date", "Time (Denmark)", "City"]).reset_index(drop=True), True

    return empty_fixtures(), False


def load_live_dashboard_data(
    owners: pd.DataFrame,
    owner_lookup: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame, bool, bool]:
    refresh_key = get_live_refresh_key()
    standings, standings_loaded = load_standings(refresh_key)
    matches, matches_loaded = load_football_data_matches(refresh_key)
    group_lookup = build_team_group_lookup(matches)

    if standings_loaded:
        standings = apply_group_lookup_to_standings(standings, group_lookup)
        owner_league_table = build_owner_league_table(owners, standings)
        group_tables = build_group_tables(standings, owner_lookup)
    else:
        owner_league_table = pd.DataFrame(columns=OWNER_LEAGUE_COLUMNS)
        group_tables = {}

    if matches_loaded and not matches.empty:
        upcoming_fixtures = build_fixture_table_from_matches(matches, owner_lookup)
        fixtures_loaded = not upcoming_fixtures.empty
    else:
        upcoming_fixtures = empty_fixtures()
        fixtures_loaded = False

    if not upcoming_fixtures.empty:
        upcoming_fixtures = upcoming_fixtures.sort_values(["Date", "Time (Denmark)", "City"]).reset_index(drop=True)

    return owner_league_table, group_tables, upcoming_fixtures, standings_loaded, fixtures_loaded


@st.fragment(run_every=f"{REFRESH_INTERVAL_SECONDS}s")
def render_refresh_controls() -> None:
    get_live_refresh_key()
    st.markdown(
        f'<div class="refresh-note">Last updated<br><span>{format_last_refreshed_at()}</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("Update now", key="manual_live_refresh", use_container_width=True):
        request_manual_refresh()
        st.rerun()


render_styles()

owners_file_mtime = (DATA_DIR / "owners.csv").stat().st_mtime
owners = load_owners(owners_file_mtime)
owner_lookup = dict(zip(owners["team"], owners["player"]))
chat_owner_options = build_chat_owner_options(owners)
chat_messages = load_chat_messages()

header_title_column, header_refresh_column = st.columns([1.7, 0.7])
with header_title_column:
    st.markdown('<div class="title-wrap"><h1>TIA X World Cup 26</h1></div>', unsafe_allow_html=True)
with header_refresh_column:
    render_refresh_controls()

left_column, right_column = st.columns([1.55, 1])

@st.fragment(run_every=f"{REFRESH_INTERVAL_SECONDS}s")
def render_league_fragment() -> None:
    (
        owner_league_table,
        _group_tables,
        _upcoming_fixtures,
        standings_loaded,
        _fixtures_loaded,
    ) = load_live_dashboard_data(owners, owner_lookup)
    st.markdown('<div class="section-title">League Table</div>', unsafe_allow_html=True)
    if standings_loaded:
        render_html_table(owner_league_table, {"W", "D", "L", "GF", "Points"})
    else:
        st.info(live_unavailable_message("standings"))


@st.fragment(run_every=f"{REFRESH_INTERVAL_SECONDS}s")
def render_schedule_fragment() -> None:
    (
        _owner_league_table,
        group_tables,
        upcoming_fixtures,
        standings_loaded,
        fixtures_loaded,
    ) = load_live_dashboard_data(owners, owner_lookup)

    st.markdown('<div class="section-title">Fixtures</div>', unsafe_allow_html=True)
    fixture_dates = sorted(upcoming_fixtures["Date"].dropna().unique().tolist())

    if fixtures_loaded and fixture_dates:
        max_index = len(fixture_dates) - 1
        today_denmark = datetime.now(DENMARK_TZ).strftime("%Y-%m-%d")
        default_index = next(
            (index for index, date_value in enumerate(fixture_dates) if date_value >= today_denmark),
            max_index,
        )
        selected_fixture_date = st.session_state.get("fixture_selected_date")
        if selected_fixture_date in fixture_dates:
            st.session_state.fixture_date_index = fixture_dates.index(selected_fixture_date)
        elif "fixture_selected_date" not in st.session_state:
            st.session_state.fixture_date_index = default_index
        else:
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
        st.session_state.fixture_selected_date = selected_fixture_date
        with date_column:
            st.markdown(
                f"<div class='fixture-date-label'>{selected_fixture_date}</div>",
                unsafe_allow_html=True,
            )

        daily_games = upcoming_fixtures[upcoming_fixtures["Date"] == selected_fixture_date].reset_index(drop=True)
        render_html_table(daily_games, set())
    else:
        st.info(live_unavailable_message("fixtures"))

    st.markdown('<div class="section-title">Group Tables</div>', unsafe_allow_html=True)
    group_names = list(group_tables.keys())

    if standings_loaded and group_names:
        for start_index in range(0, len(group_names), 3):
            row_columns = st.columns(3)
            for column, group_name in zip(row_columns, group_names[start_index:start_index + 3]):
                with column:
                    st.markdown(f'<div class="group-card"><h3>{group_name}</h3>', unsafe_allow_html=True)
                    render_html_table(group_tables[group_name], {"P", "W", "D", "L", "GD", "Pts"}, table_class="")
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info(live_unavailable_message("group standings"))


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
    f"Owner assignments are read from owners.csv, but teams and groups are shown only when returned by football-data.org's live `WC` endpoints. Data refreshes every {REFRESH_INTERVAL_SECONDS // 60} minutes or when Update now is clicked."
)
