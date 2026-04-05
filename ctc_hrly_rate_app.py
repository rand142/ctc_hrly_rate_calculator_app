import streamlit as st
import pandas as pd
import holidays
import json

# -------------------------------
# Tax Calculation Helpers
# -------------------------------
def load_tax_brackets(filepath="tax_brackets.json"):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("⚠️ Tax brackets file not found. Please ensure tax_brackets.json is in the app directory.")
        return {"brackets": [], "rebates": {"primary":0,"secondary":0,"tertiary":0}}

def calculate_tax(annual_income, age, filepath="tax_brackets.json"):
    data = load_tax_brackets(filepath)
    brackets = data["brackets"]
    rebates = data["rebates"]

    tax = 0
    for b in brackets:
        if b["upper"] is None or annual_income <= b["upper"]:
            tax = b["base"] + b["rate"] * (annual_income - b["lower"])
            break

    # Apply rebates
    rebate = rebates["primary"]
    if age >= 65:
        rebate += rebates["secondary"]
    if age >= 75:
        rebate += rebates["tertiary"]

    return max(tax - rebate, 0)

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
        all_days = pd.date_range(self.start_date, self.end_date, freq="D")
        weekdays = all_days[~all_days.weekday.isin([5, 6])]
        holiday_list = holidays.country_holidays(
            self.country, years=range(self.start_date.year, self.end_date.year + 1)
        )
        working_days = [day for day in weekdays if day not in holiday_list]
        return pd.DatetimeIndex(working_days)

    def breakdown(self, age=30):
        working_days = self.get_working_days()
        total_working_days = len(working_days)
        total_amount = total_working_days * self.daily_rate

        periods = {}

        # Handle initial partial period if start_date is before the 21st
        if self.start_date.day < 21:
            end = pd.Timestamp(self.start_date.year, self.start_date.month, 20)
            period_days = working_days[(working_days >= self.start_date) & (working_days <= end)]
            if len(period_days) > 0:
                label = f"{self.start_date.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
                periods[label] = round(len(period_days) * self.daily_rate, 2)
            current = pd.Timestamp(self.start_date.year, self.start_date.month, 21)
        else:
            current = pd.Timestamp(self.start_date.year, self.start_date.month, 21)
            if current < self.start_date:
                if current.month == 12:
                    current = pd.Timestamp(current.year + 1, 1, 21)
                else:
                    current = pd.Timestamp(current.year, current.month + 1, 21)

        # Continue with normal 21st→20th cycles
        while current < self.end_date:
            if current.month == 12:
                end = pd.Timestamp(current.year + 1, 1, 20)
            else:
                end = pd.Timestamp(current.year, current.month + 1, 20)

            period_days = working_days[(working_days >= current) & (working_days <= end)]
            if len(period_days) > 0:
                label = f"{current.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
                periods[label] = round(len(period_days) * self.daily_rate, 2)

            current = end + pd.Timedelta(days=1)

        # Tax calculation
        annual_income = total_amount
        annual_tax = calculate_tax(annual_income, age)
        monthly_tax = annual_tax / 12
        net_monthly_income = (annual_income - annual_tax) / 12

        return {
            "total_working_days": total_working_days,
            "gross_total": round(total_amount, 2),
            "custom_period_breakdown": periods,
            "annual_tax": round(annual_tax, 2),
            "monthly_tax": round(monthly_tax, 2),
            "net_monthly_income": round(net_monthly_income, 2),
        }

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="CTC Calculator", layout="centered")

st.title("💰 Hourly Rate Cost-to-Company Calculator")

hourly_rate = st.number_input("Enter Hourly Rate (ZAR)", min_value=0.0, value=200.0, step=1.0)
hours_per_day = st.number_input("Hours Worked per Day", min_value=1, value=8, step=1)
start_date = st.date_input("Start Date", pd.to_datetime("2025-10-01"))
end_date = st.date_input("End Date", pd.to_datetime("2026-12-31"))
country = st.text_input("Country Code (default ZA)", "ZA")
age = st.number_input("Enter Age (for rebate)", min_value=18, value=30, step=1)

if st.button("Calculate"):
    calc = HourlyCTCCalculator(hourly_rate, start_date, end_date, hours_per_day, country)
    result = calc.breakdown(age)

    st.subheader("📊 Results")
    st.write(f"**Total Working Days:** {result['total_working_days']}")
    st.write(f"**Gross Annual Earnings:** ZAR {result['gross_total']}")
    st.write(f"**Annual Tax:** ZAR {result['annual_tax']}")
    st.write(f"**Monthly Tax Deduction (average):** ZAR {result['monthly_tax']}")
    st.write(f"**Net Monthly Take-Home (average):** ZAR {result['net_monthly_income']}")

    st.subheader("📅 Pay Period Breakdown (21st → 20th)")
    period_df = pd.DataFrame(
        list(result["custom_period_breakdown"].items()), columns=["Period", "Amount"]
    )
    st.table(period_df)
    st.bar_chart(period_df.set_index("Period"))

    csv = period_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Pay Period Breakdown as CSV",
        data=csv,
        file_name="pay_period_breakdown.csv",
        mime="text/csv",
    )
