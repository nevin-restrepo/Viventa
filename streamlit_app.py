import streamlit as st
import pandas as pd
import numpy as np

# ===================================================
# CONFIG
# ===================================================
st.set_page_config(page_title="Viventa - Histórico & Simuladores 2026", layout="wide")
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

    dt = pd.to_datetime(txt, errors="coerce")
    if not pd.isna(dt):
        return pd.Timestamp(dt.year, dt.month, 1)

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

    st.sidebar.subheader("Filtros (Histórico)")
    cargos = sorted(df["Cargo"].dropna().unique())
    cargo_sel = st.sidebar.selectbox("Cargo", cargos, key="hist_cargo")

    df_c = df[df["Cargo"] == cargo_sel].copy()
    personas = sorted(df_c["Nick Name"].dropna().unique())
    persona_sel = st.sidebar.selectbox("Nick Name", personas, key="hist_persona")

    df_p = df_c[df_c["Nick Name"] == persona_sel].copy()

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
# SIMULADOR OPERACIONES (YA HECHO)
# ===================================================
def calc_excedente(n: int, minimo: int, valor_unidad: int) -> int:
    return max(int(n) - int(minimo), 0) * int(valor_unidad)

def calc_por_unidad(n: int, valor_unidad: int) -> int:
    return max(int(n), 0) * int(valor_unidad)

def gate_all_ok(**gates) -> bool:
    return all(bool(v) for v in gates.values())

GER_DES_META_100 = {
    "Enero": 278, "Febrero": 298, "Marzo": 338, "Abril": 316, "Mayo": 318, "Junio": 297,
    "Julio": 350, "Agosto": 330, "Septiembre": 360, "Octubre": 350, "Noviembre": 342, "Diciembre": 338,
}
GER_DES_META_95 = {
    "Enero": 264, "Febrero": 283, "Marzo": 321, "Abril": 300, "Mayo": 302, "Junio": 282,
    "Julio": 333, "Agosto": 314, "Septiembre": 342, "Octubre": 333, "Noviembre": 325, "Diciembre": 321,
}

GER_ANALISIS_100 = {"Q1": 405, "Q2": 440, "Q3": 500, "Q4": 575}
GER_ANALISIS_95 = {"Q1": 385, "Q2": 418, "Q3": 475, "Q4": 546}

SIM_ROLES_OP = {
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

def render_inputs(role_def: dict, prefix: str) -> dict:
    values = {}
    for item in role_def["inputs"]:
        if len(item) == 4:
            key, label, typ, default = item
            options = None
        else:
            key, label, typ, default, options = item[0], item[1], item[2], item[3], item[4]

        if typ == "int":
            values[key] = st.number_input(label, min_value=0, value=int(default), step=1, key=f"{prefix}_{key}")
        elif typ == "float":
            values[key] = st.number_input(label, min_value=0.0, value=float(default), step=0.01, key=f"{prefix}_{key}")
        elif typ == "bool":
            values[key] = st.checkbox(label, value=bool(default), key=f"{prefix}_{key}")
        elif typ == "select":
            if not options:
                values[key] = default
            else:
                idx = options.index(default) if default in options else 0
                values[key] = st.selectbox(label, options, index=idx, key=f"{prefix}_{key}")
        else:
            st.warning(f"Tipo no soportado: {typ} en {key}")
    return values

def build_simulador_operaciones():
    st.subheader("Simulador Operaciones")
    cargo = st.selectbox("Cargo (Operaciones)", list(SIM_ROLES_OP.keys()), key="op_cargo")
    role_def = SIM_ROLES_OP[cargo]
    currency = role_def.get("currency", "COP")

    st.markdown("#### Parámetros")
    x = render_inputs(role_def, prefix="op")

    if st.button("Calcular (Operaciones)", type="primary", key="btn_calc_op"):
        gate_ok = role_def.get("gate", lambda _: True)(x)
        res = role_def["calc"](x)

        scope = role_def.get("gate_scope", "all")
        if not gate_ok:
            if scope == "desem_only" and "Comisión desembolsos" in res:
                res["Comisión desembolsos"] = 0
            else:
                for k in list(res.keys()):
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
# SIMULADOR COMERCIAL (NUEVO - ARRANCAMOS CON CONSULTORES)
# ===================================================
CONSULTOR_SV_PCTS = {
    "Consultor - Aprendiz": [
        (1, 4, 0.35),
        (5, 9, 0.50),
        (10, 14, 0.60),
        (15, 10**9, 0.75),
    ],
    "Consultor - Emprendedor": [
        (1, 7, 0.45),
        (8, 11, 0.60),
        (12, 10**9, 0.75),
    ],
    "Consultor - Experto": [
        (1, 9, 0.50),
        (10, 13, 0.70),
        (14, 10**9, 0.75),
    ],
}

CONSULTOR_VARADOS_USD = {
    "Consultor - Aprendiz": 60,
    "Consultor - Emprendedor": 60,
    "Consultor - Experto": 100,
}

# Vivecasa % según cantidad total (A/AA/AAA) por mes
# columnas: 1, 2-3, >=4
VIVECASA_PCT = {
    "A":   { "1": 0.0052, "2_3": 0.0055, "4p": 0.0056 },
    "AA":  { "1": 0.0079, "2_3": 0.0083, "4p": 0.0085 },
    "AAA": { "1": 0.0131, "2_3": 0.0138, "4p": 0.0141 },
}

def vivecasa_bracket(total_units: int) -> str:
    if total_units <= 0:
        return "0"
    if total_units == 1:
        return "1"
    if total_units in (2, 3):
        return "2_3"
    return "4p"

# Anticipo según valor promedio inmueble (COP)
def anticipo_usd_por_inmueble(valor_cop: float) -> float:
    if valor_cop <= 0:
        return 0.0
    if 90_000_000 <= valor_cop <= 270_000_000:
        return 220.0
    if 270_000_001 <= valor_cop <= 480_000_000:
        return 420.0
    if 480_000_001 <= valor_cop <= 600_000_000:
        return 650.0
    if valor_cop >= 600_000_001:
        return 950.0
    # si cae por debajo de 90M, dejamos 0 (o podrías mapearlo al primer rango)
    return 0.0

def pct_sv_por_unidades(role: str, units: int) -> float:
    if units <= 0:
        return 0.0
    for lo, hi, pct in CONSULTOR_SV_PCTS[role]:
        if lo <= units <= hi:
            return pct
    return 0.0

def bono_bolivar_usd(n_bolivar: int) -> float:
    if n_bolivar == 2:
        return 300.0
    if n_bolivar >= 3:
        return 500.0
    return 0.0

def bono_trimestral_consultor(role: str, puntos: int, cumple_creacion: bool, cumple_efectivos: bool) -> float:
    if not (cumple_creacion and cumple_efectivos):
        return 0.0

    if role == "Consultor - Aprendiz":
        if 250 <= puntos <= 350:
            return 1500.0
        if puntos >= 351:
            return 1800.0
        return 0.0

    if role == "Consultor - Emprendedor":
        if 350 <= puntos <= 400:
            return 2200.0
        if puntos >= 401:
            return 2500.0
        return 0.0

    if role == "Consultor - Experto":
        if 400 <= puntos <= 490:
            return 2500.0
        if puntos >= 491:
            return 2800.0
        return 0.0

    return 0.0

def month_input_block(prefix: str):
    st.markdown("##### SV (Créditos)")
    sv_units = st.number_input("SV facturados (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_sv_units")
    tarifa_sv_usd = st.number_input("Tarifa SV (USD) - editable", min_value=0.0, value=500.0, step=10.0, key=f"{prefix}_tarifa_sv")
    desc_sv = st.slider("Descuento promedio SV", 0.0, 0.50, 0.0, 0.01, key=f"{prefix}_desc_sv")

    sv_asignados = st.number_input("SV facturados (leads asignados) - para puntos", min_value=0, value=0, step=1, key=f"{prefix}_sv_asig")
    sv_propios = st.number_input("SV facturados (creación propia) - para puntos", min_value=0, value=0, step=1, key=f"{prefix}_sv_propios")

    varados_to_fact = st.number_input("Varados que pasaron a Facturado (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_varados")

    st.markdown("##### Vivecasa (Ventas)")
    vc_a = st.number_input("Vivecasas A (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_vc_a")
    vc_aa = st.number_input("Vivecasas AA (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_vc_aa")
    vc_aaa = st.number_input("Vivecasas AAA (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_vc_aaa")

    v_a = st.number_input("Valor promedio A (COP)", min_value=0.0, value=0.0, step=1_000_000.0, key=f"{prefix}_v_a")
    v_aa = st.number_input("Valor promedio AA (COP)", min_value=0.0, value=0.0, step=1_000_000.0, key=f"{prefix}_v_aa")
    v_aaa = st.number_input("Valor promedio AAA (COP)", min_value=0.0, value=0.0, step=1_000_000.0, key=f"{prefix}_v_aaa")

    vc_bolivar = st.number_input("Vivecasas Bolívar (unidades en el mes)", min_value=0, value=0, step=1, key=f"{prefix}_vc_bolivar")
    vc_b2b = st.number_input("Vivecasas B2B creación propia (unidades)", min_value=0, value=0, step=1, key=f"{prefix}_vc_b2b")

    return {
        "sv_units": sv_units,
        "tarifa_sv_usd": tarifa_sv_usd,
        "desc_sv": desc_sv,
        "sv_asignados": sv_asignados,
        "sv_propios": sv_propios,
        "varados_to_fact": varados_to_fact,
        "vc_a": vc_a, "vc_aa": vc_aa, "vc_aaa": vc_aaa,
        "v_a": v_a, "v_aa": v_aa, "v_aaa": v_aaa,
        "vc_bolivar": vc_bolivar,
        "vc_b2b": vc_b2b,
    }

def calc_month(role: str, x: dict, trm: float):
    # ---------- SV ----------
    pct_sv = pct_sv_por_unidades(role, int(x["sv_units"]))
    tarifa_neta = float(x["tarifa_sv_usd"]) * (1.0 - float(x["desc_sv"]))
    com_sv_usd = int(x["sv_units"]) * tarifa_neta * pct_sv

    varados_pay_usd = int(x["varados_to_fact"]) * CONSULTOR_VARADOS_USD[role]

    # ---------- VIVECASA ----------
    total_vc_units = int(x["vc_a"]) + int(x["vc_aa"]) + int(x["vc_aaa"])
    bracket = vivecasa_bracket(total_vc_units)

    pct_a = VIVECASA_PCT["A"].get(bracket, 0.0)
    pct_aa = VIVECASA_PCT["AA"].get(bracket, 0.0)
    pct_aaa = VIVECASA_PCT["AAA"].get(bracket, 0.0)

    # comisión total (COP) por categoría
    com_vc_cop = (
        int(x["vc_a"]) * float(x["v_a"]) * pct_a +
        int(x["vc_aa"]) * float(x["v_aa"]) * pct_aa +
        int(x["vc_aaa"]) * float(x["v_aaa"]) * pct_aaa
    )

    # convertir a USD usando TRM promedio (para mostrar y para comparar con anticipo)
    com_vc_usd = com_vc_cop / trm if trm > 0 else 0.0

    # anticipo USD por inmueble (según valor promedio por categoría)
    anticipo_total_usd = (
        int(x["vc_a"]) * anticipo_usd_por_inmueble(float(x["v_a"])) +
        int(x["vc_aa"]) * anticipo_usd_por_inmueble(float(x["v_aa"])) +
        int(x["vc_aaa"]) * anticipo_usd_por_inmueble(float(x["v_aaa"]))
    )

    saldo_vc_usd = max(com_vc_usd - anticipo_total_usd, 0.0)

    # bono bolívar
    bolivar_usd = bono_bolivar_usd(int(x["vc_bolivar"]))

    # ---------- PUNTOS ----------
    # SV: asignados=10, propios=15
    puntos_sv = int(x["sv_asignados"]) * 10 + int(x["sv_propios"]) * 15

    # Vivecasa: 20 pts c/u, B2B propia: 30 pts c/u (sin duplicar)
    b2b = min(int(x["vc_b2b"]), total_vc_units)
    puntos_vc = (total_vc_units - b2b) * 20 + b2b * 30

    puntos_mes = puntos_sv + puntos_vc

    # ---------- TOTAL MES ----------
    total_mes_usd = com_sv_usd + varados_pay_usd + anticipo_total_usd + saldo_vc_usd + bolivar_usd

    return {
        "pct_sv": pct_sv,
        "tarifa_sv_neta": tarifa_neta,
        "com_sv_usd": com_sv_usd,
        "varados_usd": varados_pay_usd,
        "com_vc_cop": com_vc_cop,
        "com_vc_usd": com_vc_usd,
        "anticipo_vc_usd": anticipo_total_usd,
        "saldo_vc_usd": saldo_vc_usd,
        "bolivar_usd": bolivar_usd,
        "puntos_mes": puntos_mes,
        "total_mes_usd": total_mes_usd,
        "bracket_vc": bracket,
    }

def build_simulador_comercial():
    st.subheader("Simulador Comercial (arranque: Consultores)")

    colA, colB = st.columns([1, 1])
    with colA:
        role = st.selectbox(
            "Cargo (Comercial)",
            ["Consultor - Aprendiz", "Consultor - Emprendedor", "Consultor - Experto"],
            key="com_role",
        )
    with colB:
        trm = st.number_input("TRM promedio (COP/USD)", min_value=1.0, value=4000.0, step=50.0, key="com_trm")

    st.divider()
    st.markdown("### Mes 1 (input base)")
    mes1 = month_input_block(prefix="m1")

    st.divider()
    repetir = st.checkbox("Para el bono trimestral: simular Mes 2 y Mes 3 iguales al Mes 1", value=True, key="rep3")

    if not repetir:
        with st.expander("Mes 2"):
            mes2 = month_input_block(prefix="m2")
        with st.expander("Mes 3"):
            mes3 = month_input_block(prefix="m3")
    else:
        mes2 = dict(mes1)
        mes3 = dict(mes1)

    st.divider()
    st.markdown("### Condiciones bono trimestral (requisito)")
    if role == "Consultor - Aprendiz":
        st.caption("Aprendiz: requiere creación mensual 30 clientes propios y 5 efectivos.")
        cumple_creacion = st.checkbox("Cumple creación propia requerida (30/mes)", value=True, key="crea_ok")
    else:
        st.caption("Emprendedor/Experto: requiere creación mensual 45 clientes propios y 5 efectivos.")
        cumple_creacion = st.checkbox("Cumple creación propia requerida (45/mes)", value=True, key="crea_ok")

    cumple_efectivos = st.checkbox("Cumple mínimo de 5 efectivos/mes", value=True, key="efec_ok")

    st.divider()
    if st.button("Calcular (Comercial)", type="primary", key="btn_calc_com"):
        r1 = calc_month(role, mes1, trm)
        r2 = calc_month(role, mes2, trm)
        r3 = calc_month(role, mes3, trm)

        puntos_trim = int(r1["puntos_mes"] + r2["puntos_mes"] + r3["puntos_mes"])
        bono_trim_usd = bono_trimestral_consultor(role, puntos_trim, cumple_creacion, cumple_efectivos)

        total_trim_usd = r1["total_mes_usd"] + r2["total_mes_usd"] + r3["total_mes_usd"] + bono_trim_usd

        st.markdown("## Resultados")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Mes 1", fmt_money(r1["total_mes_usd"], "USD"))
        k2.metric("Puntos Trimestre", f"{puntos_trim:,}")
        k3.metric("Bono Trimestral", fmt_money(bono_trim_usd, "USD"))
        k4.metric("Total Trimestre (incluye bono)", fmt_money(total_trim_usd, "USD"))

        st.divider()
        st.markdown("### Detalle Mes 1")
        d1, d2, d3, d4, d5 = st.columns(5)
        d1.metric("SV % tramo", f"{r1['pct_sv']*100:.0f}%")
        d2.metric("SV comisión", fmt_money(r1["com_sv_usd"], "USD"))
        d3.metric("Varados", fmt_money(r1["varados_usd"], "USD"))
        d4.metric("Vivecasa anticipo", fmt_money(r1["anticipo_vc_usd"], "USD"))
        d5.metric("Vivecasa saldo", fmt_money(r1["saldo_vc_usd"], "USD"))

        st.caption(f"Vivecasa bracket por cantidad (Mes 1): **{r1['bracket_vc']}** | Comisión Vivecasa total: {fmt_money(r1['com_vc_usd'], 'USD')} (≈ {fmt_money(r1['com_vc_cop'], 'COP')})")

        st.markdown("### Tabla resumen (Mes 1 / Mes 2 / Mes 3)")
        df_sum = pd.DataFrame([
            {"Mes": "Mes 1", "Total USD": r1["total_mes_usd"], "Puntos": r1["puntos_mes"]},
            {"Mes": "Mes 2", "Total USD": r2["total_mes_usd"], "Puntos": r2["puntos_mes"]},
            {"Mes": "Mes 3", "Total USD": r3["total_mes_usd"], "Puntos": r3["puntos_mes"]},
        ])
        st.dataframe(df_sum)


# ===================================================
# MAIN (3 TABS)
# ===================================================
def main():
    st.title("Viventa – Histórico & Simuladores 2026")

    tab1, tab2, tab3 = st.tabs(["Histórico", "Simulador Operaciones", "Simulador Comercial"])

    with tab1:
        build_historico()

    with tab2:
        build_simulador_operaciones()

    with tab3:
        build_simulador_comercial()
if __name__ == "__main__":
    main()
