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
# Sidebar: filtros
# ----------------------------------
st.sidebar.header("Filtros")

# Moneda de visualización
moneda = st.sidebar.radio(
    "Moneda de visualización",
    ["COP", "USD", "EUR"],
    index=0,
)

# Tasas fijas
TASA_USD = 3800.0
TASA_EUR = 4424.0

def convertir_desde_cop(valor_cop: float, moneda: str) -> float:
    if moneda == "COP":
        return valor_cop
    elif moneda == "USD":
        return valor_cop / TASA_USD
    elif moneda == "EUR":
        return valor_cop / TASA_EUR
    return valor_cop

def formato_moneda(valor: float, moneda: str) -> str:
    if moneda == "COP":
        return f"${valor:,.0f} COP"
    else:
        return f"${valor:,.0f} {moneda}"

# Filtro de año y rango de meses
años = sorted(df["Año"].unique())
año_sel = st.sidebar.selectbox("Año", años)

meses = sorted(df[df["Año"] == año_sel]["Mes"].unique())
mes_ini, mes_fin = st.sidebar.select_slider(
    "Rango de meses",
    options=meses,
    value=(min(meses), max(meses)),
)

# Data filtrada por año y meses
df_filt = df[(df["Año"] == año_sel) & (df["Mes"].between(mes_ini, mes_fin))].copy()

# ----------------------------------
# Título
# ----------------------------------
st.title("Dashboard Plan de Compensación – Especialista de Crédito")
st.caption(
    f"Datos originales en COP. Valores mostrados en **{moneda}** "
    f"(USD=3.800 COP, EUR=4.424 COP). Meses: {mes_ini}–{mes_fin}."
)

# ----------------------------------
# KPIs ACUMULADOS
# ----------------------------------
total_sv_unid = df_filt["SV_Unidades"].sum()
total_sv_com_cop = df_filt["SV_Comision"].sum()
total_vc_unid = df_filt["VC_Unidades"].sum()
total_vc_com_cop = df_filt["VC_Comision"].sum()
total_tri_cop = df_filt["Trimestral"].sum()
total_var_cop = total_sv_com_cop + total_vc_com_cop + total_tri_cop

total_sv_com = convertir_desde_cop(total_sv_com_cop, moneda)
total_vc_com = convertir_desde_cop(total_vc_com_cop, moneda)
total_tri = convertir_desde_cop(total_tri_cop, moneda)
total_var = convertir_desde_cop(total_var_cop, moneda)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("SV Unidades (acum.)", int(total_sv_unid))
c2.metric("SV Comisión (acum.)", formato_moneda(total_sv_com, moneda))
c3.metric("VC Unidades (acum.)", int(total_vc_unid))
c4.metric("VC Comisión (acum.)", formato_moneda(total_vc_com, moneda))
c5.metric("Variable total (acum.)", formato_moneda(total_var, moneda))

st.markdown("---")

# ----------------------------------
# Data para gráficos (comisiones convertidas)
# ----------------------------------
df_plot = df_filt.copy()
df_plot["SV_Comision_conv"] = df_plot["SV_Comision"].apply(
    lambda v: convertir_desde_cop(v, moneda)
)
df_plot["VC_Comision_conv"] = df_plot["VC_Comision"].apply(
    lambda v: convertir_desde_cop(v, moneda)
)

# ----------------------------------
# Gráficos (cada uno con key distinta)
# ----------------------------------
colA, colB = st.columns(2)

with colA:
    st.subheader("Servicio Viventa – Unidades por mes")
    fig1 = px.bar(
        df_plot,
        x="NombreMes",
        y="SV_Unidades",
        text="SV_Unidades",
        labels={"NombreMes": "Mes", "SV_Unidades": "Unidades"},
    )
    st.plotly_chart(fig1, use_container_width=True, key="sv_units")

    st.subheader(f"Servicio Viventa – Comisión por mes ({moneda})")
    fig2 = px.line(
        df_plot,
        x="NombreMes",
        y="SV_Comision_conv",
        markers=True,
        labels={"NombreMes": "Mes", "SV_Comision_conv": f"Comisión ({moneda})"},
    )
    st.plotly_chart(fig2, use_container_width=True, key="sv_comision")

with colB:
    st.subheader("Vivecasa – Unidades por mes")
    fig3 = px.bar(
        df_plot,
        x="NombreMes",
        y="VC_Unidades",
        text="VC_Unidades",
        labels={"NombreMes": "Mes", "VC_Unidades": "Unidades"},
    )
    st.plotly_chart(fig3, use_container_width=True, key="vc_units")

    st.subheader(f"Vivecasa – Comisión por mes ({moneda})")
    fig4 = px.line(
        df_plot,
        x="NombreMes",
        y="VC_Comision_conv",
        markers=True,
        labels={"NombreMes": "Mes", "VC_Comision_conv": f"Comisión ({moneda})"},
    )
    st.plotly_chart(fig4, use_container_width=True, key="vc_comision")

st.markdown("### Detalle filtrado (valores originales en COP)")
st.dataframe(df_filt)
