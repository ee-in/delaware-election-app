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
            ["🏠 Dashboard", "🎯 Simulator", "📋 Data Explorer"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        years = sorted(df["year"].dropna().astype(int).unique().tolist())
        st.caption(f"**{len(df):,}** records · {years[0]}–{years[-1]}")
        st.caption("Data: [Delaware DoE](https://elections.delaware.gov)")

    if   page == "🏠 Dashboard":    page_dashboard(df)
    elif page == "🎯 Simulator":    page_simulator(df)
    elif page == "📋 Data Explorer": page_explorer(df)


if __name__ == "__main__":
    main()
