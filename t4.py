
import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go


st.set_page_config(
    page_title="CASHFLOW MANAGEMENT",
    layout="wide"
)

col1, col2, col3 = st.columns([1, 5, 1])

with col2:
    st.markdown(
        "<h1 style='text-align: center; margin: 0;'>CASHFLOW MANAGEMENT by quantifin</h1>",
        unsafe_allow_html=True
    )

uploaded_file = st.file_uploader(
    "Choose an Excel file",
    type=['xlsx']
)
# ถ้ายังไม่อัปโหลดไฟล์ ให้แสดงข้อความแล้วหยุดรันต่อ
if uploaded_file is None:
    st.info("กรุณาอัปโหลดไฟล์ก่อน")
    st.stop()

# ถ้ามีไฟล์แล้ว จะมาถึงตรงนี้เท่านั้น
df = pd.read_excel(uploaded_file)
try:
    # แปลงวันที่
    df['วันที่จ่ายจริง']       = pd.to_datetime(df['วันที่จ่ายจริง'], format='mixed')
    df['วันวางบิล']           = pd.to_datetime(df['วันวางบิล'], format='mixed')
    df['วันที่จะได้รับ/จ่าย']   = pd.to_datetime(df['วันที่จะได้รับ/จ่าย'], format='mixed')

    # คำนวณระยะเวลา
    df['ระยะเวลา']           = (df['วันที่จ่ายจริง'] - df['วันวางบิล']).dt.days
    df['ระยะเวลาที่กำหนด'] = (df['วันที่จะได้รับ/จ่าย'] - df['วันวางบิล']).dt.days
    df['diff']               = df['ระยะเวลา'] - df['ระยะเวลาที่กำหนด']

    # ซ่อนคอลัมน์ไม่ต้องการ
    cols_to_hide = ['ระยะเวลา', 'ระยะเวลาที่กำหนด', 'diff']
    df_display = df.drop(columns=cols_to_hide)

    # แสดงผล
    st.write(df_display)

except Exception:
    st.error("รูปแบบไม่ถูกต้อง")
    st.stop()
###############################################################################################################################
st.title('AR & AP DAYS')

# กำหนดขอบเขตช่วงเวลา
start_date = df['วันที่จ่ายจริง'].min()                    # วันที่เก่าสุดในชุดข้อมูล
end_date   = pd.Timestamp.today().normalize()             # วันนี้ (ตัดเวลาเป็นเที่ยงคืน)

# กรอง DataFrame
mask = (df['วันที่จ่ายจริง'] >= start_date) & (df['วันที่จ่ายจริง'] <= end_date)
df_filtered = df.loc[mask].copy()

# เตรียม DataFrame ย่อย
df_ar = df_filtered[df_filtered['ประเภท'] == 'ลูกหนี้']
df_ap = df_filtered[df_filtered['ประเภท'] == 'เจ้าหนี้']

# คำนวณค่าเฉลี่ย (ถ้ามีข้อมูล)
if not df_ar.empty:
    dfarday    = int(df_ar['ระยะเวลา'].mean().round())
    dfarontime = int(df_ar['diff'].mean().round())
if not df_ap.empty:
    dfapday    = int(df_ap['ระยะเวลา'].mean().round())
    dfapontime = int(df_ap['diff'].mean().round())

# --- แสดงช่วงข้อมูล (Date Range) ---
col0, col1, col2 = st.columns(3)
with col0:
    st.metric("วันที่เริ่มต้นข้อมูล", start_date.strftime("%Y-%m-%d"))
with col1:
    st.metric("วันที่สิ้นสุด",      end_date.strftime("%Y-%m-%d"))
with col2:
    st.metric("ระยะเวลาข้อมูลที่ใช้ในการคำนวณ",
              f"{(end_date - start_date).days} วัน")

# แสดงผล AR / AP DAYS เฉพาะกรณีที่มีข้อมูล
cols = st.columns(2)
# AR DAYS
with cols[0]:
    if not df_ar.empty:
        st.metric(
            label="AR DAYS",
            value=f"{dfarday} วัน",
            delta=f"{dfarontime:+d} วัน(ช้า/เร็ว)",
            delta_color="inverse"
        )
# AP DAYS
with cols[1]:
    if not df_ap.empty:
        st.metric(
            label="AP DAYS",
            value=f"{dfapday} วัน",
            delta=f"{dfapontime:+d} วัน(ช้า/เร็ว)",
            delta_color="normal"
        )


###############################################################################################################################

dfar = df_filtered[df_filtered['ประเภท'] == 'ลูกหนี้']

# 1) เฉลี่ยระยะเวลา (เรียงจากค่าเฉลี่ยระยะเวลามากที่สุดลงมาน้อยที่สุด)
avg_duration = (
    dfar
    .groupby('ชื่อ')['ระยะเวลา']
    .mean()
    .round(0)
    .sort_values(ascending=False)
    .rename('avg_duration')
    .to_frame()
)

# 2) ยอดเงินรวม (เรียงจากยอดเงินรวมมากที่สุดลงมาน้อยที่สุด)
total_amount = (
    dfar
    .groupby('ชื่อ')['จำนวนเงิน']
    .sum()
    .round(0)
    .sort_values(ascending=False)
    .rename('total_amount')
    .to_frame()
)

# 1) คำนวณ late_freq และ total_count
late_counts = (
    dfar[dfar['diff'] > 0]
    .groupby('ชื่อ')['diff']
    .count()
    .rename('late_freq')
)
total_counts = (
    dfar
    .groupby('ชื่อ')['diff']
    .count()
    .rename('total_count')
)

# 2) สร้างตาราง % จ่ายเกินเวลา
late_pct = (
    pd.concat([late_counts, total_counts], axis=1)
    .assign(**{'% จ่ายเกินเวลา': lambda x: (x['late_freq'] / x['total_count']) * 100})
    [['% จ่ายเกินเวลา']]
    .round(0)
    .fillna(0)
)

# 3) กำหนดเงื่อนไขแบ่งเกรดและคำอธิบาย
bins = [ -0.1, 10, 30, 50, 70, 100 ]
grades      = ['ต่ำมาก', 'ต่ำ', 'ปานกลาง', 'เสี่ยง', 'เสี่ยงสูง']


late_pct['grade'] = pd.cut(
    late_pct['% จ่ายเกินเวลา'],
    bins=bins,
    labels=grades,
    right=True
)

late_pct['description'] = pd.cut(
    late_pct['% จ่ายเกินเวลา'],
    bins=bins,
    right=True
)

# 4) เรียงจาก % จ่ายเกินเวลามาก→น้อย
risk_table = late_pct.sort_values('% จ่ายเกินเวลา', ascending=False)[
    ['% จ่ายเกินเวลา', 'grade']
]




# --- Streamlit layout ---
st.title('วิเคราะห์พฤติกรรมลูกหนี้')

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("เฉลี่ยระยะเวลา (วัน)")
    st.write(avg_duration)

with col2:
    st.subheader("ยอดเงินรวม (฿)")
    st.write(total_amount)

with col3:
    st.subheader("% จ่ายเกินเวลา & ความเสี่ยง")
    st.write(risk_table)

###############################################################################################################################

dfap = df_filtered[df_filtered['ประเภท'] == 'เจ้าหนี้']

# 1) ระยะเวลาเฉลี่ย 10 รายการที่ระยะเวลาสั้นที่สุด
avg_durationap = (
    dfap
    .groupby('ชื่อ')['ระยะเวลาที่กำหนด']
    .mean()
    .sort_values(ascending=True)
    .head(10)
    .rename('ระยะเวลาเฉลี่ย (น้อยสุด 10 อันดับ)')
    .to_frame()
)

# 2) ยอดเงินรวม 10 รายการที่จำนวนเงินน้อยที่สุด
total_amountap = (
    dfap
    .groupby('ชื่อ')['จำนวนเงิน']
    .sum()
    .sort_values(ascending=True)
    .head(10)
    .rename('ยอดเงินรวม (น้อยสุด 10 อันดับ)')
    .to_frame()
)
avg_durationap = avg_durationap.round(0)
total_amountap = total_amountap.round(0)

st.title('วิเคราะห์พฤติกรรมเจ้าหนี้')

# สร้างสองคอลัมน์เรียงจากซ้ายไปขวา
col1, col2 = st.columns(2)

with col1:
    st.subheader("ระยะเวลาเฉลี่ย 10 อันดับที่น้อยสุด")
    st.write(avg_durationap)

with col2:
    st.subheader("ยอดเงินรวม 10 อันดับที่มากสุด")
    st.write(total_amountap)


###############################################################################################################################


st.title('เงินสดสะสมรายวัน')

dfcashflow = pd.merge(df, late_pct, on='ชื่อ', how='left')
dfcashflow['riskamt'] = (dfcashflow['% จ่ายเกินเวลา']/100)*dfcashflow['จำนวนเงิน']
dfcashflow['cash_in']  = dfcashflow['จำนวนเงิน'].where(dfcashflow['จำนวนเงิน'] > 0, 0)
dfcashflow['cash_out'] = dfcashflow['จำนวนเงิน'].where(dfcashflow['จำนวนเงิน'] < 0, 0)



# 2) สรุปยอดรับ-จ่ายรายวัน
df_grouped = (
    dfcashflow
    .groupby('วันที่จ่ายจริง')
    .agg({'cash_in': 'sum', 'cash_out': 'sum'})
    .reset_index()
)


# 1) รวมยอด riskamt และ จำนวนเงิน ตามวัน
# กรองเฉพาะลูกหนี้ก่อน
df_debtors = dfcashflow[dfcashflow['ประเภท'] == 'ลูกหนี้']

# สรุปยอด riskamt และ จำนวนเงิน ตามวัน (เฉพาะลูกหนี้)
df_daily_risk = (
    df_debtors
    .groupby('วันที่จ่ายจริง')
    .agg({
        'riskamt': 'sum',
        'จำนวนเงิน': 'sum'
    })
    .rename(columns={
        'riskamt': 'total_riskamt',
        'จำนวนเงิน': 'total_amount'
    })
    .reset_index()
)

# คำนวณสัดส่วนความเสี่ยง และเปอร์เซ็นต์
df_daily_risk['risk_ratio'] = df_daily_risk['total_riskamt'] / df_daily_risk['total_amount']
df_daily_risk['risk_pct']   = (df_daily_risk['risk_ratio'] * 100).round(2)


df_grouped = pd.merge(
    df_grouped,
    df_daily_risk,
    on='วันที่จ่ายจริง',
    how='left'          # ถ้าวันไหนไม่มีความเสี่ยง ก็จะแทนด้วย NaN
).fillna({          # เติม 0 ให้กับค่าว่าง
    'total_riskamt': 0,
    'total_amount':   0,
    'risk_ratio':     0,
    'risk_pct':       0
})











# 3) เตรียมช่วงวันที่เต็ม
start_date = df_grouped['วันที่จ่ายจริง'].min()
end_date2   = df_grouped['วันที่จ่ายจริง'].max()
date_range = pd.date_range(start=start_date, end=end_date2, freq='D')
df_dates   = pd.DataFrame({'วันที่': date_range})

# 4) รวมกับ df_grouped และเติม 0
df_grouped.rename(columns={'วันที่จ่ายจริง': 'วันที่'}, inplace=True)
df_merged = df_dates.merge(df_grouped, on='วันที่', how='left').fillna(0)

# 5) คำนวณ net_cash
df_merged['net_cash'] = df_merged['cash_in'] + df_merged['cash_out']

# 6) คำนวณ net_cash






# 7) รับค่าเงินสดยกมา
cash_accum = st.number_input(
    'กรุณาใส่ค่าเงินสดยกมา:',
    value=0.0,
    step=10000.0,
    format="%.0f"
)

# 8) คำนวณเงินสดสะสม
df_merged['เงินสดสะสม'] = df_merged['net_cash'].cumsum() + cash_accum

# 9) แปลงวันที่เป็น datetime และตั้ง index
df_merged['วันที่'] = pd.to_datetime(df_merged['วันที่'])
df_merged = df_merged.set_index('วันที่')

# 10) เปลี่ยนชื่อคอลัมน์เป็นภาษาไทย
df_merged = df_merged.rename(columns={
    'cash_in': 'กระแสเงินสดรับ',
    'cash_out': 'กระแสเงินสดจ่าย',
    'net_cash': 'กระแสเงินสดสุทธิ'
})


today = end_date
# สร้างสองซีรีส์: สะสมจริง (ก่อนหรือเท่ากับ today) กับ คาดการณ์ (หลัง today)
df_merged['สะสมจริง'] = df_merged['เงินสดสะสม'].where(df_merged.index <= today)
df_merged['สะสมคาดการณ์'] = df_merged['เงินสดสะสม'].where(df_merged.index > today)

# วาดกราฟ 2 เส้นพร้อมกัน
# สร้าง Figure
fig = go.Figure()

# เพิ่มแท่ง risk_pct บนแกนขวา
fig.add_trace(
    go.Bar(
        x=df_merged.index,
        y=df_merged['risk_pct'],
        name='Risk %',
        yaxis='y2',
        opacity=0.4
    )
)

# เพิ่มเส้นสะสมจริง
fig.add_trace(
    go.Scatter(
        x=df_merged.index,
        y=df_merged['สะสมจริง'],
        mode='lines',
        name='สะสมจริง'
    )
)

# เพิ่มเส้นสะสมคาดการณ์
fig.add_trace(
    go.Scatter(
        x=df_merged.index,
        y=df_merged['สะสมคาดการณ์'],
        mode='lines',
        name='สะสมคาดการณ์'
    )
)

# ปรับ layout ให้มีแกนซ้าย-ขวา
# ตั้งค่า layout พร้อมกำหนดช่วงแกน yaxis2
fig.update_layout(
    title='Cashflow Cumulative vs. Risk %',
    xaxis=dict(
        title='Date',
        showgrid=False,        # ปิดเส้นกริดแกน X
        zeroline=False         # ปิดเส้นศูนย์ตรงกลาง
    ),
    yaxis=dict(
        title='Cumulative Cash',
        showgrid=False,
        zeroline=False
    ),
    yaxis2=dict(
        title='Risk %',
        overlaying='y',
        side='right',
        range=[70, 100],
        showgrid=False,
        zeroline=False
    )
)

# แสดงใน Streamlit
st.plotly_chart(fig, use_container_width=True)

# 11) แสดงตารางคอลัมน์สำคัญ

df_from_today = df_merged.loc[df_merged.index >= today, [
    'กระแสเงินสดรับ',
    'กระแสเงินสดจ่าย',
    'กระแสเงินสดสุทธิ',
    'เงินสดสะสม',
    'risk_pct'
]]

st.subheader('สรุปกระแสเงินสดรายวัน (ตั้งแต่วันนี้)')
st.dataframe(df_from_today)
###############################################################################################################################

st.title('วางแผนการจ่าย')

threshold = st.number_input(
    'กรุณาใส่ค่า threshold (จำนวนเงินขั้นต่ำ):',
    min_value=0.0,
    value=0.0,
    step=100_000.0,
    format="%.0f"
)

# ——————————————————————
# เตรียม df_merged ให้เริ่มต้นตั้งแต่ today
df_merged = df_merged.loc[df_merged.index >= today].copy()

# หาค่าเงินสดสะสม ณ วันนี้ (ใช้เป็นจุดเริ่มต้นของ cash_accum)
cash_accum_today = df_merged['เงินสดสะสม'].iloc[0]

# 1) เตรียม DataFrame เจ้าหนี้ (cash out) เฉพาะตั้งแต่วันนี้
df_cashout = (
    df.loc[
        (pd.to_datetime(df['วันที่จะได้รับ/จ่าย']) >= today) &
        (df['จำนวนเงิน'] < 0)
    ]
    [['วันที่จะได้รับ/จ่าย', 'ชื่อ', 'จำนวนเงิน']]
    .copy()
)
df_cashout.columns = ['วันที่', 'ชื่อเจ้าหนี้', 'จำนวนเงิน']
df_cashout['วันที่'] = pd.to_datetime(df_cashout['วันที่'])

# 2) Merge กับ df_merged (index เป็นวันที่)
df_cashout = (
    df_cashout
    .merge(
        df_merged[['เงินสดสะสม']],
        left_on='วันที่',
        right_index=True,
        how='left'
    )
    .sort_values('วันที่')
)

# 3) วางแผนเลื่อนชำระ
payment_plan = []
for _, row in df_cashout.iterrows():
    orig_date = row['วันที่']
    creditor  = row['ชื่อเจ้าหนี้']
    amount    = row['จำนวนเงิน']
    cash      = row['เงินสดสะสม']

    if cash < threshold:
        pos = df_merged.index.get_loc(orig_date)
        j = pos + 1
        while j < len(df_merged) and df_merged.iloc[j]['เงินสดสะสม'] < threshold:
            j += 1
        if j < len(df_merged):
            new_date = df_merged.index[j]
            payment_plan.append({
                'ชื่อเจ้าหนี้': creditor,
                'วันที่เดิม':       orig_date,
                'วันที่จ่ายใหม่':  new_date,
                'จำนวนเงินที่เลื่อน': amount
            })

df_payment_plan = pd.DataFrame(payment_plan)

# 4) แสดงแผนเลื่อนชำระ
st.subheader('สรุปแผนเลื่อนชำระ (ตั้งแต่วันนี้)')
st.write(df_payment_plan)

# 5) ปรับ cashflow ตามแผน
df_adjusted = df_merged[['กระแสเงินสดสุทธิ']].copy()
for _, row in df_payment_plan.iterrows():
    orig = row['วันที่เดิม']
    new  = row['วันที่จ่ายใหม่']
    amt  = row['จำนวนเงินที่เลื่อน']
    df_adjusted.loc[orig, 'กระแสเงินสดสุทธิ'] -= amt
    df_adjusted.loc[new, 'กระแสเงินสดสุทธิ']  += amt


# 6) คำนวณผลต่างระหว่าง net cashflow ที่ปรับ กับ net cashflow ดั้งเดิม
delta = df_adjusted['กระแสเงินสดสุทธิ'] - df_merged['กระแสเงินสดสุทธิ']

# 7) สะสม delta ทีละวัน (delta.cumsum()) แล้วบวกกับเงินสดสะสมของเดิม
df_adjusted['เงินสดสะสม_adjusted'] = (
    df_merged['เงินสดสะสม']  # baseline เดิม
    + delta.cumsum()
)

# 8) เปรียบเทียบกราฟ ก่อน–หลัง
st.subheader('เปรียบเทียบเงินสดสะสม ก่อน–หลังเลื่อนชำระ (เริ่มตั้งแต่วันนี้)')
df_compare = pd.DataFrame({
    'ก่อนเลื่อน':  df_merged['เงินสดสะสม'],
    'หลังเลื่อน': df_adjusted['เงินสดสะสม_adjusted']
})
st.line_chart(df_compare)