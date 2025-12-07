import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------
# Configuración básica de la página
# ----------------------------------
st.set_page_config(
    page_title="Dashboard Plan de Compensación",
    layout="wide"
)

# ----------------------------------
# Función para cargar y limpiar datos
# ----------------------------------
@st.cache_data
def load_data():
    # Leemos el CSV dentro de la carpeta data
    df = pd.read_csv("data/datos.csv")

    # Normalizar nombres de meses a minúscula y crear número de mes
    mes_map = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    df["Mes_clean"] = df["Mes"].astype(str).str.strip().str.lower()
    df["Mes_num"] = df["Mes_clean"].map(mes_map)

    # Orden correcto para mostrar en gráficos
    orden_meses = list(mes_map.keys())
    df["Mes_clean"] = pd.Categorical(df["Mes_clean"], categories=orden_meses, ordered=True)

    # Función para convertir texto tipo "1.094.400" -> 1094400
    def to_number(col):
        return (
            pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", "", regex=False),
                errors="coerce"
            )
            .fillna(0)
        )

    # Convertir columnas de dinero a número
    df["Comision SV"] = to_number("Comision SV")
    df["Vivecasas"] = to_number("Vivecasas")
    df["Salario"] = to_number("Salario")
    df["Trimestral"] = to_number("Trimestral")   # bono trimestral

    return df

df = load_data()

# ----------------------------------
# Título
# ----------------------------------
st.title("Dashboard Plan de Compensación – Especialista de Crédito")

st.markdown(
    "Dashboard de **unidades y compensación variable** por Servicio Viventa y Vivecasa, "
    "incluyendo el **bono trimestral**, filtrado por año, rango de meses y comercial."
)

# ----------------------------------
# SIDEBAR: filtros
# ----------------------------------
st.sidebar.header("Filtros")

comerciales = ["Todos"] + sorted(df["Comercial"].unique().tolist())
com_sel = st.sidebar.selectbox("Comercial", comerciales)

años = sorted(df["Año"].unique())
año_sel = st.sidebar.selectbox("Año", años)

df_filt = df[df["Año"] == año_sel].copy()
if com_sel != "Todos":
    df_filt = df_filt[df_filt["Comercial"] == com_sel]

mes_min = int(df_filt["Mes_num"].min())
mes_max = int(df_filt["Mes_num"].max())

rango_meses = st.sidebar.slider(
    "Rango de meses",
    mes_min,
    mes_max,
    (mes_min, mes_max)
)

mes_ini, mes_fin = rango_meses
df_filt = df_filt[(df_filt["Mes_num"] >= mes_ini) & (df_filt["Mes_num"] <= mes_fin)]
df_filt = df_filt.sort_values("Mes_num")

# ----------------------------------
# KPIs
# ----------------------------------
total_sv_unid = df_filt["SV facturado"].sum()
total_sv_com = df_filt["Comision SV"].sum()
total_vc_com = df_filt["Vivecasas"].sum()
total_tri = df_filt["Trimestral"].sum()
total_var = total_sv_com + total_vc_com + total_tri
salario_prom = df_filt["Salario"].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Unidades Viventa", total_sv_unid)
col2.metric("Comisión SV", f"${total_sv_com:,.0f}")
col3.metric("Comisión Vivecasa", f"${total_vc_com:,.0f}")
col4.metric("Bono Trimestral", f"${total_tri:,.0f}")
col5.metric("Total Variable", f"${total_var:,.0f}")

st.markdown("---")

# ----------------------------------
# GRÁFICOS
# ----------------------------------
if df_filt.empty:
    st.warning("No hay datos para los filtros seleccionados.")
else:
    colA, colB = st.columns(2)

    with colA:
        st.subheader("Servicio Viventa – Unidades por mes")
        fig1 = px.bar(df_filt, x="Mes_clean", y="SV facturado", text="SV facturado")
        st.plotly_chart(fig1, use_container_width=True)

    with colA:
        st.subheader("Servicio Viventa – Comisión")
        fig2 = px.line(df_filt, x="Mes_clean", y="Comision SV", markers=True)
        st.plotly_chart(fig2, use_container_width=True)

    with colB:
        st.subheader("Vivecasa – Comisión")
        fig3 = px.bar(df_filt, x="Mes_clean", y="Vivecasas", text="Vivecasas")
        st.plotly_chart(fig3, use_container_width=True)

    with colB:
        st.subheader("Bono Trimestral por Mes")
        fig4 = px.bar(df_filt, x="Mes_clean", y="Trimestral", text="Trimestral")
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("### Detalle de los datos filtrados")
    st.dataframe(df_filt)
