import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Hoja1", layout="wide")

FILE_PATH = "data/HdePagos.xlsx"

MONEY_COLS = [
    "Total Salario Basico USD",
    "Total PPSS Salario Basico USD",
    "Total Prestaciones Sociales USD",
    "Total Comisiones Vivecasa USD",
    "Total Comisiones Viveprestamo USD",
    "Total Bonos y Premios USD",
    "Total Total Nomina USD",
]

DIM_COLS = ["Periodo", "Empleador", "Nick Name", "Cargo", "Total Activos"]

# -------------------------
# PARSEO PERIODO (January 2024 -> fecha)
# -------------------------
MONTH_MAP_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}
MONTH_MAP_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def parse_periodo_to_date(s: str):
    """
    Convierte 'January 2024' / 'Enero 2024' a Timestamp del 1er día del mes.
    Si ya es fecha (2024-01-01 o similar), también lo parsea.
    """
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return pd.NaT
    txt = str(s).strip()

    # 1) Intento directo (por si viene como fecha o '2024-01')
    dt = pd.to_datetime(txt, errors="coerce")
    if not pd.isna(dt):
        return pd.Timestamp(dt.year, dt.month, 1)

    # 2) Formato "Mes Año"
    parts = txt.replace("-", " ").replace("/", " ").split()
    if len(parts) >= 2:
        mes = parts[0].lower()
        anio = parts[1]
        try:
            y = int(anio)
        except Exception:
            return pd.NaT

        m = MONTH_MAP_EN.get(mes) or MONTH_MAP_ES.get(mes)
        if m:
            return pd.Timestamp(y, m, 1)

    return pd.NaT


def fmt_usd(x: float) -> str:
    return f"${x:,.2f} USD"


# -------------------------
# CARGA + LIMPIEZA
# -------------------------
@st.cache_data
def load_nomina():
    df = pd.read_excel(FILE_PATH)  # requiere openpyxl instalado

    df.columns = [c.strip() for c in df.columns]
    df = df.replace(r"^\s*$", np.nan, regex=True)

    # Limpia dimensiones
    for c in ["Periodo", "Empleador", "Nick Name", "Cargo"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # Parse Periodo a fecha para ordenar y filtrar por rango
    if "Periodo" in df.columns:
        df["Periodo_dt"] = df["Periodo"].apply(parse_periodo_to_date)
    else:
        df["Periodo_dt"] = pd.NaT

    # Convierte numéricos
    for c in MONEY_COLS + ["Total Activos"]:
        if c in df.columns:
            df[c] = (
                df[c]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .replace("nan", np.nan)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df


# -------------------------
# APP
# -------------------------
def build_historico_nomina():
    df = load_nomina()

    required = {"Periodo", "Empleador", "Nick Name", "Cargo", "Total Total Nomina USD"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"Faltan columnas requeridas: {missing}")
        return

    st.title("Histórico de pagos (USD)")
    st.subheader("Consulta por Cargo → Persona")

    # ---- Filtros ----
    st.sidebar.subheader("Filtros")

    cargos = sorted(df["Cargo"].dropna().unique())
    cargo_sel = st.sidebar.selectbox("Cargo", cargos, key="cargo_sel")

    df_c = df[df["Cargo"] == cargo_sel].copy()

    personas = sorted(df_c["Nick Name"].dropna().unique())
    persona_sel = st.sidebar.selectbox("Nick Name", personas, key="persona_sel")

    df_p = df_c[df_c["Nick Name"] == persona_sel].copy()

    # (Opcional) empleador
    empleadores = sorted(df_p["Empleador"].dropna().unique())
    if len(empleadores) > 1:
        emp_sel = st.sidebar.multiselect(
            "Empleador", empleadores, default=empleadores, key="emp_sel"
        )
        df_p = df_p[df_p["Empleador"].isin(emp_sel)].copy()

    # ---- Filtro por rango de periodos (ordenado por Periodo_dt) ----
    st.sidebar.markdown("---")
    st.sidebar.subheader("Rango de periodos")

    periodos = (
        df_p[["Periodo", "Periodo_dt"]]
        .drop_duplicates()
        .sort_values(["Periodo_dt", "Periodo"], na_position="last")
        .reset_index(drop=True)
    )

    if periodos.empty:
        st.warning("No hay periodos para los filtros seleccionados.")
        return

    has_dt = periodos["Periodo_dt"].notna().any()

    if has_dt:
        labels = periodos["Periodo"].tolist()
        start_label, end_label = st.sidebar.select_slider(
            "Desde / Hasta",
            options=labels,
            value=(labels[0], labels[-1]),
            key="periodo_rango",
        )

        start_dt = periodos.loc[periodos["Periodo"] == start_label, "Periodo_dt"].iloc[0]
        end_dt = periodos.loc[periodos["Periodo"] == end_label, "Periodo_dt"].iloc[0]

        if pd.isna(start_dt) or pd.isna(end_dt):
            idx1 = labels.index(start_label)
            idx2 = labels.index(end_label)
            selected_labels = labels[min(idx1, idx2): max(idx1, idx2) + 1]
            df_p = df_p[df_p["Periodo"].isin(selected_labels)].copy()
        else:
            df_p = df_p[(df_p["Periodo_dt"] >= start_dt) & (df_p["Periodo_dt"] <= end_dt)].copy()
    else:
        labels = periodos["Periodo"].tolist()
        selected_labels = st.sidebar.multiselect(
            "Selecciona periodos", labels, default=labels, key="periodo_multi"
        )
        df_p = df_p[df_p["Periodo"].isin(selected_labels)].copy()

    if df_p.empty:
        st.warning("No hay datos para el rango seleccionado.")
        return

    # ---- Orden cronológico real ----
    df_p = df_p.sort_values(["Periodo_dt", "Periodo"], na_position="last")

    # ---- Totales base para KPIs ----
    total_basico = df_p["Total Salario Basico USD"].sum() if "Total Salario Basico USD" in df_p.columns else 0
    total_vc = df_p["Total Comisiones Vivecasa USD"].sum() if "Total Comisiones Vivecasa USD" in df_p.columns else 0
    total_vp = df_p["Total Comisiones Viveprestamo USD"].sum() if "Total Comisiones Viveprestamo USD" in df_p.columns else 0
    total_bonos = df_p["Total Bonos y Premios USD"].sum() if "Total Bonos y Premios USD" in df_p.columns else 0

    prestaciones_total = (
        df_p["Total PPSS Salario Basico USD"].sum() if "Total PPSS Salario Basico USD" in df_p.columns else 0
    ) + (
        df_p["Total Prestaciones Sociales USD"].sum() if "Total Prestaciones Sociales USD" in df_p.columns else 0
    )

    # ---- KPIs (nombres simplificados) ----
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Salario Básico", fmt_usd(total_basico))
    c2.metric("Prestaciones", fmt_usd(prestaciones_total))
    c3.metric("Vivecasa", fmt_usd(total_vc))
    c4.metric("Viveprestamo", fmt_usd(total_vp))
    c5.metric("Bonos", fmt_usd(total_bonos))

    st.caption(f"**Cargo:** {cargo_sel}  |  **Persona:** {persona_sel}")

    st.markdown("---")

    # ---- Resumen por periodo ----
    st.markdown("### Resumen por periodo")

    # Para el resumen, dejamos las columnas originales + Total Nómina (si existe)
    sum_cols = [c for c in MONEY_COLS if c in df_p.columns]

    resumen = (
        df_p.groupby(["Periodo", "Periodo_dt"], as_index=False)[sum_cols]
        .sum(numeric_only=True)
        .sort_values(["Periodo_dt", "Periodo"], na_position="last")
        .drop(columns=["Periodo_dt"])
    )
    st.dataframe(resumen)

    # ---- Detalle ----
    st.markdown("### Detalle")
    show_cols = [c for c in DIM_COLS if c in df_p.columns] + sum_cols
    st.dataframe(df_p[show_cols])

    st.download_button(
        "Descargar detalle filtrado (CSV)",
        data=df_p.drop(columns=["Periodo_dt"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name=f"HdePagos_{persona_sel}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    build_historico_nomina()
