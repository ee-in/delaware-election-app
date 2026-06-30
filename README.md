# Delaware Election Modeling Web-App

An interactive web application for exploring, analyzing, and modeling Delaware election results from 2018–2024.

## Features

- 📊 **Dashboard** — Historical election results for all major races
- 🗺️ **Map View** — District-level results (add GeoJSON to enable)
- 🎯 **Simulator** — Model hypothetical scenarios (turnout shifts, partisan swings)
- 📋 **Data Explorer** — Browse and download the underlying data

## Data Sources

All data is sourced from official Delaware government sources:

| Dataset | Source | Coverage |
|---|---|---|
| Election Results | [Delaware Dept. of Elections](https://elections.delaware.gov) | 2018–2024 |
| Open Data Portal | [data.delaware.gov](https://data.delaware.gov/resource/4hbv-7brf) | 2018–2024 |

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

This app is deployed on [Streamlit Cloud](https://streamlit.io/cloud).

## Adding More Data

Drop additional CSVs into the `data/` folder matching this schema:

| Column | Description |
|---|---|
| `Office` | Office name |
| `CandidateName` | Full candidate name |
| `PartyName` | Political party |
| `ElectionDate` | Date (YYYY-MM-DD) |
| `MachineVotesSum` | Machine votes |
| `AbsenteeVotesSum` | Absentee votes |
| `EarlyVotesSum` | Early votes |
| `TotalVotesSum` | Total votes |
| `TotalVotesPercentage` | % of total |
| `ElectionName` | Full race name |
| `election_year` | Year (added at load) |
| `election_type` | general/primary/special |

## License

Data is public domain (Delaware state government). App code is MIT licensed.
