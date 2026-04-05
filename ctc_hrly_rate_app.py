import streamlit as st
import pandas as pd
import holidays

# -------------------------------
# Core Calculator Class
# -------------------------------
class HourlyCTCCalculator:
    def __init__(self, hourly_rate, start_date, end_date, hours_per_day=8, country="ZA"):
        self.hourly_rate = float(hourly_rate)
        self.hours_per_day = float(hours_per_day)
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.country = country
        self.daily_rate = self.hourly_rate * self.hours_per_day

    def get_working_days(self):
        # Generate all days in range
        all_days = pd.date_range(self.start_date, self.end_date, freq="D")
        # Exclude weekends
        weekdays = all_days[~all_days.weekday.isin([5, 6])]
        # Exclude public holidays
        holiday_list = holidays.country_holidays(
            self.country,
            years=range(self.start_date.year, self.end_date.year + 1)
        )
        working_days = [day for day in weekdays if day not in holiday_list]
        return pd.DatetimeIndex(working_days)

    def breakdown(self):
        working_days = self.get_working_days()
        total_working_days = len(working_days)
        total_amount = total_working_days * self.daily_rate

        monthly_breakdown = (
            pd.Series(working_days)
            .groupby(working_days.to_period("M"))
            .count()
            .apply(lambda d: d * self.daily_rate)
        )

        return {
            "total_working_days": total_working_days,
            "total_amount": round(total_amount, 2),
            "monthly_breakdown": monthly_breakdown.round(2).to_dict()
        }

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="CTC Calculator", layout="centered")

st.title("💰 Hourly Rate Cost-to-Company Calculator")

# Inputs
hourly_rate = st.number_input("Enter Hourly Rate (ZAR)", min_value=0.0, value=556.5, step=1.0)
hours_per_day = st.number_input("Hours Worked per Day", min_value=1, value=8, step=1)
start_date = st.date_input("Start Date", pd.to_datetime("2026-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("2026-12-31"))
country = st.text_input("Country Code (default ZA)", "ZA")

# Calculate button
if st.button("Calculate"):
    calc = HourlyCTCCalculator(hourly_rate, start_date, end_date, hours_per_day, country)
    result = calc.breakdown()

    # Results
    st.subheader("📊 Results")
    st.write(f"**Total Working Days:** {result['total_working_days']}")
    st.write(f"**Grand Total Earnings:** ZAR {result['total_amount']}")

    # Monthly breakdown
    st.subheader("📅 Monthly Breakdown")
    monthly_df = pd.DataFrame(list(result["monthly_breakdown"].items()), columns=["Month", "Amount"])
    st.table(monthly_df)
    st.bar_chart(monthly_df.set_index("Month"))

    # Optional: CSV download
    csv = monthly_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Monthly Breakdown as CSV",
        data=csv,
        file_name="monthly_breakdown.csv",
        mime="text/csv",
    )
