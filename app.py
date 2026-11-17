"""South Korea external-resilience dashboard (six public no-key indicators)."""
from __future__ import annotations

import csv
import io

import pandas as pd
import streamlit as st

from data_sources import SERIES, load_snapshot, retrieve_all, save_snapshot

st.set_page_config(page_title="South Korea | External Resilience", page_icon="🇰🇷", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 2rem; max-width: 1350px}
[data-testid='stMetricValue'] {font-size: 1.65rem}
</style>""", unsafe_allow_html=True)

st.title("South Korea | External Resilience Monitor")
st.caption("International Finance · Are Korea's external buffers holding up despite won weakness?")

if "live_snapshot" not in st.session_state:
    st.session_state.live_snapshot = None

left, right = st.columns([3, 1])
with left:
    st.markdown("**USD/KRW is KRW per USD:** a higher number means **won depreciation** (a weaker won); a lower number means appreciation. Exchange-rate observations are the Federal Reserve's New York noon buying rates, not Seoul market closing rates.")
with right:
    if st.button("🔄 Refresh Data", type="primary", use_container_width=True, help="Fetch new public-source data for this session. Does not update the GitHub repository; the scheduled workflow does that."):
        try:
            with st.spinner("Retrieving six official series..."):
                fresh = retrieve_all()
            st.session_state.live_snapshot = fresh
            st.success("All six public sources were retrieved successfully for this session.")
        except Exception as e:
            st.error(f"Refresh failed. Keeping the previous valid dataset. Details: {e}")

try:
    saved = load_snapshot()
except Exception as e:
    saved = None
    st.warning(f"Stored data could not be read: {e}")
data = st.session_state.live_snapshot or saved

if data is None:
    st.warning("No verified data snapshot exists yet. Click **Refresh Data** or run the GitHub Actions workflow after deployment. No example values are fabricated.")
    st.info("This dashboard retrieves public CSV data from FRED and JSON data from the World Bank. No API credentials or registration are necessary.")
    st.stop()

last = pd.to_datetime(data["last_successful_refresh_utc"], utc=True)
st.markdown(f"**Last successful data refresh:** {last.strftime('%Y-%m-%d %H:%M:%S UTC')}  ·  **Mode:** {'Live in this session' if st.session_state.live_snapshot else 'Scheduled saved snapshot'}")
st.caption("This is the successful retrieval time — **not** the latest observation date. Each series below has its own publication period.")

with st.sidebar:
    st.header("Display")
    from_year = st.slider("Historical start year", min_value=2000, max_value=2022, value=2005)
    st.caption("Annual indicators update more slowly than market series. Default view starts in 2005 to include the global financial crisis.")
    st.markdown("**Sources**")
    st.markdown("[Federal Reserve / FRED](https://fred.stlouisfed.org/)  \n[World Bank](https://data.worldbank.org/)  \n[OECD](https://www.oecd.org/)")

ORDER = ["fx", "yield10", "gdp", "cpi", "current_account", "reserves"]
for group, members in [("Currency and financial markets", ["fx", "yield10"]), ("Domestic economic conditions", ["gdp", "cpi"]), ("External resilience buffers", ["current_account", "reserves"])]:
    st.subheader(group)
    cols = st.columns(2, gap="large")
    for i, key in enumerate(members):
        s = data["series"][key]
        with cols[i]:
            st.markdown(f"#### {s['title']}")
            st.metric("Latest value", f"{s['latest_value']:,.2f} {s['units']}", help=f"Observation date: {s['latest_observation_date']}")
            # Period labels are kept intact: annual series are years, monthly yield is month start.
            df = pd.DataFrame(s["observations"])
            df["date"] = pd.to_datetime(df["date"], errors="raise")
            df = df[df["date"].dt.year >= from_year]
            df = df.set_index("date")
            st.line_chart(df["value"], height=225, x_label="Observation period", y_label=s["units"], use_container_width=True)
            st.caption(f"**Frequency:** {s['frequency']} · **Latest observation:** {s['latest_observation_date']}  \n**Source:** {s['source']} (`{s['code']}`) · [Original series]({s['url']})")
            with st.expander("Definition and transformations"):
                st.write(s["detail"])
                st.write("Dates and figures are returned by the source. No forward filling, interpolation or invented current-period values are used.")

st.divider()
st.subheader("Verify one observation per indicator")
st.write("Compare each dashboard value with the **same period** on its linked official source page. A value retrieved twice from this app is not an independent verification. Record the source value, comparison result and evidence before submitting.")
verification_rows = []
for key in ORDER:
    s = data["series"][key]
    verification_rows.append({"Indicator": s["title"], "Code": s["code"], "Observation date": s["latest_observation_date"], "Dashboard value": s["latest_value"], "Units": s["units"], "Original source value": "", "Match?": "", "Checked on": "", "Official URL": s["url"]})
verify_df = pd.DataFrame(verification_rows)
st.dataframe(verify_df, use_container_width=True, hide_index=True, column_config={"Official URL": st.column_config.LinkColumn("Official URL")})
buffer = io.StringIO()
verify_df.to_csv(buffer, index=False)
st.download_button("Download verification worksheet (CSV)", data=buffer.getvalue().encode("utf-8-sig"), file_name="south_korea_verification.csv", mime="text/csv")

with st.expander("How to demonstrate an automatic refresh"):
    st.markdown("1. In GitHub, open **Actions → Refresh official data** and run the workflow manually or view its daily run.  \n2. Capture a successful job log containing `result: SUCCESS` and the retrieval timestamp.  \n3. Compare that time to **Last successful data refresh** above.  \n4. Independently verify one observation per series using the worksheet.")

st.caption("Interpretation caution: market indicators are daily/monthly, while GDP, CPI, current account and reserves are annual. Currency depreciation alone does not establish external vulnerability. Reserve coverage and short-term foreign-currency debt are not measured here.")
