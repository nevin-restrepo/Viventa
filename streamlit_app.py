import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------
# CONFIGURACIÓN BÁSICA
# ---------------------------------------------------
st.set_page_config(page_title="Dashboard & Simulador Viventa", layout="wide")

# Constantes generales
TASA_USD = 3800.0   # para histórico y simulador
TASA_EUR = 4424.0
TARIFA_SV_USD = 400.0  # valor estándar de una SV en el simulador


# ---------------------------------------------------
# CARGA DE DATOS HISTÓRICOS (DASHBOARD)
# ---------------------------------------------------
@st.cache_data
def load_data():
    """Carga el CSV histórico en COP para el dashboard."""
    df = pd.read_csv("data/datos.csv")

    # Columnas numéricas en COP
    num_cols = ["SV_Comision", "VC_Comision", "Trimestral", "Salario"]
    for col in num_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ---------------------------------------------------
# FUNCIONES COMUNES DE MONEDA
# ---------------------------------------------------
def convertir_desde_cop(valor_cop, moneda):
    """Convierte un valor en COP a la moneda seleccionada."""
    if moneda == "COP":
        return valor_cop
    elif moneda == "USD":
        return valor_cop / TASA_USD
    elif moneda == "EUR":
        return valor_cop / TASA_EUR
    return valor_cop


def formato_moneda(valor, moneda):
    """Devuelve un string formateado con la moneda."""
    if moneda == "COP":
        return f"${valor:,.0f} COP"
    else:
        return f"${valor:,.0f} {moneda}"


# ---------------------------------------------------
# MÓDULO 1: DASHBOARD HISTÓRICO
# ---------------------------------------------------
def build_dashboard():
    df = load_data()

    st.subheader("Dashboard histórico de compensación")

    # --- Filtros en sidebar ---
    moneda = st.sidebar.radio(
        "Moneda de visualización (histórico)",
        ["COP", "USD", "EUR"],
        index=0,
        key="db_moneda",
    )

    años = sorted(df["Año"].unique())
    año_sel = st.sidebar.selectbox("Año", años, key="db_ano")

    meses = sorted(df[df["Año"] == año_sel]["Mes"].unique())
    mes_ini, mes_fin = st.sidebar.select_slider(
        "Rango de meses (histórico)",
        options=meses,
        value=(min(meses), max(meses)),
        key="db_rango_meses",
    )

    df_filt = df[(df["Año"] == año_sel) & (df["Mes"].between(mes_ini, mes_fin))].copy()
    df_filt = df_filt.sort_values("Mes")

    if df_filt.empty:
        st.warning("No hay datos para el rango seleccionado.")
        return

    st.caption(
        f"Mostrando histórico en **{moneda}**. Meses: {mes_ini}–{mes_fin}. "
        f"(TRM fija: USD = {TASA_USD:,.0f} COP, EUR = {TASA_EUR:,.0f} COP)."
    )

    # --- KPIs acumulados ---
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

    # --- Data para gráficos ---
    df_plot = df_filt.copy()
    df_plot["SV_Comision_conv"] = df_plot["SV_Comision"].apply(
        lambda v: convertir_desde_cop(v, moneda)
    )
    df_plot["VC_Comision_conv"] = df_plot["VC_Comision"].apply(
        lambda v: convertir_desde_cop(v, moneda)
    )

    colA, colB = st.columns(2)

    with colA:
        st.subheader("Servicio Viventa – Unidades por mes")
        fig_sv_u = px.bar(
            df_plot,
            x="NombreMes",
            y="SV_Unidades",
            text="SV_Unidades",
            labels={"NombreMes": "Mes", "SV_Unidades": "Unidades"},
        )
        st.plotly_chart(fig_sv_u, use_container_width=True, key="db_sv_units")

        st.subheader(f"Servicio Viventa – Comisión por mes ({moneda})")
        fig_sv_c = px.line(
            df_plot,
            x="NombreMes",
            y="SV_Comision_conv",
            markers=True,
            labels={"NombreMes": "Mes", "SV_Comision_conv": f"Comisión ({moneda})"},
        )
        st.plotly_chart(fig_sv_c, use_container_width=True, key="db_sv_comision")

    with colB:
        st.subheader("Vivecasa – Unidades por mes")
        fig_vc_u = px.bar(
            df_plot,
            x="NombreMes",
            y="VC_Unidades",
            text="VC_Unidades",
            labels={"NombreMes": "Mes", "VC_Unidades": "Unidades"},
        )
        st.plotly_chart(fig_vc_u, use_container_width=True, key="db_vc_units")

        st.subheader(f"Vivecasa – Comisión por mes ({moneda})")
        fig_vc_c = px.line(
            df_plot,
            x="NombreMes",
            y="VC_Comision_conv",
            markers=True,
            labels={"NombreMes": "Mes", "VC_Comision_conv": f"Comisión ({moneda})"},
        )
        st.plotly_chart(fig_vc_c, use_container_width=True, key="db_vc_comision")

    st.markdown("### Detalle filtrado (valores originales en COP)")
    st.dataframe(df_filt)


# ---------------------------------------------------
# MÓDULO 2: SIMULADOR VIVENTA 2025
# ---------------------------------------------------

# Tramos SV:
# 0–8 SV   -> 0%
# 9–11 SV  -> 8%
# 12–16 SV -> 18%
# 17+ SV   -> 25%

def get_pct_sv(num_sv: int) -> float:
    if num_sv <= 8:
        return 0.0
    elif num_sv <= 11:
        return 0.08
    elif num_sv <= 16:
        return 0.18
    else:
        return 0.25


def calcular_comision_sv(num_sv: int, descuento: float, trm: float):
    """
    Calcula la comisión total de SV en COP con:
    - Tarifa estándar SV: 400 USD (TARIFA_SV_USD)
    - descuento: 0.0 a 0.5
    - trm: COP por USD

    Fórmula:
    comision_por_sv = (tarifa_neta_usd * trm) * pct_según_tramo
    comision_total = comision_por_sv * num_sv
    """
    pct = get_pct_sv(num_sv)
    valor_sv_neto_usd = TARIFA_SV_USD * (1.0 - descuento)
    valor_sv_neto_cop = valor_sv_neto_usd * trm

    comision_por_sv_cop = valor_sv_neto_cop * pct
    comision_total = comision_por_sv_cop * num_sv

    return comision_total, pct, valor_sv_neto_cop, comision_por_sv_cop


def calcular_comision_vivecasa(
    num_vivecasas: int,
    tipo_esquema: str,
    comision_fija_cop=None,
    tarifa_vivecasa_cop=None,
    pct_vivecasa=None,
):
    if num_vivecasas <= 0:
        return 0.0

    if tipo_esquema == "Fija por unidad (COP)":
        return num_vivecasas * (comision_fija_cop or 0.0)

    tarifa_vivecasa_cop = tarifa_vivecasa_cop or 0.0
    pct_vivecasa = pct_vivecasa or 0.0
    return num_vivecasas * tarifa_vivecasa_cop * pct_vivecasa


def build_simulador():
    st.subheader("Simulador de compensación comercial Viventa 2025")

    st.write(
        """
        Tarifa estándar SV: **400 USD**  
        TRM usada en la simulación: **3.800 COP/USD**  
        La comisión SV depende del número total de SV facturados.
        """
    )

    # -------- ENTRADAS ----------
    st.sidebar.markdown("---")
    st.sidebar.subheader("Parámetros del simulador")

    num_sv = st.sidebar.number_input(
        "SV facturados",
        min_value=0,
        max_value=200,
        value=10,
        step=1,
        key="num_sv",
    )

    descuento = st.sidebar.slider(
        "Descuento promedio SV (%)",
        min_value=0.0,
        max_value=0.50,
        value=0.0,
        step=0.01,
        key="desc_sv",
    )

    num_vivecasas = st.sidebar.number_input(
        "Vivecasas cerradas",
        min_value=0,
        max_value=200,
        value=5,
        step=1,
        key="num_vc",
    )

    tipo_esquema_vc = st.sidebar.selectbox(
        "Esquema Vivecasa",
        ["Fija por unidad (COP)", "% sobre tarifa (COP)"],
        key="tipo_vc",
    )

    comision_fija_cop = None
    tarifa_vivecasa_cop = None
    pct_vivecasa = None

    if tipo_esquema_vc == "Fija por unidad (COP)":
        comision_fija_cop = st.sidebar.number_input(
            "Comisión fija por Vivecasa (COP)",
            min_value=0.0,
            value=2_000_000.0,
            step=100_000.0,
            key="vc_fija",
        )
    else:
        tarifa_vivecasa_cop = st.sidebar.number_input(
            "Tarifa promedio Vivecasa (COP)",
            min_value=5_000_000.0,
            value=15_000_000.0,
            step=500_000.0,
            key="vc_tarifa",
        )
        pct_vivecasa = st.sidebar.slider(
            "% comisión Vivecasa",
            min_value=0.0,
            max_value=0.20,
            value=0.05,
            step=0.01,
            key="vc_pct",
        )

    fijo_mensual = st.sidebar.number_input(
        "Fijo mensual (COP)",
        min_value=0.0,
        value=4_000_000.0,
        step=100_000.0,
        key="fijo",
    )
    bono_mensual = st.sidebar.number_input(
        "Bono mensual (COP)",
        min_value=0.0,
        value=500_000.0,
        step=50_000.0,
        key="bono",
    )

    # -------- CÁLCULOS ----------
    com_sv_total, pct_sv, valor_sv_neto_cop, comision_por_sv = calcular_comision_sv(
        num_sv=num_sv,
        descuento=descuento,
        trm=TASA_USD,   # 3.800
    )

    com_vc_total = calcular_comision_vivecasa(
        num_vivecasas=num_vivecasas,
        tipo_esquema=tipo_esquema_vc,
        comision_fija_cop=comision_fija_cop,
        tarifa_vivecasa_cop=tarifa_vivecasa_cop,
        pct_vivecasa=pct_vivecasa,
    )

    total_variable = com_sv_total + com_vc_total
    total_mensual = fijo_mensual + bono_mensual + total_variable

    # -------- MÉTRICAS ----------
    st.markdown("### Resultado mensual simulado")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Fijo", f"${fijo_mensual:,.0f}")
    m2.metric("Bono", f"${bono_mensual:,.0f}")
    m3.metric("Var. SV", f"${com_sv_total:,.0f}")
    m4.metric("Var. Vivecasas", f"${com_vc_total:,.0f}")
    m5.metric("Total mensual", f"${total_mensual:,.0f}")

    # -------- TABLA DETALLE ----------
    st.markdown("### Detalle de cálculo")

    detalle = pd.DataFrame({
        "Concepto": [
            "SV facturados",
            "% comisión SV según tramo",
            "Tarifa neta por SV (COP)",
            "Comisión por SV (COP)",
            "Comisión total SV (COP)",
            "Vivecasas cerradas",
            "Comisión total Vivecasa (COP)",
            "Fijo (COP)",
            "Bono (COP)",
            "Total Variable (COP)",
            "Total Mensual (COP)",
        ],
        "Valor": [
            num_sv,
            f"{pct_sv * 100:.1f} %",
            f"{valor_sv_neto_cop:,.0f}",
            f"{comision_por_sv:,.0f}",
            f"{com_sv_total:,.0f}",
            num_vivecasas,
            f"{com_vc_total:,.0f}",
            f"{fijo_mensual:,.0f}",
            f"{bono_mensual:,.0f}",
            f"{total_variable:,.0f}",
            f"{total_mensual:,.0f}",
        ],
    })
    st.table(detalle)

    # -------- GRÁFICO ----------
    st.markdown("### Fijo vs Variable")

    barras = pd.DataFrame({
        "Componente": ["Fijo", "Variable SV", "Variable VC"],
        "Valor": [fijo_mensual, com_sv_total, com_vc_total],
    })

    fig = px.bar(
        barras,
        x="Componente",
        y="Valor",
        text="Valor",
        labels={"Valor": "Valor (COP)"},
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    st.title("Viventa – Dashboard & Simulador de Compensación 2025")

    modo = st.sidebar.radio(
        "¿Qué quieres usar?",
        ["Dashboard histórico", "Simulador 2025"],
        index=0,
        key="modo_app",
    )

    if modo == "Dashboard histórico":
        build_dashboard()
    else:
        build_simulador()


if __name__ == "__main__":
    main()
