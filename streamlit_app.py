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
# Sidebar: filtros generales
# ----------------------------------
st.sidebar.header("Filtros")

# 🔹 Filtro de moneda
moneda = st.sidebar.selectbox(
    "Moneda de visualización",
    ["COP", "USD", "EUR"]
)

# Tasas de cambio (COP por 1 USD / COP por 1 EUR)
st.sidebar.markdown("### Tasas de cambio (COP por unidad)")
tasa_usd = st.sidebar.number_input(
    "1 USD = cuántos COP",
    min_value=0.0001,
    value=4000.0,
    step=100.0
)
tasa_eur = st.sidebar.number_input(
    "1 EUR = cuántos COP",
    min_value=0.0001,
    value=4300.0,
    step=100.0
)

def convertir_desde_cop(valor_cop: float, moneda: str) -> float:
    """Convierte un valor en COP a la moneda seleccionada."""
    if moneda == "COP":
        return valor_cop
    elif moneda == "USD":
        return valor_cop / tasa_usd
    elif moneda == "EUR":
        return valor_cop / tasa_eur
    return valor_cop

def formato_moneda(valor: float, moneda: str) -> str:
    """Devuelve un string formateado con la moneda."""
    if moneda == "COP":
        return f"${valor:,.0f} COP"
    else:
        return f"${valor:,.0f} {moneda}"

# 🔹 Filtros de año y meses
años = sorted(df["Año"].unique())
año_sel = st.sidebar.selectbox("Año", años)

meses = sorted(df[df["Año"] == año_sel]["Mes"].unique())
mes_ini, mes_fin = st.sidebar.select_slider(
    "Rango de meses",
    options=meses,
    value=(min(meses), max(meses))
)

df_filt = df[(df["Año"] == año_sel) & (df["Mes"].between(mes_ini, mes_fin))]

# ----------------------------------
# Título
# ----------------------------------
st.title("Dashboard Plan de Compensación – Especialista de Crédito")
st.caption(f"Mostrando valores en **{moneda}** (tasas configurables en la barra lateral)")

# ----------------------------------
# KPIs (convertidos a la moneda seleccionada)
# ----------------------------------
total_sv_unid = df_filt["SV_Unidades"].sum()
total_sv_com_cop = df_filt["SV_Comision"].sum()
total_vc_unid = df_filt["VC_Unidades"].sum()
total_vc_com_cop = df_filt["VC_Comision"].sum()
total_tri_cop = df_filt["Trimestral"].sum()
total_var_cop = total_sv_com_cop + total_vc_com_cop + total_tri_cop

# Conversión a la moneda elegida
total_sv_com = convertir_desde_cop(total_sv_com_cop, moneda)
total_vc_com = convertir_desde_cop(total_vc_com_cop, moneda)
total_tri = convertir_desde_cop(total_tri_cop, moneda)
total_var = convertir_desde_cop(total_var_cop, moneda)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("SV Unidades", int(total_sv_unid))
col2.metric("SV Comisión", formato_moneda(total_sv_com, moneda))
col3.metric("VC Unidades", int(total_vc_unid))
col4.metric("VC Comisión", formato_moneda(total_vc_com, moneda))
col5.metric("Variable total", formato_moneda(total_var, moneda))

st.markdown("---")

# ----------------------------------
# Preparar dataframe convertido para gráficos
# ----------------------------------
df_plot = df_filt.copy()
for col in ["SV_Comision", "VC_Comision"]:
    df_plot[col + "_conv"] = df_plot[col].apply(
        lambda v: convertir_desde_cop(v, moneda)
    )

# ----------------------------------
# Gráficos
# ----------------------------------
colA, colB = st.columns(2)

with colA:
    st.subheader("Servicio Viventa – Unidades por mes")
    fig1 = px.bar(df_plot, x="NombreMes", y="SV_Unidades", text="SV_Unidades",
                  labels={"NombreMes": "Mes", "SV_Unidades": "Unidades"})
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f"Servicio Viventa – Comisión por mes ({moneda})")
    fig2 = px.line(
        df_plot,
        x="NombreMes",
        y="SV_Comision_conv",
        markers=True,
        labels={"NombreMes": "Mes", "SV_Comision_conv": f"Comisión ({moneda})"}
    )
    st.plotly_chart(fig2, use_container_width=True)

with colB:
    st.subheader("Vivecasa – Unidades por mes")
    fig3 = px.bar(df_plot, x="NombreMes", y="VC_Unidades", text="VC_Unidades",
                  labels={"NombreMes": "Mes", "VC_Unidades": "Unidades"})
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader(f"Vivecasa – Comisión por mes ({moneda})")
    fig4 = px.line(
        df_plot,
        x="NombreMes",
        y="VC_Comision_conv",
        markers=True,
        labels={"NombreMes": "Mes", "VC_Comision_conv": f"Comisión ({moneda})"}
    )
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("### Detalle filtrado (valores monetarios en COP originales)")
st.dataframe(df_filt)
