import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------
# Configuración básica
# ----------------------------------
st.set_page_config(page_title="Dashboard Compensación", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("data/datos.csv")

    # Convertir valores numéricos si vienen con puntos
    num_cols = ["SV_Comision", "VC_Comision", "Trimestral", "Salario"]
    for col in num_cols:
        df[col] = (
            df[col].astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# ----------------------------------
# Título
# ----------------------------------
st.title("Dashboard Plan de Compensación – Especialista de Crédito")

# ----------------------------------
# Filtros
# ----------------------------------
st.sidebar.header("Filtros")

años = sorted(df["Año"].unique())
año_sel = st.sidebar.selectbox("Año", años)

meses = df[df["Año"] == año_sel]["Mes"].unique()
mes_ini, mes_fin = st.sidebar.select_slider(
    "Rango de meses",
    options=sorted(meses),
    value=(min(meses), max(meses))
)

df_filt = df[(df["Año"] == año_sel) & (df["Mes"].between(mes_ini, mes_fin))]

# ----------------------------------
# KPIs
# ----------------------------------
total_sv_unid = df_filt["SV_Unidades"].sum()
total_sv_com = df_filt["SV_Comision"].sum()
total_vc_unid = df_filt["VC_Unidades"].sum()
total_vc_com = df_filt["VC_Comision"].sum()
total_tri = df_filt["Trimestral"].sum()
total_var = total_sv_com + total_vc_com + total_tri

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("SV Unidades", total_sv_unid)
col2.metric("SV Comisión", f"${total_sv_com:,.0f}")
col3.metric("VC Unidades", total_vc_unid)
col4.metric("VC Comisión", f"${total_vc_com:,.0f}")
col5.metric("Variable total", f"${total_var:,.0f}")

st.markdown("---")

# ----------------------------------
# Gráficos
# ----------------------------------
colA, colB = st.columns(2)

with colA:
    st.subheader("Servicio Viventa – Unidades por mes")
    fig1 = px.bar(df_filt, x="NombreMes", y="SV_Unidades", text="SV_Unidades")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Servicio Viventa – Comisión por mes")
    fig2 = px.line(df_filt, x="NombreMes", y="SV_Comision", markers=True)
    st.plotly_chart(fig2, use_container_width=True)

with colB:
    st.subheader("Vivecasa – Unidades por mes")
    fig3 = px.bar(df_filt, x="NombreMes", y="VC_Unidades", text="VC_Unidades")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Vivecasa – Comisión por mes")
    fig4 = px.line(df_filt, x="NombreMes", y="VC_Comision", markers=True)
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("### Detalle filtrado")
st.dataframe(df_filt)
