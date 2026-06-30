"""
Delaware Election Modeling Web-App
Data: Delaware Department of Elections, 2018–2024
Source: https://elections.delaware.gov
"""

import re
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Delaware Election Modeler",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PARTY_COLORS = {
    "Democratic":  "#1565C0",
    "Republican":  "#C62828",
    "Green":       "#2E7D32",
    "Libertarian": "#F57F17",
    "Other":       "#546E7A",
}

# ─────────────────────────────────────────────────────────────────────────────
# WFP / DSA CANDIDATE DATA  (curated — these candidates run as Democrats)
# Sources: workingfamilies.org, deworkingfamilies.org, Delaware DSA Instagram
# ─────────────────────────────────────────────────────────────────────────────

WFP_CANDIDATES = [
    # ── 2026 (primary Sept 15 2026) ──────────────────────────────────────────
    {"name": "Adriana Bohm",       "office": "State Senator",        "district": "District 1",  "year": 2026, "status": "primary", "csv_fragment": "ADRIANA BOHM",       "orgs": ["WFP"],       "county": "New Castle", "notes": "Targeting pro-SB21 incumbent"},
    {"name": "Shay Frisby",        "office": "State Senator",        "district": "District 5",  "year": 2026, "status": "primary", "csv_fragment": "SHAY FRISBY",        "orgs": ["WFP","DSA"], "county": "New Castle", "notes": "AFSCME Local 81 organizer; Medicaid option champion"},
    {"name": "Shané Darby",        "office": "State Representative", "district": "District 1",  "year": 2026, "status": "primary", "csv_fragment": "SHANE DARBY",        "orgs": ["WFP"],       "county": "New Castle", "notes": "Wilmington District 2 community leader"},
    {"name": "Rae Krantz",         "office": "State Representative", "district": "District 6",  "year": 2026, "status": "primary", "csv_fragment": "RAE KRANTZ",         "orgs": ["WFP"],       "county": "New Castle", "notes": "Challenging SB21 supporter"},
    {"name": "Pamela Salaam",      "office": "State Representative", "district": "District 16", "year": 2026, "status": "primary", "csv_fragment": "PAMELA SALAAM",      "orgs": ["WFP"],       "county": "New Castle", "notes": "Progressive challenger"},
    {"name": "Will Imbrie-Moore",  "office": "State Representative", "district": "District 19", "year": 2026, "status": "primary", "csv_fragment": "WILL IMBRIE",        "orgs": ["WFP"],       "county": "New Castle", "notes": "Open seat"},
    {"name": "Coby Owens",         "office": "Wilmington City Council", "district": "District 1", "year": 2026, "status": "primary", "csv_fragment": "COBY OWENS",       "orgs": ["WFP"],       "county": "New Castle", "notes": "Incumbent; seeking reelection"},
    {"name": "Christian Willauer", "office": "Wilmington City Council", "district": "District 5", "year": 2026, "status": "primary", "csv_fragment": "CHRISTIAN WILLAUER","orgs": ["WFP"],      "county": "New Castle", "notes": "Incumbent; seeking reelection"},
    {"name": "Kevin Caneco",       "office": "NCC Council",          "district": "District 12", "year": 2026, "status": "primary", "csv_fragment": "KEVIN CANECO",       "orgs": ["WFP"],       "county": "New Castle", "notes": "Incumbent; seeking reelection"},
    # ── 2024 ──────────────────────────────────────────────────────────────────
    {"name": "Kamela T. Smith",    "office": "State Representative", "district": "District 15", "year": 2024, "status": "won",     "csv_fragment": "KAMELA",             "orgs": ["WFP"],       "county": "New Castle", "notes": "Defeated incumbent Speaker of the House"},
    {"name": "Frank Burns",        "office": "State Representative", "district": "District 21", "year": 2024, "status": "won",     "csv_fragment": "FRANK BURNS",        "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    {"name": "Eric Morrison",      "office": "State Representative", "district": "District 27", "year": 2024, "status": "won",     "csv_fragment": "ERIC MORRISON",      "orgs": ["WFP"],       "county": "New Castle", "notes": "WFP winner since 2020"},
    {"name": "Kerri Evelyn Harris","office": "State Representative", "district": "District 32", "year": 2024, "status": "won",     "csv_fragment": "KERRI EVELYN HARRIS","orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    {"name": "Madinah Wilson-Anton","office": "State Representative","district": "District 26", "year": 2024, "status": "won",     "csv_fragment": "MADINAH WILSON",     "orgs": ["WFP"],       "county": "New Castle", "notes": "WFP winner since 2020"},
    {"name": "Cyndie Romer",       "office": "State Representative", "district": "District 25", "year": 2024, "status": "won",     "csv_fragment": "CYNDIE ROMER",       "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    {"name": "Deshanna Neal",      "office": "State Representative", "district": "District 13", "year": 2024, "status": "won",     "csv_fragment": "DESHANNA NEAL",      "orgs": ["WFP"],       "county": "New Castle", "notes": "Defeated House Majority Whip (2022)"},
    {"name": "Sophie Phillips",    "office": "State Representative", "district": "District 18", "year": 2024, "status": "won",     "csv_fragment": "SOPHIE PHILLIPS",    "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    {"name": "Larry D. Lambert Jr.","office": "State Representative","district": "District 7",  "year": 2024, "status": "won",     "csv_fragment": "LARRY LAMBERT",      "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    {"name": "Kevin Caneco",       "office": "NCC Council",          "district": "District 12", "year": 2024, "status": "won",     "csv_fragment": "KEVIN CANECO",       "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    # ── 2022 ──────────────────────────────────────────────────────────────────
    {"name": "Marie Pinkney",      "office": "State Senator",        "district": "District 13", "year": 2022, "status": "won",     "csv_fragment": "MARIE PINKNEY",      "orgs": ["WFP"],       "county": "New Castle", "notes": ""},
    # ── 2020 ──────────────────────────────────────────────────────────────────
    {"name": "Sherae'a 'Rae' Moore","office": "State Representative","district": "District 8",  "year": 2020, "status": "won",     "csv_fragment": "RAE MOORE",          "orgs": ["WFP"],       "county": "Kent",       "notes": ""},
]

DSA_CANDIDATES = [
    {"name": "Shay Frisby",  "office": "State Senator",        "district": "District 5",  "year": 2026, "status": "primary", "csv_fragment": "SHAY FRISBY",  "orgs": ["DSA","WFP"], "county": "New Castle", "notes": "AFSCME Local 81 organizer. Fights for DE Public Medicaid Option. Primary Sept 15, 2026."},
]

DSA_PLATFORM = [
    "Public Delaware Medicaid Option — healthcare for all Delawareans",
    "Expand union rights and collective bargaining",
    "Affordable housing — end displacement in Wilmington",
    "Tax the wealthy; close corporate loopholes",
    "Free school meals for all children statewide",
    "Community control over policing",
]

WFP_PLATFORM = [
    "Affordable housing & preventing displacement",
    "Free school meals for all children",
    "Tax the wealthy — reverse SB21 corporate giveaways",
    "Earned sick time & workers' rights",
    "Community Workforce Agreements on state projects",
    "Clean energy & environmental justice",
]

WFP_COLOR  = "#8B1A1A"   # deep WFP red
DSA_COLOR  = "#C41E3A"   # DSA rose red
WFP_LIGHT  = "#FFEBEE"
DSA_LIGHT  = "#FFF0F0"

# Keywords used to identify "major" statewide/federal races
MAJOR_OFFICE_KEYWORDS = [
    "UNITED STATES SENATOR", "U.S. SENATOR",
    "REPRESENTATIVE IN CONGRESS", "U.S. REPRESENTATIVE",
    "PRESIDENT",
    "GOVERNOR",
    "LIEUTENANT GOVERNOR",
    "ATTORNEY GENERAL",
    "STATE TREASURER",
    "AUDITOR OF ACCOUNTS",
    "INSURANCE COMMISSIONER",
    "SECRETARY OF STATE",
]

DATA_DIR = Path(__file__).parent / "data"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & PARSING
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_party(party: str) -> str:
    p = str(party).upper().strip()
    if "DEMOCRAT"  in p: return "Democratic"
    if "REPUBLIC"  in p: return "Republican"
    if "GREEN"     in p: return "Green"
    if "LIBERTARI" in p: return "Libertarian"
    return "Other"


def _election_type_from_name(name: str) -> str:
    n = str(name).upper()
    if "PRESIDENTIAL PRIMARY" in n:                return "presidential_primary"
    if "PRIMARY" in n:                             return "primary"
    if "GENERAL" in n:                             return "general"
    if "SCHOOL" in n or "REFERENDUM" in n:         return "school_special"
    return "special"


def _parse_2018_txt(filepath: Path, election_date: str, election_name: str) -> list[dict]:
    """
    Parse Delaware's semicolon-delimited 2018 election TXT files.

    Format after the 'Office/Party/Candidate' header line:
      UNITED STATES SENATOR ; 436 of 436 Districts Reported ; ;
           DEMOCRATIC PARTY ; ; ; ; ;
               THOMAS R CARPER ; 205830 ; 11555 ; 217385 ; 59.95 % ;
    """
    records: list[dict] = []
    current_office: Optional[str] = None
    current_party:  Optional[str] = None
    in_data = False

    try:
        with open(filepath, "r", encoding="latin-1") as fh:
            for raw_line in fh:
                line = raw_line.rstrip("\r\n")

                # Wait until we hit the column-header sentinel
                if "Office/Party/Candidate" in line:
                    in_data = True
                    continue
                if not in_data or not line.strip():
                    continue

                leading = len(line) - len(line.lstrip(" "))
                parts   = [p.strip() for p in line.split(";")]
                label   = parts[0].strip()

                if not label:
                    continue

                # ── Office header (no indentation) ────────────────────────
                if leading == 0:
                    current_office = label
                    current_party  = None

                # ── Party line (~5 spaces, contains "PARTY") ─────────────
                elif leading <= 6 and "PARTY" in label.upper():
                    current_party = label

                # ── Candidate line (~9 spaces) ────────────────────────────
                elif leading >= 7 and current_office and current_party:
                    try:
                        machine  = int(parts[1].replace(",", "").replace(" ", "")) if len(parts) > 1 and parts[1].strip() else 0
                        absentee = int(parts[2].replace(",", "").replace(" ", "")) if len(parts) > 2 and parts[2].strip() else 0
                        total    = int(parts[3].replace(",", "").replace(" ", "")) if len(parts) > 3 and parts[3].strip() else 0
                        pct_raw  = parts[4].replace("%", "").strip()               if len(parts) > 4 else "0"
                        pct      = float(pct_raw) if pct_raw else 0.0

                        if total > 0:
                            records.append({
                                "office":               current_office,
                                "candidatename":        label,
                                "partyname":            current_party,
                                "electiondate":         election_date,
                                "machinevotessum":      machine,
                                "absenteevotessum":     absentee,
                                "earlyvotessum":        0,
                                "totalvotessum":        total,
                                "totalvotespercentage": pct,
                                "xmlreporttime":        None,
                                "electionname":         election_name,
                            })
                    except (ValueError, IndexError):
                        pass

    except FileNotFoundError:
        st.warning(f"2018 data file not found: {filepath.name}")

    return records


@st.cache_data(show_spinner="Loading election data…")
def load_data() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    # ── 1. Modern results (2020–2024) from Delaware Open Data Portal ──
    portal_path = DATA_DIR / "elections_all.csv"
    if portal_path.exists():
        portal_df = pd.read_csv(portal_path)
        portal_df.columns = [c.lower() for c in portal_df.columns]
        frames.append(portal_df)

    # ── 2. 2018 General Election (TXT) ───────────────────────────────
    gen18 = _parse_2018_txt(
        DATA_DIR / "elections_2018_general_raw.txt",
        "2018-11-06",
        "2018 General Election",
    )
    if gen18:
        frames.append(pd.DataFrame(gen18))

    # ── 3. 2018 Primary Election (TXT) ───────────────────────────────
    pri18 = _parse_2018_txt(
        DATA_DIR / "elections_2018_primary_raw.txt",
        "2018-09-06",
        "2018 State Primary Election",
    )
    if pri18:
        frames.append(pd.DataFrame(pri18))

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # ── Derived columns ───────────────────────────────────────────────
    df["electiondate"]      = pd.to_datetime(df["electiondate"], errors="coerce")
    df["year"]              = df["electiondate"].dt.year.astype("Int64")
    df["party"]             = df["partyname"].fillna("").apply(_normalize_party)
    df["election_type"]     = df["electionname"].fillna("").apply(_election_type_from_name)
    df["office_upper"]      = df["office"].str.upper().str.strip()

    # Numeric coercion
    for col in ["machinevotessum", "absenteevotessum", "earlyvotessum",
                "totalvotessum",  "totalvotespercentage"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Winner flag: highest total per (election × office)
    idx_max     = df.groupby(["electionname", "office"])["totalvotessum"].idxmax()
    df["winner"] = False
    df.loc[idx_max, "winner"] = True

    # Standardise text casing
    df["candidatename"] = df["candidatename"].str.title().str.strip()
    df["office"]        = df["office"].str.title().str.strip()
    df["office_upper"]  = df["office"].str.upper().str.strip()

    return df


def is_major_office(office_upper: str) -> bool:
    return any(kw in office_upper for kw in MAJOR_OFFICE_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def bar_race(race_df: pd.DataFrame, title: str) -> go.Figure:
    """Horizontal bar chart for a single race."""
    race_df = race_df.sort_values("totalvotessum", ascending=True)
    colors  = [PARTY_COLORS.get(p, "#546E7A") for p in race_df["party"]]

    fig = go.Figure(go.Bar(
        x=race_df["totalvotessum"],
        y=race_df["candidatename"],
        orientation="h",
        marker_color=colors,
        text=[f"{int(v):,}  ({p:.1f}%)"
              for v, p in zip(race_df["totalvotessum"], race_df["totalvotespercentage"])],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Votes: %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Total Votes",
        yaxis_title="",
        height=max(220, 70 * len(race_df)),
        margin=dict(l=0, r=100, t=40, b=0),
        plot_bgcolor="white",
        font=dict(size=12),
        xaxis=dict(gridcolor="#EEEEEE"),
    )
    return fig


def line_party_trends(df: pd.DataFrame) -> go.Figure:
    """Votes by party over general elections."""
    subset = df[
        (df["election_type"] == "general") &
        (df["party"].isin(["Democratic", "Republican"]))
    ]
    agg = (
        subset
        .groupby(["year", "party"])["totalvotessum"]
        .sum()
        .reset_index()
        .sort_values("year")
    )
    agg["year"] = agg["year"].astype(int)

    fig = px.line(
        agg, x="year", y="totalvotessum", color="party",
        color_discrete_map=PARTY_COLORS,
        markers=True,
        labels={"totalvotessum": "Total Votes", "year": "Year", "party": "Party"},
    )
    fig.update_layout(
        plot_bgcolor="white",
        height=340,
        xaxis=dict(tickmode="linear", dtick=2, gridcolor="#EEEEEE"),
        yaxis=dict(gridcolor="#EEEEEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=10),
    )
    return fig


def stacked_margin_chart(df: pd.DataFrame) -> go.Figure:
    """D vs R margin across general elections for major offices."""
    subset = df[
        (df["election_type"] == "general") &
        (df["party"].isin(["Democratic", "Republican"])) &
        (df["office_upper"].apply(is_major_office))
    ].copy()

    pivot = (
        subset.groupby(["year", "office", "party"])["totalvotespercentage"]
        .max()
        .unstack("party")
        .reset_index()
        .dropna(subset=["Democratic", "Republican"])
    )
    pivot["D_margin"] = pivot["Democratic"] - pivot["Republican"]
    pivot["year"] = pivot["year"].astype(int)

    fig = px.bar(
        pivot.sort_values(["year", "office"]),
        x="office", y="D_margin", color="year",
        barmode="group",
        labels={"D_margin": "Dem − Rep margin (pts)", "office": "Office", "year": "Year"},
        color_continuous_scale="Blues",
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        plot_bgcolor="white",
        height=400,
        xaxis_tickangle=-30,
        margin=dict(t=10),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def page_dashboard(df: pd.DataFrame) -> None:
    st.title("🗳️ Delaware Election Dashboard")
    st.caption("Historical results · 2018–2024 · Source: [Delaware Dept. of Elections](https://elections.delaware.gov)")

    # ── Top metrics ──────────────────────────────────────────────────────────
    years  = sorted(df["year"].dropna().astype(int).unique().tolist())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Elections Covered",   df["electionname"].nunique())
    c2.metric("Years",               f"{years[0]}–{years[-1]}")
    c3.metric("Candidate Records",   f"{len(df):,}")
    c4.metric("Races With Results",  df["office"].nunique())

    st.markdown("---")

    # ── Election browser ─────────────────────────────────────────────────────
    st.subheader("Browse by Election")
    row1, row2 = st.columns([1, 3])

    with row1:
        year_opts = ["All"] + [str(y) for y in sorted(years, reverse=True)]
        sel_year  = st.selectbox("Year", year_opts, key="db_year")
        type_opts = {
            "All": "All",
            "General": "general",
            "Primary": "primary",
            "Presidential Primary": "presidential_primary",
            "School / Special": "school_special",
            "Special": "special",
        }
        sel_type_label = st.selectbox("Type", list(type_opts.keys()), key="db_type")
        sel_type = type_opts[sel_type_label]

    view = df.copy()
    if sel_year != "All": view = view[view["year"] == int(sel_year)]
    if sel_type != "All": view = view[view["election_type"] == sel_type]

    election_list = sorted(view["electionname"].dropna().unique())

    with row2:
        if election_list:
            sel_election = st.selectbox("Election", election_list, key="db_election")
        else:
            st.info("No elections match the selected filters.")
            sel_election = None

    if sel_election:
        el_df  = view[view["electionname"] == sel_election]
        major  = el_df[el_df["office_upper"].apply(is_major_office)]
        local  = el_df[~el_df["office_upper"].apply(is_major_office)]

        # Total votes cast in this election
        total_cast = el_df.groupby("office")["totalvotessum"].max().sum()
        st.caption(f"**Total votes cast (approx):** {int(total_cast):,}")

        if not major.empty:
            st.subheader("Major Races")
            for office in major["office"].unique():
                race    = major[major["office"] == office].sort_values("totalvotessum", ascending=False)
                winner  = race[race["winner"]]["candidatename"].values
                wlabel  = f" — 🏆 {winner[0]}" if len(winner) else ""
                with st.expander(f"**{office}**{wlabel}", expanded=True):
                    cola, colb = st.columns([2, 1])
                    with cola:
                        st.plotly_chart(bar_race(race, office), use_container_width=True)
                    with colb:
                        st.dataframe(
                            race[["candidatename", "party", "totalvotessum", "totalvotespercentage"]]
                            .rename(columns={
                                "candidatename":        "Candidate",
                                "party":                "Party",
                                "totalvotessum":        "Total Votes",
                                "totalvotespercentage": "Vote %",
                            }),
                            hide_index=True,
                            use_container_width=True,
                        )

        if not local.empty:
            with st.expander(f"All Other Races ({local['office'].nunique()})"):
                st.dataframe(
                    local[["office", "candidatename", "party", "totalvotessum", "totalvotespercentage", "winner"]]
                    .sort_values(["office", "totalvotessum"], ascending=[True, False])
                    .rename(columns={
                        "office": "Office", "candidatename": "Candidate",
                        "party":  "Party",  "totalvotessum": "Votes",
                        "totalvotespercentage": "Vote %", "winner": "Winner",
                    }),
                    hide_index=True,
                    use_container_width=True,
                    height=400,
                )

    st.markdown("---")

    # ── Trends ───────────────────────────────────────────────────────────────
    st.subheader("Statewide Trends — General Elections")
    tab_a, tab_b = st.tabs(["Party Vote Totals", "D vs R Margin by Office"])
    with tab_a:
        st.plotly_chart(line_party_trends(df), use_container_width=True)
    with tab_b:
        st.plotly_chart(stacked_margin_chart(df), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SIMULATOR
# ─────────────────────────────────────────────────────────────────────────────

def page_simulator(df: pd.DataFrame) -> None:
    st.title("🎯 Election Simulator")
    st.markdown("Adjust turnout and partisan swing to model hypothetical outcomes.")

    # ── Controls in sidebar ──────────────────────────────────────────────────
    st.sidebar.markdown("### Base Election")

    general_elections = sorted(
        df[df["election_type"] == "general"]["electionname"].dropna().unique(),
        reverse=True,
    )
    base_election = st.sidebar.selectbox("Base Election", general_elections, key="sim_el")

    offices = sorted(df[df["electionname"] == base_election]["office"].unique())
    sel_office = st.sidebar.selectbox("Office", offices, key="sim_off")

    base_df = df[(df["electionname"] == base_election) & (df["office"] == sel_office)].copy()

    if base_df.empty:
        st.warning("No data found for this race.")
        return

    st.sidebar.markdown("### Scenario Levers")
    turnout_pct = st.sidebar.slider(
        "Turnout Change (%)", -40, 100, 0, 5,
        help="+10 = 10 % more total votes cast",
    )
    dem_swing = st.sidebar.slider(
        "Dem ↔ Rep Swing (pts)", -20, 20, 0, 1,
        help="Positive shifts votes toward Democrats; negative toward Republicans",
    )
    third_boost = st.sidebar.slider(
        "Third-Party Boost (%)", 0, 30, 0, 1,
        help="Increases third-party vote share",
    )
    run = st.sidebar.button("▶ Run Simulation", type="primary")

    # ── Show original ────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Actual Results")
        st.plotly_chart(bar_race(base_df, f"{sel_office} · {base_election}"), use_container_width=True)

    # ── Simulation ───────────────────────────────────────────────────────────
    if run:
        sim = base_df.copy()

        # Apply overall turnout adjustment
        sim["totalvotessum"] = sim["totalvotessum"] * (1 + turnout_pct / 100)

        # Partisan swing: redistribute votes between Dem and Rep
        two_party_total = sim.loc[sim["party"].isin(["Democratic", "Republican"]), "totalvotessum"].sum()
        swing_votes = two_party_total * abs(dem_swing) / 100

        n_dem = max(1, (sim["party"] == "Democratic").sum())
        n_rep = max(1, (sim["party"] == "Republican").sum())

        if dem_swing > 0:
            sim.loc[sim["party"] == "Democratic", "totalvotessum"] += swing_votes / n_dem
            sim.loc[sim["party"] == "Republican", "totalvotessum"] -= swing_votes / n_rep
        elif dem_swing < 0:
            sim.loc[sim["party"] == "Republican", "totalvotessum"] += swing_votes / n_rep
            sim.loc[sim["party"] == "Democratic", "totalvotessum"] -= swing_votes / n_dem

        # Third-party boost
        if third_boost > 0:
            third_mask = ~sim["party"].isin(["Democratic", "Republican"])
            sim.loc[third_mask, "totalvotessum"] *= (1 + third_boost / 100)

        sim["totalvotessum"] = sim["totalvotessum"].clip(lower=0).round(0)
        race_total = sim["totalvotessum"].sum()
        sim["totalvotespercentage"] = (
            (sim["totalvotessum"] / race_total * 100).round(2) if race_total else 0
        )
        sim["winner"] = sim["totalvotessum"] == sim["totalvotessum"].max()

        with col_b:
            st.subheader("Simulated Results")
            st.plotly_chart(bar_race(sim, "Simulated"), use_container_width=True)

        # ── Comparison table ─────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Head-to-Head Comparison")

        comp = (
            base_df[["candidatename", "party", "totalvotessum", "totalvotespercentage"]]
            .rename(columns={"totalvotessum": "Actual Votes", "totalvotespercentage": "Actual %"})
        )
        sim_tbl = (
            sim[["candidatename", "totalvotessum", "totalvotespercentage", "winner"]]
            .rename(columns={"totalvotessum": "Sim Votes", "totalvotespercentage": "Sim %"})
        )
        merged = comp.merge(sim_tbl, on="candidatename", how="left")
        merged["Δ Votes"] = (merged["Sim Votes"] - merged["Actual Votes"]).round(0).astype(int)
        merged["Δ %"]     = (merged["Sim %"] - merged["Actual %"]).round(2)
        merged["🏆"]       = merged["winner"].apply(lambda x: "🏆" if x else "")
        merged = merged.drop(columns=["winner"]).rename(columns={"candidatename": "Candidate", "party": "Party"})

        st.dataframe(
            merged.sort_values("Sim Votes", ascending=False),
            hide_index=True,
            use_container_width=True,
        )

        # Scenario summary
        orig_winner = base_df[base_df["winner"]]["candidatename"].values
        sim_winner  = sim[sim["winner"]]["candidatename"].values
        if len(orig_winner) and len(sim_winner):
            if orig_winner[0] == sim_winner[0]:
                st.success(f"**Same winner:** {sim_winner[0]} holds on under this scenario.")
            else:
                st.error(f"**Flip!** {sim_winner[0]} defeats {orig_winner[0]} under this scenario.")
    else:
        with col_b:
            st.info("Adjust the levers in the sidebar and click **▶ Run Simulation**.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DATA EXPLORER
# ─────────────────────────────────────────────────────────────────────────────

def page_explorer(df: pd.DataFrame) -> None:
    st.title("📋 Data Explorer")
    st.markdown("Browse, filter, and download the full underlying dataset.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        years     = ["All"] + [str(y) for y in sorted(df["year"].dropna().astype(int).unique(), reverse=True)]
        f_year    = st.selectbox("Year", years, key="ex_yr")
    with c2:
        type_map  = {"All": "All", "General": "general", "Primary": "primary",
                     "Presidential Primary": "presidential_primary",
                     "School / Special": "school_special", "Special": "special"}
        f_type_lbl = st.selectbox("Type", list(type_map.keys()), key="ex_tp")
        f_type    = type_map[f_type_lbl]
    with c3:
        parties   = ["All"] + sorted(df["party"].unique().tolist())
        f_party   = st.selectbox("Party", parties, key="ex_pa")
    with c4:
        f_office  = st.text_input("Search office / candidate", key="ex_oc")

    view = df.copy()
    if f_year  != "All": view = view[view["year"] == int(f_year)]
    if f_type  != "All": view = view[view["election_type"] == f_type]
    if f_party != "All": view = view[view["party"] == f_party]
    if f_office:
        mask = (
            view["office"].str.contains(f_office, case=False, na=False) |
            view["candidatename"].str.contains(f_office, case=False, na=False)
        )
        view = view[mask]

    st.caption(f"**{len(view):,}** records matching current filters")

    display = (
        view[[
            "year", "election_type", "electionname", "office",
            "candidatename", "party",
            "machinevotessum", "absenteevotessum", "earlyvotessum",
            "totalvotessum", "totalvotespercentage", "winner",
        ]]
        .sort_values(["year", "office", "totalvotessum"], ascending=[False, True, False])
        .rename(columns={
            "year":                 "Year",
            "election_type":        "Type",
            "electionname":         "Election",
            "office":               "Office",
            "candidatename":        "Candidate",
            "party":                "Party",
            "machinevotessum":      "Machine",
            "absenteevotessum":     "Absentee",
            "earlyvotessum":        "Early",
            "totalvotessum":        "Total",
            "totalvotespercentage": "Vote %",
            "winner":               "Winner",
        })
    )

    st.dataframe(display, use_container_width=True, height=520, hide_index=True)

    csv_bytes = display.to_csv(index=False).encode()
    fname = f"delaware_elections_{f_year}_{f_type_lbl.lower().replace(' ','_')}.csv"
    st.download_button("⬇️ Download CSV", data=csv_bytes, file_name=fname, mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: pull CSV rows for a candidate by name fragment
# ─────────────────────────────────────────────────────────────────────────────

def get_candidate_history(df: pd.DataFrame, fragment: str) -> pd.DataFrame:
    mask = df["candidatename"].str.upper().str.contains(fragment.upper(), na=False)
    return df[mask].sort_values("electiondate")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Working Families Party
# ─────────────────────────────────────────────────────────────────────────────

def page_wfp(df: pd.DataFrame) -> None:
    st.markdown(
        f"<h1 style='color:{WFP_COLOR};'>🌹 Working Families Party in Delaware</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "The Delaware WFP elects progressive champions who fight for affordable housing, "
        "workers' rights, and taxing the wealthy. They endorse candidates of any registered "
        "party who align with WFP values — most run in Democratic primaries."
    )

    # ── Metrics row ────────────────────────────────────────────────────────
    historical = [c for c in WFP_CANDIDATES if c["year"] < 2026]
    won   = sum(1 for c in historical if c["status"] == "won")
    total = len(historical)
    upcoming = [c for c in WFP_CANDIDATES if c["year"] == 2026]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("2026 Active Races", len(upcoming))
    col2.metric("Historical Wins (2020–24)", won)
    col3.metric("Historical Races", total)
    col4.metric("Win Rate", f"{won/total*100:.0f}%" if total else "—")

    st.markdown("---")

    # ── 2026 Candidates ────────────────────────────────────────────────────
    st.markdown(f"### 🗓️ 2026 Primary Races  <span style='color:gray;font-size:0.85em;'>Primary: September 15, 2026</span>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, c in enumerate(upcoming):
        with cols[i % 3]:
            orgs_badges = " ".join(
                [f"<span style='background:{WFP_COLOR};color:white;padding:2px 7px;border-radius:10px;font-size:0.75em;'>WFP</span>" if o == "WFP" else
                 f"<span style='background:{DSA_COLOR};color:white;padding:2px 7px;border-radius:10px;font-size:0.75em;'>DSA</span>"
                 for o in c["orgs"]]
            )
            # Check for prior election history in CSV
            hist = get_candidate_history(df, c["csv_fragment"])
            if not hist.empty:
                last = hist.iloc[-1]
                hist_line = f"Last result: **{float(last['totalvotespercentage']):.1f}%** ({int(last['totalvotessum']):,} votes, {last['electionname']})"
            else:
                hist_line = "New candidate — no prior results in database"

            st.markdown(
                f"""<div style='background:{WFP_LIGHT};border-left:4px solid {WFP_COLOR};
                    border-radius:6px;padding:12px 14px;margin-bottom:10px;'>
                <b style='font-size:1.05em;'>{c['name']}</b> {orgs_badges}<br/>
                <span style='color:#555;font-size:0.9em;'>{c['office']} · {c['district']}</span><br/>
                <span style='color:#555;font-size:0.85em;'>{hist_line}</span><br/>
                <span style='color:#777;font-size:0.82em;'>{c['notes']}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Platform ────────────────────────────────────────────────────────────
    with st.expander("📋 WFP 2026 Platform Priorities", expanded=False):
        for p in WFP_PLATFORM:
            st.markdown(f"- {p}")
        st.markdown("[→ deworkingfamilies.org](https://www.deworkingfamilies.org)  |  "
                    "[→ workingfamilies.org/state/delaware](https://workingfamilies.org/state/delaware/)")

    # ── Historical track record ────────────────────────────────────────────
    st.markdown("### 📊 WFP Track Record (2020–2024)")

    wfp_names = [c["csv_fragment"] for c in WFP_CANDIDATES if c["year"] <= 2024]
    mask = pd.Series(False, index=df.index)
    for frag in wfp_names:
        mask |= df["candidatename"].str.upper().str.contains(frag.upper(), na=False)

    wfp_hist_df = df[mask].copy()

    if not wfp_hist_df.empty:
        # General elections only for cleaner view
        gen = wfp_hist_df[wfp_hist_df["election_type"] == "general"].copy()
        if not gen.empty:
            gen["pct"] = pd.to_numeric(gen["totalvotespercentage"], errors="coerce")
            gen["votes"] = pd.to_numeric(gen["totalvotessum"], errors="coerce")
            gen["label"] = gen["candidatename"].str.title()

            fig = px.bar(
                gen.sort_values(["year","pct"], ascending=[True, False]),
                x="pct", y="label", color="year",
                orientation="h",
                title="WFP-Endorsed Candidates — General Election Vote Share (%)",
                labels={"pct": "Vote %", "label": "Candidate", "year": "Year"},
                color_continuous_scale=["#FFCDD2", WFP_COLOR],
                text=gen["pct"].map(lambda x: f"{x:.1f}%"),
            )
            fig.update_layout(height=max(400, len(gen) * 22), yaxis={"categoryorder": "total ascending"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.markdown("#### All WFP Results (Primaries + Generals)")
        display_cols = ["year", "election_type", "candidatename", "office", "totalvotessum", "totalvotespercentage", "electionname"]
        available = [c for c in display_cols if c in wfp_hist_df.columns]
        tbl = wfp_hist_df[available].copy()
        tbl.columns = [c.replace("totalvotes","votes_").replace("election_type","type").replace("electionname","election") for c in tbl.columns]
        tbl = tbl.sort_values(["year", "candidatename"], ascending=[False, True])
        st.dataframe(tbl, use_container_width=True, height=420, hide_index=True)

        csv_dl = tbl.to_csv(index=False).encode()
        st.download_button("⬇️ Download WFP Data", data=csv_dl, file_name="delaware_wfp_results.csv", mime="text/csv")
    else:
        st.info("No historical matches found — check candidate name fragments in WFP_CANDIDATES.")

    # ── Current WFP Electeds ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🏆 WFP Incumbents (Currently Serving)")
    incumbents = [
        {"name": "Rep. Kamela T. Smith",       "office": "State Rep District 15",  "since": 2024},
        {"name": "Rep. Madinah Wilson-Anton",   "office": "State Rep District 26",  "since": 2020},
        {"name": "Rep. Eric Morrison",          "office": "State Rep District 27",  "since": 2020},
        {"name": "Rep. Larry D. Lambert Jr.",   "office": "State Rep District 7",   "since": 2020},
        {"name": "Rep. Sherae'a 'Rae' Moore",   "office": "State Rep District 8",   "since": 2020},
        {"name": "Rep. Deshanna Neal",          "office": "State Rep District 13",  "since": 2022},
        {"name": "Rep. Sophie Phillips",        "office": "State Rep District 18",  "since": 2022},
        {"name": "Rep. Cyndie Romer",           "office": "State Rep District 25",  "since": 2022},
        {"name": "Rep. Kerri Evelyn Harris",    "office": "State Rep District 32",  "since": 2022},
        {"name": "Rep. Frank Burns",            "office": "State Rep District 21",  "since": 2022},
        {"name": "Sen. Marie Pinkney",          "office": "State Senator District 13","since": 2020},
        {"name": "CM Christian Willauer",       "office": "Wilmington Council D5",  "since": 2020},
        {"name": "CM Coby Owens",               "office": "Wilmington Council D1",  "since": 2022},
        {"name": "CM Kevin Caneco",             "office": "NCC Council District 12","since": 2022},
    ]
    inc_cols = st.columns(3)
    for i, inc in enumerate(incumbents):
        with inc_cols[i % 3]:
            st.markdown(
                f"<div style='background:#fff;border:1px solid {WFP_COLOR};border-radius:5px;"
                f"padding:8px 12px;margin-bottom:8px;'>"
                f"<b>{inc['name']}</b><br/>"
                f"<span style='color:#555;font-size:0.88em;'>{inc['office']} · since {inc['since']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DSA
# ─────────────────────────────────────────────────────────────────────────────

def page_dsa(df: pd.DataFrame) -> None:
    st.markdown(
        f"<h1 style='color:{DSA_COLOR};'>✊ Democratic Socialists of America in Delaware</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "The Delaware DSA chapter endorses candidates committed to a socialist vision: "
        "Medicare for All, workers' power, housing as a right, and democratic control "
        "of the economy. DSA candidates run in Democratic primaries; many hold dual "
        "WFP/DSA endorsements."
    )

    # ── Metrics ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("2026 DSA Endorsed Races", len(DSA_CANDIDATES))
    col2.metric("Dual WFP+DSA Races", sum(1 for c in DSA_CANDIDATES if "WFP" in c["orgs"] and "DSA" in c["orgs"]))
    col3.metric("Primary Date", "September 15, 2026")

    st.markdown("---")

    # ── 2026 DSA Endorsed Candidates ───────────────────────────────────────
    st.markdown("### 🗓️ 2026 DSA-Endorsed Candidates")

    for c in DSA_CANDIDATES:
        hist = get_candidate_history(df, c["csv_fragment"])
        orgs_html = " ".join(
            [f"<span style='background:{WFP_COLOR};color:white;padding:2px 8px;border-radius:10px;font-size:0.8em;'>WFP</span>" if o == "WFP" else
             f"<span style='background:{DSA_COLOR};color:white;padding:2px 8px;border-radius:10px;font-size:0.8em;'>DSA</span>"
             for o in c["orgs"]]
        )
        st.markdown(
            f"""<div style='background:{DSA_LIGHT};border-left:5px solid {DSA_COLOR};
                border-radius:6px;padding:16px 18px;margin-bottom:14px;'>
            <h3 style='margin:0;color:{DSA_COLOR};'>{c['name']} {orgs_html}</h3>
            <p style='margin:4px 0;color:#444;'>{c['office']} · {c['district']} · {c['county']} County</p>
            <p style='margin:4px 0;'>{c['notes']}</p>
            </div>""",
            unsafe_allow_html=True,
        )

        if not hist.empty:
            st.markdown(f"**Historical results for {c['name']}:**")
            h = hist[["year","election_type","office","totalvotessum","totalvotespercentage","electionname"]].copy()
            h.columns = ["Year","Type","Office","Votes","Vote %","Election"]
            st.dataframe(h, use_container_width=True, hide_index=True)
        else:
            st.info(f"No prior election results in database for {c['name']} — first-time candidate.")

    st.markdown("---")

    # ── DSA Platform ────────────────────────────────────────────────────────
    st.markdown("### 📋 DSA Platform Priorities")
    col1, col2 = st.columns(2)
    half = len(DSA_PLATFORM) // 2
    with col1:
        for p in DSA_PLATFORM[:half]:
            st.markdown(f"- {p}")
    with col2:
        for p in DSA_PLATFORM[half:]:
            st.markdown(f"- {p}")

    st.markdown("[→ Delaware DSA on Instagram](https://www.instagram.com/delawaredsachapter/)  |  "
                "[→ DSA National](https://www.dsausa.org)")

    st.markdown("---")

    # ── WFP/DSA Overlap ────────────────────────────────────────────────────
    st.markdown("### 🤝 WFP + DSA Cross-Endorsements")
    st.markdown(
        "These candidates carry both WFP and DSA endorsements — the broadest "
        "progressive coalition in Delaware."
    )
    dual = [c for c in WFP_CANDIDATES + DSA_CANDIDATES
            if "WFP" in c["orgs"] and "DSA" in c["orgs"]]
    seen = set()
    unique_dual = [c for c in dual if not (c["name"] in seen or seen.add(c["name"]))]  # type: ignore

    if unique_dual:
        for c in unique_dual:
            hist = get_candidate_history(df, c["csv_fragment"])
            last_result = ""
            if not hist.empty:
                last = hist[hist["election_type"]=="general"]
                if not last.empty:
                    r = last.iloc[-1]
                    last_result = f" — {float(r['totalvotespercentage']):.1f}% in {int(r['year'])} general"
            st.markdown(
                f"**{c['name']}** · {c['office']} {c['district']} · {c['year']} primary{last_result}"
            )
    else:
        st.info("No dual WFP+DSA endorsees found for the selected cycle.")

    st.markdown("---")

    # ── WFP-aligned electeds context ───────────────────────────────────────
    st.markdown("### 🏛️ The Progressive Caucus Context")
    st.markdown(
        "While DSA's footprint in Delaware is growing, WFP-endorsed electeds "
        "form the backbone of Delaware's progressive legislative caucus — "
        "**14 current officeholders** who have won primaries against establishment "
        "Democrats since 2020. The 2026 cycle targets 5 incumbents who voted for "
        "**SB21** (the 'Elon Musk billionaire bill') plus one open seat."
    )
    st.markdown("See the **🌹 WFP** tab for the full incumbent tracker and historical vote data.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    df = load_data()

    if df.empty:
        st.error(
            "No election data found. "
            "Make sure the `data/` folder contains `elections_all.csv` and the 2018 TXT files."
        )
        st.stop()

    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Flag_of_Delaware.svg/200px-Flag_of_Delaware.svg.png",
            width=72,
        )
        st.markdown("## Delaware Election Modeler")
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["🏠 Dashboard", "🌹 WFP", "✊ DSA", "🎯 Simulator", "📋 Data Explorer"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        years = sorted(df["year"].dropna().astype(int).unique().tolist())
        st.caption(f"**{len(df):,}** records · {years[0]}–{years[-1]}")
        st.caption("Data: [Delaware DoE](https://elections.delaware.gov)")

    if   page == "🏠 Dashboard":     page_dashboard(df)
    elif page == "🌹 WFP":           page_wfp(df)
    elif page == "✊ DSA":           page_dsa(df)
    elif page == "🎯 Simulator":     page_simulator(df)
    elif page == "📋 Data Explorer": page_explorer(df)


if __name__ == "__main__":
    main()
