import streamlit as st
import pandas as pd
import numpy as np

# ===================================================
# CONFIG
# ===================================================
st.set_page_config(page_title="Viventa - Histórico & Simulador 2026", layout="wide")
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
    """Convierte 'January 2024' / 'Enero 2024' a Timestamp del 1er día del mes."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return pd.NaT
    txt = str(s).strip()

    # 1) Intento directo (por si viene como fecha)
    dt = pd.to_datetime(txt, errors="coerce")
    if not pd.isna(dt):
        return pd.Timestamp(dt.year, dt.month, 1)

    # 2) Formato "Mes Año"
    parts = txt.replace("-", " ").replace("/", " ").split()
    if len(parts) >= 2:
        mes = parts[0].lower()
        try:
            y = int(parts[1])
        except Exception:
            return pd.NaT

        m = MONTH_MAP_EN.get(mes) or MONTH_MAP_ES.get(mes)
        if m:
            return pd.Timestamp(y, m, 1)

    return pd.NaT


def fmt_usd(x: float) -> str:
    return f"${x:,.2f} USD"


def fmt_money(x: float, currency: str = "COP") -> str:
    """Formatea moneda para el simulador."""
    if currency == "USD":
        return f"${x:,.2f} USD"
    if currency == "EUR":
        return f"€{x:,.2f} EUR"
    return f"${x:,.0f} COP"


# ===================================================
# HISTÓRICO: CARGA + LIMPIEZA
# ===================================================
@st.cache_data
def load_nomina():
    # Nota: para .xlsx en Streamlit Cloud necesitas openpyxl en requirements.txt
    df = pd.read_excel(FILE_PATH)

    df.columns = [c.strip() for c in df.columns]
    df = df.replace(r"^\s*$", np.nan, regex=True)

    for c in ["Periodo", "Empleador", "Nick Name", "Cargo"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    df["Periodo_dt"] = df["Periodo"].apply(parse_periodo_to_date) if "Periodo" in df.columns else pd.NaT

    for c in MONEY_COLS + ["Total Activos"]:
        if c in df.columns:
            df[c] = (
                df[c].astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .replace("nan", np.nan)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df


def build_historico():
    df = load_nomina()

    required = {"Periodo", "Empleador", "Nick Name", "Cargo"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"Faltan columnas requeridas: {missing}")
        return

    st.subheader("Histórico de pagos (USD)")
    st.write("Selecciona el **cargo** y la **persona** para ver sus pagos históricos.")

    # Sidebar (solo histórico)
    st.sidebar.subheader("Filtros (Histórico)")
    cargos = sorted(df["Cargo"].dropna().unique())
    cargo_sel = st.sidebar.selectbox("Cargo", cargos, key="hist_cargo")

    df_c = df[df["Cargo"] == cargo_sel].copy()
    personas = sorted(df_c["Nick Name"].dropna().unique())
    persona_sel = st.sidebar.selectbox("Nick Name", personas, key="hist_persona")

    df_p = df_c[df_c["Nick Name"] == persona_sel].copy()

    # Rango de periodos
    st.sidebar.markdown("---")
    st.sidebar.subheader("Rango de periodos")

    periodos = (
        df_p[["Periodo", "Periodo_dt"]].drop_duplicates()
        .sort_values(["Periodo_dt", "Periodo"], na_position="last")
        .reset_index(drop=True)
    )

    if periodos.empty:
        st.warning("No hay periodos para los filtros seleccionados.")
        return

    labels = periodos["Periodo"].tolist()
    start_label, end_label = st.sidebar.select_slider(
        "Desde / Hasta",
        options=labels,
        value=(labels[0], labels[-1]),
        key="hist_rango",
    )

    start_dt = periodos.loc[periodos["Periodo"] == start_label, "Periodo_dt"].iloc[0]
    end_dt = periodos.loc[periodos["Periodo"] == end_label, "Periodo_dt"].iloc[0]

    if pd.notna(start_dt) and pd.notna(end_dt):
        df_p = df_p[(df_p["Periodo_dt"] >= start_dt) & (df_p["Periodo_dt"] <= end_dt)].copy()
    else:
        # fallback: filtra por etiquetas si no se pudo parsear
        idx1 = labels.index(start_label)
        idx2 = labels.index(end_label)
        selected_labels = labels[min(idx1, idx2): max(idx1, idx2) + 1]
        df_p = df_p[df_p["Periodo"].isin(selected_labels)].copy()

    if df_p.empty:
        st.warning("No hay datos para el rango seleccionado.")
        return

    df_p = df_p.sort_values(["Periodo_dt", "Periodo"], na_position="last")

    # KPIs simplificados (USD)
    total_basico = df_p["Total Salario Basico USD"].sum() if "Total Salario Basico USD" in df_p.columns else 0
    prestaciones = df_p["Total Prestaciones Sociales USD"].sum() if "Total Prestaciones Sociales USD" in df_p.columns else 0
    total_vc = df_p["Total Comisiones Vivecasa USD"].sum() if "Total Comisiones Vivecasa USD" in df_p.columns else 0
    total_vp = df_p["Total Comisiones Viveprestamo USD"].sum() if "Total Comisiones Viveprestamo USD" in df_p.columns else 0
    bonos = df_p["Total Bonos y Premios USD"].sum() if "Total Bonos y Premios USD" in df_p.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Salario Básico", fmt_usd(total_basico))
    c2.metric("Prestaciones", fmt_usd(prestaciones))
    c3.metric("Vivecasa", fmt_usd(total_vc))
    c4.metric("Viveprestamo", fmt_usd(total_vp))
    c5.metric("Bonos", fmt_usd(bonos))

    st.caption(f"Cargo: **{cargo_sel}**  |  Persona: **{persona_sel}**")
    st.divider()

    st.markdown("### Resumen por periodo")
    sum_cols = [c for c in MONEY_COLS if c in df_p.columns]
    resumen = (
        df_p.groupby(["Periodo", "Periodo_dt"], as_index=False)[sum_cols]
        .sum(numeric_only=True)
        .sort_values(["Periodo_dt", "Periodo"], na_position="last")
        .drop(columns=["Periodo_dt"])
    )
    st.dataframe(resumen)

    st.markdown("### Detalle")
    show_cols = [c for c in DIM_COLS if c in df_p.columns] + sum_cols
    st.dataframe(df_p[show_cols])

    st.download_button(
        "Descargar detalle filtrado (CSV)",
        data=df_p.drop(columns=["Periodo_dt"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name=f"HdePagos_{persona_sel}.csv",
        mime="text/csv",
    )


# ===================================================
# SIMULADOR: ENGINE DINÁMICO (POR CARGO)
# ===================================================
def calc_excedente(n: int, minimo: int, valor_unidad: int) -> int:
    return max(int(n) - int(minimo), 0) * int(valor_unidad)

def calc_por_unidad(n: int, valor_unidad: int) -> int:
    return max(int(n), 0) * int(valor_unidad)

def gate_all_ok(**gates) -> bool:
    return all(bool(v) for v in gates.values())


# Metas Gerente Desembolso (100% y 95%)
GER_DES_META_100 = {
    "Enero": 278, "Febrero": 298, "Marzo": 338, "Abril": 316, "Mayo": 318, "Junio": 297,
    "Julio": 350, "Agosto": 330, "Septiembre": 360, "Octubre": 350, "Noviembre": 342, "Diciembre": 338,
}
GER_DES_META_95 = {
    "Enero": 264, "Febrero": 283, "Marzo": 321, "Abril": 300, "Mayo": 302, "Junio": 282,
    "Julio": 333, "Agosto": 314, "Septiembre": 342, "Octubre": 333, "Noviembre": 325, "Diciembre": 321,
}

# Metas Gerente Análisis (por trimestre, mensual)
GER_ANALISIS_100 = {"Q1": 405, "Q2": 440, "Q3": 500, "Q4": 575}
GER_ANALISIS_95 = {"Q1": 385, "Q2": 418, "Q3": 475, "Q4": 546}

SIM_ROLES = {
    # --------- GESTORES ----------
    "Gestor de Crédito - UPF": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones netas (trimestre)", "int", 0),
            ("garantia", "Cumple garantía de servicio", "bool", True),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=4, valor_unidad=125000),
            "Bono trimestral": 500000 if x["aprob_trim"] >= 25 else 0,
        },
        "gate": lambda x: x["garantia"],
    },
    "Gestor de Crédito - Convenios/Vivecasas": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones netas (trimestre)", "int", 0),
            ("garantia", "Cumple garantía de servicio", "bool", True),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=10, valor_unidad=125000),
            "Bono trimestral": 500000 if x["aprob_trim"] >= 50 else 0,
        },
        "gate": lambda x: x["garantia"],
    },
    "Gestor de Crédito - FNA": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones netas (trimestre)", "int", 0),
            ("garantia", "Cumple garantía de servicio", "bool", True),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_por_unidad(x["aprob_mes"], valor_unidad=125000),
            "Bono trimestral": 500000 if x["aprob_trim"] >= 20 else 0,
        },
        "gate": lambda x: x["garantia"],
    },
    "Gestor de Crédito - Nueva/Usada": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones netas (trimestre)", "int", 0),
            ("garantia", "Cumple garantía de servicio", "bool", True),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=15, valor_unidad=125000),
            "Bono trimestral": 500000 if x["aprob_trim"] >= 70 else 0,
        },
        "gate": lambda x: x["garantia"],
    },

    # --------- ANALISTAS CRÉDITO ----------
    "Analista de Crédito II": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("carpetas_3dias", "% carpetas ≤ 3 días (0-1)", "float", 0.90),
            ("radicado_ok", "% radicado aprobado (0-1)", "float", 0.90),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=40, valor_unidad=25000),
        },
        "gate": lambda x: gate_all_ok(
            carpetas=x["carpetas_3dias"] >= 0.90,
            radicado=x["radicado_ok"] >= 0.90
        ),
    },
    "Analista de Crédito III": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones netas (mes)", "int", 0),
            ("carpetas_3dias", "% carpetas ≤ 3 días (0-1)", "float", 0.90),
            ("radicado_ok", "% radicado aprobado (0-1)", "float", 0.90),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=60, valor_unidad=25000),
        },
        "gate": lambda x: gate_all_ok(
            carpetas=x["carpetas_3dias"] >= 0.90,
            radicado=x["radicado_ok"] >= 0.90
        ),
    },

    # --------- LÍDER ANÁLISIS CRÉDITO ----------
    "Líder de Análisis de Crédito": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones (mes)", "int", 0),
            ("carpetas_3dias", "% carpetas ≤ 3 días (0-1)", "float", 0.90),
            ("radicado_ok", "% radicado aprobado (0-1)", "float", 0.90),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["aprob_mes"], minimo=350, valor_unidad=10000),
        },
        "gate": lambda x: gate_all_ok(
            carpetas=x["carpetas_3dias"] >= 0.90,
            radicado=x["radicado_ok"] >= 0.90
        ),
    },

    # --------- LEGALIZACIÓN ----------
    "Analista de Legalización": {
        "currency": "COP",
        "inputs": [
            ("desem_mes", "Desembolsos (mes)", "int", 0),
            ("monitoreo", "% monitoreo (0-1)", "float", 0.95),
            ("ans", "% ANS (0-1)", "float", 0.90),
            ("prod_notas", "% productividad notas (0-1)", "float", 0.90),
            ("act_t1", "Actualizaciones tipo 1 (unid)", "int", 0),
            ("act_t2", "Actualizaciones tipo 2 (unid)", "int", 0),
        ],
        "calc": lambda x: {
            "Comisión desembolsos": calc_excedente(x["desem_mes"], minimo=20, valor_unidad=75000),
            "Actualizaciones": (x["act_t1"] * 30000) + (x["act_t2"] * 50000),
        },
        "gate": lambda x: gate_all_ok(
            monitoreo=x["monitoreo"] >= 0.95,
            ans=x["ans"] >= 0.90,
            prod=x["prod_notas"] >= 0.90
        ),
        "gate_scope": "desem_only"
    },

    # --------- LÍDER DE DESEMBOLSOS ----------
    "Líder de Desembolsos": {
        "currency": "COP",
        "inputs": [
            ("desem_mes", "Desembolsos (mes)", "int", 0),
            ("monitoreo", "% monitoreo (0-1)", "float", 0.95),
            ("ans", "% ANS (0-1)", "float", 0.90),
            ("prod_notas", "% productividad notas (0-1)", "float", 0.90),
        ],
        "calc": lambda x: {
            "Comisión mensual": calc_excedente(x["desem_mes"], minimo=250, valor_unidad=10000),
        },
        "gate": lambda x: gate_all_ok(
            monitoreo=x["monitoreo"] >= 0.95,
            ans=x["ans"] >= 0.90,
            prod=x["prod_notas"] >= 0.90
        ),
    },

    # --------- GERENTE DE DESEMBOLSO ----------
    "Gerente de Desembolso y Éxito del Cliente": {
        "currency": "COP",
        "inputs": [
            ("mes", "Mes", "select", "Enero",
             ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]),
            ("desem_mes", "Desembolsos (mes)", "int", 0),
        ],
        "calc": lambda x: (lambda mes, n: {
            "Fijo mensual": 10_000_000,
            "Variable mensual": (2_000_000 if n >= GER_DES_META_100[mes] else (1_250_000 if n >= GER_DES_META_95[mes] else 0)),
        })(x["mes"], x["desem_mes"]),
        "gate": lambda x: True,
    },

    # --------- LÍDERES (CONVENIOS / USADA+UPF / NUEVA+VIVECASAS) ----------
    "Líder de Convenios": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones bancarias (mes)", "int", 0),
            ("trim", "Trimestre", "select", "Q1", ["Q1","Q2","Q3","Q4"]),
            ("aprob_trim", "Aprobaciones bancarias (trimestre)", "int", 0),
            ("reviews_trim", "Reviews 5★ Google (trimestre)", "int", 0),
        ],
        "calc": lambda x: {
            "Comisión mensual (aprob)": 1_000_000 if x["aprob_mes"] >= 85 else 0,
            "Bono trimestral (aprob)": (
                1_000_000 if (
                    (x["trim"] == "Q1" and x["aprob_trim"] >= 250) or
                    (x["trim"] == "Q2" and x["aprob_trim"] >= 275) or
                    (x["trim"] == "Q3" and x["aprob_trim"] >= 275) or
                    (x["trim"] == "Q4" and x["aprob_trim"] >= 300)
                ) else 0
            ),
            "Bono trimestral (reviews)": 500_000 if x["reviews_trim"] >= 250 else 0,
        },
        "gate": lambda x: True,
    },

    "Líder de Vivienda Usada y UPF": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes", "Aprobaciones bancarias (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones bancarias (trimestre)", "int", 0),
            ("reviews_trim", "Reviews 5★ Google (trimestre)", "int", 0),
        ],
        "calc": lambda x: {
            "Comisión mensual (aprob)": 1_000_000 if x["aprob_mes"] >= 120 else 0,
            "Bono trimestral (aprob)": 1_000_000 if x["aprob_trim"] >= 325 else 0,
            "Bono trimestral (reviews)": 500_000 if x["reviews_trim"] >= 325 else 0,
        },
        "gate": lambda x: True,
    },

    "Líder de Vivienda Nueva y Vivecasas": {
        "currency": "COP",
        "inputs": [
            ("aprob_mes_total", "Aprobaciones bancarias TOTAL (mes)", "int", 0),
            ("aprob_mes_vivecasas", "Aprobaciones Vivecasas (mes)", "int", 0),
            ("aprob_mes_nuevas", "Aprobaciones Nuevas (mes)", "int", 0),
            ("aprob_trim", "Aprobaciones bancarias (trimestre)", "int", 0),
            ("reviews_trim", "Reviews 5★ Google (trimestre)", "int", 0),
        ],
        "calc": lambda x: {
            "Comisión mensual (aprob)": (
                1_000_000 if x["aprob_mes_total"] >= 200
                else (500_000 if (x["aprob_mes_vivecasas"] > 60 or x["aprob_mes_nuevas"] > 140) else 0)
            ),
            "Bono trimestral (aprob)": 1_000_000 if x["aprob_trim"] >= 575 else 0,
            "Bono trimestral (reviews)": 500_000 if x["reviews_trim"] >= 500 else 0,
        },
        "gate": lambda x: True,
    },

    # --------- GERENTE ANÁLISIS (EUR) ----------
    "Gerente de Análisis y Gestión de Crédito": {
        "currency": "EUR",
        "inputs": [
            ("trim", "Trimestre", "select", "Q1", ["Q1","Q2","Q3","Q4"]),
            ("aprob_mes", "Aprobaciones bancarias (mes)", "int", 0),
        ],
        "calc": lambda x: (lambda q, n: {
            "Variable mensual": (700 if n >= GER_ANALISIS_100[q] else (450 if n >= GER_ANALISIS_95[q] else 0))
        })(x["trim"], x["aprob_mes"]),
        "gate": lambda x: True,
    },
}


def render_inputs(role_def: dict) -> dict:
    values = {}
    for item in role_def["inputs"]:
        # item puede venir de 4 o 5 elementos (para selects)
        if len(item) == 4:
            key, label, typ, default = item
            options = None
        else:
            key, label, typ, default, options = item[0], item[1], item[2], item[3], item[4]

        if typ == "int":
            values[key] = st.number_input(label, min_value=0, value=int(default), step=1, key=f"sim_{key}")
        elif typ == "float":
            values[key] = st.number_input(label, min_value=0.0, value=float(default), step=0.01, key=f"sim_{key}")
        elif typ == "bool":
            values[key] = st.checkbox(label, value=bool(default), key=f"sim_{key}")
        elif typ == "select":
            if not options:
                st.warning(f"Select sin opciones: {key}")
                values[key] = default
            else:
                idx = options.index(default) if default in options else 0
                values[key] = st.selectbox(label, options, index=idx, key=f"sim_{key}")
        else:
            st.warning(f"Tipo no soportado: {typ} en {key}")
    return values


def build_simulador():
    st.subheader("Simulador por cargo")
    st.write("Selecciona un **cargo** y diligencia los parámetros. El sistema calculará el incentivo estimado.")

    cargo = st.selectbox("Cargo (Simulador)", list(SIM_ROLES.keys()), key="sim_cargo")
    role_def = SIM_ROLES[cargo]
    currency = role_def.get("currency", "COP")

    st.markdown("#### Parámetros")
    x = render_inputs(role_def)

    if st.button("Calcular", type="primary", key="btn_calc"):
        gate_ok = role_def.get("gate", lambda _: True)(x)
        res = role_def["calc"](x)

        scope = role_def.get("gate_scope", "all")
        if not gate_ok:
            if scope == "desem_only" and "Comisión desembolsos" in res:
                res["Comisión desembolsos"] = 0
            else:
                for k in list(res.keys()):
                    # si hay fijo, lo dejamos; si no, tumba todo
                    if k.lower().startswith("fijo"):
                        continue
                    res[k] = 0

        total = sum(float(v) for v in res.values() if isinstance(v, (int, float, np.integer, np.floating)))
        res["Total estimado"] = total

        st.markdown("#### Resultados")
        cols = st.columns(min(4, len(res)))
        for i, (k, v) in enumerate(res.items()):
            cols[i % len(cols)].metric(k, fmt_money(float(v), currency))

        if not gate_ok:
            st.warning("No cumple condiciones de calidad/garantía → se ajustó el pago según reglas del cargo.")


# ===================================================
# MAIN (TABS)
# ===================================================
def main():
    st.title("Viventa – Histórico & Simulador 2026")

    tab1, tab2 = st.tabs(["Histórico", "Simulador"])

    with tab1:
        build_historico()

    with tab2:
        build_simulador()


if __name__ == "__main__":
    main()
