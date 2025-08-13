import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go


st.set_page_config(page_title="CASHFLOW MANAGEMENT", layout="wide")






col1, col2, col3 = st.columns([1, 5, 1])
with col2:
    st.markdown("<h1 style='text-align: center; margin: 0;'>CASHFLOW MANAGEMENT</h1>", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_excel(file):
    return pd.read_excel(file)

required_cols = [
    'วันที่จ่ายจริง', 'วันวางบิล', 'วันที่จะได้รับ/จ่าย',
    'ประเภท', 'ชื่อ', 'จำนวนเงิน'
]

uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])
if uploaded_file is None:
    st.info("กรุณาอัปโหลดไฟล์ก่อน")
    st.stop()

try:
    df = load_excel(uploaded_file)
except Exception:
    st.error("ไม่สามารถเปิดไฟล์ได้")
    st.stop()

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"คอลัมน์หายไป: {', '.join(missing)}")
    st.stop()

try:
    df['วันที่จ่ายจริง']       = pd.to_datetime(df['วันที่จ่ายจริง'], format='mixed')
    df['วันวางบิล']           = pd.to_datetime(df['วันวางบิล'], format='mixed')
    df['วันที่จะได้รับ/จ่าย']   = pd.to_datetime(df['วันที่จะได้รับ/จ่าย'], format='mixed')

    df['ระยะเวลา']           = (df['วันที่จ่ายจริง'] - df['วันวางบิล']).dt.days
    df['ระยะเวลาที่กำหนด']   = (df['วันที่จะได้รับ/จ่าย'] - df['วันวางบิล']).dt.days
    df['diff']               = df['ระยะเวลา'] - df['ระยะเวลาที่กำหนด']

    cols_to_hide = ['ระยะเวลา', 'ระยะเวลาที่กำหนด', 'diff']
    df_display = df.drop(columns=cols_to_hide, errors='ignore')
    st.dataframe(df_display, use_container_width=True)
except Exception:
    st.error("รูปแบบไม่ถูกต้อง")
    st.stop()

st.title('AR & AP DAYS')

start_date = df['วันที่จ่ายจริง'].min()
end_date   = pd.Timestamp.today().normalize()

mask = (df['วันที่จ่ายจริง'] >= start_date) & (df['วันที่จ่ายจริง'] <= end_date)
df_filtered = df.loc[mask].copy()

df_ar = df_filtered[df_filtered['ประเภท'] == 'ลูกหนี้']
df_ap = df_filtered[df_filtered['ประเภท'] == 'เจ้าหนี้']

if not df_ar.empty:
    dfarday    = int(df_ar['ระยะเวลา'].mean().round())
    dfarontime = int(df_ar['diff'].mean().round())
if not df_ap.empty:
    dfapday    = int(df_ap['ระยะเวลา'].mean().round())
    dfapontime = int(df_ap['diff'].mean().round())

col0, col1, col2 = st.columns(3)
with col0:
    st.metric("วันที่เริ่มต้นข้อมูล", start_date.strftime("%Y-%m-%d"))
with col1:
    st.metric("วันที่สิ้นสุด", end_date.strftime("%Y-%m-%d"))
with col2:
    st.metric("ระยะเวลาข้อมูลที่ใช้ในการคำนวณ", f"{(end_date - start_date).days} วัน")

cols = st.columns(2)
with cols[0]:
    if not df_ar.empty:
        st.metric("AR DAYS", f"{dfarday} วัน", delta=f"{dfarontime:+d} วัน(ช้า/เร็ว)", delta_color="inverse")
with cols[1]:
    if not df_ap.empty:
        st.metric("AP DAYS", f"{dfapday} วัน", delta=f"{dfapontime:+d} วัน(ช้า/เร็ว)", delta_color="normal")

dfar = df_filtered[df_filtered['ประเภท'] == 'ลูกหนี้']

avg_duration = (
    dfar.groupby('ชื่อ')['ระยะเวลา'].mean().round(0)
    .sort_values(ascending=False).rename('avg_duration').to_frame()
)

total_amount = (
    dfar.groupby('ชื่อ')['จำนวนเงิน'].sum().round(0)
    .sort_values(ascending=False).rename('total_amount').to_frame()
)

late_counts = (
    dfar[dfar['diff'] > 0].groupby('ชื่อ')['diff'].count().rename('late_freq')
)
total_counts = (
    dfar.groupby('ชื่อ')['diff'].count().rename('total_count')
)

late_pct = (
    pd.concat([late_counts, total_counts], axis=1)
    .assign(**{'% จ่ายเกินเวลา': lambda x: (x['late_freq'] / x['total_count']) * 100})
    [['% จ่ายเกินเวลา']]
    .round(0)
    .fillna(0)
)

bins = [-0.1, 10, 30, 50, 70, 100]
grades = ['ต่ำมาก', 'ต่ำ', 'ปานกลาง', 'เสี่ยง', 'เสี่ยงสูง']

late_pct['grade'] = pd.cut(late_pct['% จ่ายเกินเวลา'], bins=bins, labels=grades, right=True)
late_pct['description'] = pd.cut(late_pct['% จ่ายเกินเวลา'], bins=bins, right=True)

risk_table = late_pct.sort_values('% จ่ายเกินเวลา', ascending=False)[['% จ่ายเกินเวลา', 'grade']]

st.title('วิเคราะห์พฤติกรรมลูกหนี้')
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("เฉลี่ยระยะเวลา (วัน)")
    st.dataframe(avg_duration, use_container_width=True)
with col2:
    st.subheader("ยอดเงินรวม (฿)")
    st.dataframe(total_amount, use_container_width=True)
with col3:
    st.subheader("% จ่ายเกินเวลา & ความเสี่ยง")
    st.dataframe(risk_table, use_container_width=True)

dfap = df_filtered[df_filtered['ประเภท'] == 'เจ้าหนี้']

avg_durationap = (
    dfap.groupby('ชื่อ')['ระยะเวลาที่กำหนด'].mean()
    .sort_values(ascending=True).head(10)
    .rename('ระยะเวลาเฉลี่ย (น้อยสุด 10 อันดับ)').to_frame().round(0)
)

total_amountap = (
    dfap.groupby('ชื่อ')['จำนวนเงิน'].sum()
    .sort_values(ascending=True).head(10)
    .rename('ยอดเงินรวม (น้อยสุด 10 อันดับ)').to_frame().round(0)
)

st.title('วิเคราะห์พฤติกรรมเจ้าหนี้')
col1, col2 = st.columns(2)
with col1:
    st.subheader("ระยะเวลาเฉลี่ย 10 อันดับที่น้อยสุด")
    st.dataframe(avg_durationap, use_container_width=True)
with col2:
    st.subheader("ยอดเงินรวม 10 อันดับที่มากสุด")
    st.dataframe(total_amountap, use_container_width=True)

st.title('เงินสดสะสมรายวัน')

dfcashflow = pd.merge(df, late_pct, on='ชื่อ', how='left')
dfcashflow['riskamt'] = (dfcashflow['% จ่ายเกินเวลา']/100) * dfcashflow['จำนวนเงิน']
dfcashflow['cash_in']  = dfcashflow['จำนวนเงิน'].where(dfcashflow['จำนวนเงิน'] > 0, 0)
dfcashflow['cash_out'] = dfcashflow['จำนวนเงิน'].where(dfcashflow['จำนวนเงิน'] < 0, 0)

df_grouped = (
    dfcashflow.groupby('วันที่จ่ายจริง')
    .agg({'cash_in': 'sum', 'cash_out': 'sum'})
    .reset_index()
)

df_debtors = dfcashflow[dfcashflow['ประเภท'] == 'ลูกหนี้']
df_daily_risk = (
    df_debtors.groupby('วันที่จ่ายจริง')
    .agg({'riskamt': 'sum', 'จำนวนเงิน': 'sum'})
    .rename(columns={'riskamt': 'total_riskamt', 'จำนวนเงิน': 'total_amount'})
    .reset_index()
)
df_daily_risk['risk_ratio'] = df_daily_risk['total_riskamt'] / df_daily_risk['total_amount']
df_daily_risk['risk_pct']   = (df_daily_risk['risk_ratio'] * 100).round(2)

df_grouped = pd.merge(
    df_grouped, df_daily_risk, on='วันที่จ่ายจริง', how='left'
).fillna({'total_riskamt': 0, 'total_amount': 0, 'risk_ratio': 0, 'risk_pct': 0})

start_date2 = df_grouped['วันที่จ่ายจริง'].min()
end_date2   = df_grouped['วันที่จ่ายจริง'].max()
date_range  = pd.date_range(start=start_date2, end=end_date2, freq='D')
df_dates    = pd.DataFrame({'วันที่': date_range})

df_grouped.rename(columns={'วันที่จ่ายจริง': 'วันที่'}, inplace=True)
df_merged = df_dates.merge(df_grouped, on='วันที่', how='left').fillna(0)

df_merged['net_cash'] = df_merged['cash_in'] + df_merged['cash_out']

cash_accum = st.number_input('กรุณาใส่ค่าเงินสดยกมา:', value=0.0, step=10000.0, format="%.0f")

df_merged['เงินสดสะสม'] = df_merged['net_cash'].cumsum() + cash_accum
df_merged['วันที่'] = pd.to_datetime(df_merged['วันที่'])
df_merged = df_merged.set_index('วันที่')

df_merged = df_merged.rename(columns={
    'cash_in': 'กระแสเงินสดรับ',
    'cash_out': 'กระแสเงินสดจ่าย',
    'net_cash': 'กระแสเงินสดสุทธิ'
})

today = end_date
df_merged['สะสมจริง'] = df_merged['เงินสดสะสม'].where(df_merged.index <= today)
df_merged['สะสมคาดการณ์'] = df_merged['เงินสดสะสม'].where(df_merged.index > today)

st.subheader("กราฟเงินสดสะสมเทียบ Risk %")
rmin, rmax = st.slider("ช่วงแกนขวา Risk %", 0, 100, (70, 100), step=1)

fig = go.Figure()
fig.add_trace(go.Bar(x=df_merged.index, y=df_merged['risk_pct'], name='Risk %', yaxis='y2', opacity=0.4))
fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['สะสมจริง'], mode='lines', name='สะสมจริง'))
fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['สะสมคาดการณ์'], mode='lines', name='สะสมคาดการณ์'))

fig.update_layout(
    title='Cashflow Cumulative vs. Risk %',
    xaxis=dict(title='Date', showgrid=False, zeroline=False),
    yaxis=dict(title='Cumulative Cash', showgrid=False, zeroline=False),
    yaxis2=dict(title='Risk %', overlaying='y', side='right', range=[rmin, rmax], showgrid=False, zeroline=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

df_from_today = df_merged.loc[df_merged.index >= today, [
    'กระแสเงินสดรับ', 'กระแสเงินสดจ่าย', 'กระแสเงินสดสุทธิ', 'เงินสดสะสม', 'risk_pct'
]]
st.subheader('สรุปกระแสเงินสดรายวัน (ตั้งแต่วันนี้)')
st.dataframe(df_from_today, use_container_width=True)

st.title('วางแผนการจ่าย')

threshold = st.number_input('กรุณาใส่ค่า threshold (จำนวนเงินขั้นต่ำ):', min_value=0.0, value=0.0, step=100_000.0, format="%.0f")

df_merged = df_merged.loc[df_merged.index >= today].copy()
cash_accum_today = df_merged['เงินสดสะสม'].iloc[0]

df_cashout = (
    df.loc[(pd.to_datetime(df['วันที่จะได้รับ/จ่าย']) >= today) & (df['จำนวนเงิน'] < 0)]
    [['วันที่จะได้รับ/จ่าย', 'ชื่อ', 'จำนวนเงิน']].copy()
)
df_cashout.columns = ['วันที่', 'ชื่อเจ้าหนี้', 'จำนวนเงิน']
df_cashout['วันที่'] = pd.to_datetime(df_cashout['วันที่'])

df_cashout = (
    df_cashout.merge(df_merged[['เงินสดสะสม']], left_on='วันที่', right_index=True, how='left')
    .sort_values('วันที่')
)

payment_plan = []
for _, row in df_cashout.iterrows():
    orig_date = row['วันที่']
    creditor  = row['ชื่อเจ้าหนี้']
    amount    = row['จำนวนเงิน']
    cash      = row['เงินสดสะสม']

    if cash < threshold:
        try:
            pos = df_merged.index.get_loc(orig_date)
        except KeyError:
            continue
        j = pos + 1
        while j < len(df_merged) and df_merged.iloc[j]['เงินสดสะสม'] < threshold:
            j += 1
        if j < len(df_merged):
            new_date = df_merged.index[j]
            payment_plan.append({
                'ชื่อเจ้าหนี้': creditor,
                'วันที่เดิม': orig_date,
                'วันที่จ่ายใหม่': new_date,
                'จำนวนเงินที่เลื่อน': amount
            })

df_payment_plan = pd.DataFrame(payment_plan)

st.subheader('สรุปแผนเลื่อนชำระ (ตั้งแต่วันนี้)')
st.dataframe(df_payment_plan, use_container_width=True)

df_adjusted = df_merged[['กระแสเงินสดสุทธิ']].copy()
for _, row in df_payment_plan.iterrows():
    orig = row['วันที่เดิม']
    new  = row['วันที่จ่ายใหม่']
    amt  = row['จำนวนเงินที่เลื่อน']
    if orig in df_adjusted.index:
        df_adjusted.loc[orig, 'กระแสเงินสดสุทธิ'] -= amt
    if new in df_adjusted.index:
        df_adjusted.loc[new, 'กระแสเงินสดสุทธิ']  += amt

delta = df_adjusted['กระแสเงินสดสุทธิ'] - df_merged['กระแสเงินสดสุทธิ']
df_adjusted['เงินสดสะสม_adjusted'] = df_merged['เงินสดสะสม'] + delta.cumsum()

st.subheader('เปรียบเทียบเงินสดสะสม ก่อน–หลังเลื่อนชำระ (เริ่มตั้งแต่วันนี้)')
df_compare = pd.DataFrame({'ก่อนเลื่อน': df_merged['เงินสดสะสม'], 'หลังเลื่อน': df_adjusted['เงินสดสะสม_adjusted']})
st.line_chart(df_compare, use_container_width=True)
