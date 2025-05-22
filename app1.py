import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import streamlit as st

try:
    # Load the COVID-19 data
   
    df_cases = pd.read_csv("https://raw.githubusercontent.com/babdelfa/project/refs/heads/main/cases_data.csv")
    df_deaths = pd.read_csv("https://raw.githubusercontent.com/babdelfa/project/refs/heads/main/deaths_data.csv")
    

    # Load county geometry from a local ZIP (ensure it's in the same folder as this script)
    county_shapes = gpd.read_file("counties_geometry.zip")
   
    # Standardize column names
    df_cases.columns = df_cases.columns.str.lower()
    df_deaths.columns = df_deaths.columns.str.lower()

    # Detect state column
    if 'state' in df_cases.columns:
        state_col = 'state'
    elif 'province_state' in df_cases.columns:
        state_col = 'province_state'
    else:
        st.error("State column not found in dataset.")
        st.stop()

    # Streamlit UI

    st.set_page_config(page_title="COVID-19 Dashboard", layout="wide")
    st.title("COVID-19 Dashboard")
    st.subheader("U.S. Cases & Deaths Trends (2020-2021)")
    name = st.text_input("Enter your name:", " ")
    input_state = st.selectbox("Select a U.S. state:", sorted(df_cases[state_col].dropna().unique()))

    # Preprocess
    df_cases = df_cases.drop(columns=["uid", "iso3", "code3", "fips", "long_", "lat"], errors='ignore')
    df_cases = df_cases.rename(columns={"combined_key": "county_state"})
    df_cases_melted = pd.melt(df_cases, id_vars=["county", state_col, "county_state"], var_name="date", value_name="cases")

    df_deaths = df_deaths.drop(columns=["iso3", "population"], errors='ignore')
    df_deaths = df_deaths.rename(columns={"combined_key": "county_state", "late": "latitude", "long_": "longitud"})
    df_deaths_melted = pd.melt(df_deaths, id_vars=["fips", "county", state_col, "latitude", "longitud", "county_state"], var_name="date", value_name="deaths")

    # Merge
    df_cases_melted["date"] = pd.to_datetime(df_cases_melted["date"])
    df_deaths_melted["date"] = pd.to_datetime(df_deaths_melted["date"])
    df_merged = pd.merge(df_cases_melted, df_deaths_melted)

    # Date info
    day_0 = df_merged.loc[(df_merged[state_col] == input_state) & (df_merged.cases > 0), "date"].min()
    day_0_str = day_0.strftime('%B %d, %Y')
    as_of_date = df_merged.date.max().strftime('%B %d, %Y')

    # Compute stats
    def compute_stats(df, year):
        df = df[(df[state_col] == input_state) & (df.date.dt.year == year)].sort_values(["county", "date"])
        final = df[df.date == df.date.max()]
        df["new_cases"] = df.groupby("county")["cases"].diff()
        df["new_deaths"] = df.groupby("county")["deaths"].diff()
        return {
            "data": df,
            "cases": final["cases"].sum(),
            "deaths": final["deaths"].sum(),
            "avg_new_cases": df.groupby("date")["new_cases"].sum().mean(),
            "avg_new_deaths": df.groupby("date")["new_deaths"].sum().mean(),
        }

    stats_2020 = compute_stats(df_merged, 2020)
    stats_2021 = compute_stats(df_merged, 2021)
    total_cases = stats_2020["cases"] + stats_2021["cases"]
    total_deaths = stats_2020["deaths"] + stats_2021["deaths"]

    # Show metrics
    st.markdown(f"<h2 style='font-size:28px;'>COVID-19 Summary for {input_state}</h2>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color:gray;'>Day 0: {day_0_str}</h4>", unsafe_allow_html=True)

    # Row 1
    col1, col2, col3 = st.columns(3)
    col1.metric("2020 Total Cases", f"{stats_2020['cases']:,}")
    col2.metric("2020 Avg Daily Cases", f"{stats_2020['avg_new_cases']:,.2f}")
    col3.metric("2020 Total Deaths", f"{stats_2020['deaths']:,}")

    # Row 2
    col4, col5, col6 = st.columns(3)
    col4.metric("2020 Avg Daily Deaths", f"{stats_2020['avg_new_deaths']:,.2f}")
    col5.metric("2021 Total Cases", f"{stats_2021['cases']:,}")
    col6.metric("2021 Avg Daily Cases", f"{stats_2021['avg_new_cases']:,.2f}")

    # Row 3
    col7, col8, col9 = st.columns(3)
    col7.metric("2021 Total Deaths", f"{stats_2021['deaths']:,}")
    col8.metric("2021 Avg Daily Deaths", f"{stats_2021['avg_new_deaths']:,.2f}")
    col9.metric("Total Cases (2020–2021)", f"{total_cases:,}")

    # Row 4 (optional)
    st.metric("Total Deaths (2020–2021)", f"{total_deaths:,}")

    # Visualization
    option = st.radio("Choose a visualization:", ["4 Trend Charts", "Choropleth Map"])

    if option == "4 Trend Charts":
        combined = pd.concat([stats_2020["data"], stats_2021["data"]]).sort_values("date")
        fig, ax = plt.subplots(2, 2, figsize=(14, 10))
        ax[0, 0].bar(combined.groupby("date")["new_cases"].sum().index, combined.groupby("date")["new_cases"].sum())
        ax[0, 0].set_title("Daily New Cases", fontweight='bold')
        ax[0, 1].plot(combined.groupby("date")["cases"].sum().index, combined.groupby("date")["cases"].sum())
        ax[0, 1].set_title("Cumulative Cases", fontweight='bold')
        ax[1, 0].bar(combined.groupby("date")["new_deaths"].sum().index, combined.groupby("date")["new_deaths"].sum())
        ax[1, 0].set_title("Daily New Deaths", fontweight='bold')
        ax[1, 1].plot(combined.groupby("date")["deaths"].sum().index, combined.groupby("date")["deaths"].sum())
        ax[1, 1].set_title("Cumulative Deaths", fontweight='bold')
        plt.suptitle(f"{input_state} COVID-19 Report for {name}", size =23)
        plt.tight_layout(pad=5) 

        for a in ax.flat:
            a.set_xlabel("Date")
            a.tick_params(axis="x", rotation=45)
        st.pyplot(fig)

    elif option == "Choropleth Map":
        latest_date = df_merged['date'].max()
        latest_df = df_merged[df_merged['date'] == latest_date]
        state_cases = latest_df.groupby(["county_state", "county", "fips", state_col], as_index=False)[["cases", "deaths"]].sum()
        gdf = pd.merge(county_shapes, state_cases, left_on="FIPS_BEA", right_on="fips")
        gdf_filtered = gdf[gdf[state_col] == input_state]
        st.subheader(f"Choropleth Map for {input_state} as of {latest_date.strftime('%B %d, %Y')}")
        gdf_tooltip = gdf_filtered.rename(columns={"state": "State", "county": "County", "cases": "Cases", "deaths": "Deaths"})
        map_object = gdf_tooltip.explore(
        column="Cases",
        cmap="Set2",
        legend=True,
        scheme="EqualInterval",
        tooltip=["State", "County", "Cases", "Deaths"]
        )
        st.components.v1.html(map_object._repr_html_(), height=800, scrolling=True)
except Exception as e:
    st.error("An unexpected error occurred while loading the app. Please try again later.")
   
