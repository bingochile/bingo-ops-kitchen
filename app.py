import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Bingo Ops Kitchen", layout="wide")

# ---------- ESTILO ----------
st.markdown("""
<style>
.main {
    background-color: #0E1117;
}
h1, h2, h3 {
    color: #FAFAFA;
}
.stMetric {
    background-color: #1E2228;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER CON LOGO ----------
col_logo, col_title = st.columns([1,4])

with col_logo:
    st.image("logo.png", width=120)

with col_title:
    st.title("Bingo Ops Kitchen")
    st.caption("Smart Restaurant Decision System")

st.divider()

# ---------- ARCHIVOS ----------
bingo_file = "Bingo_Ops_Kitchen_FULL.xlsx"
fudo_file = "Ventas xlxs fudo.xlsx"

# ---------- CARGA ----------
@st.cache_data
def load_bingo():
    prod = pd.read_excel(bingo_file, sheet_name="Produccion")
    rec = pd.read_excel(bingo_file, sheet_name="Recetas")
    bod = pd.read_excel(bingo_file, sheet_name="Bodega")
    return prod, rec, bod

@st.cache_data
def load_fudo():
    df = pd.read_excel(fudo_file, sheet_name="Adiciones")
    return df

produccion, recetas, bodega = load_bingo()
fudo = load_fudo()

# ---------- SIDEBAR ----------
st.sidebar.header("📅 Predicción")

dia = st.sidebar.selectbox(
    "Selecciona día",
    ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
)

# ---------- PREDICCIÓN ----------
pred_base = {
    "Wednesday": {
        "Ceviche Meraki": 20,
        "Burger Luke Simple": 16,
        "Power Bowl": 12
    },
    "Friday": {
        "Ceviche Meraki": 30,
        "Burger Luke Simple": 25,
        "Power Bowl": 18
    },
    "Saturday": {
        "Ceviche Meraki": 35,
        "Burger Luke Simple": 28,
        "Power Bowl": 20
    }
}

pred = pred_base.get(dia, pred_base["Wednesday"])

produccion_auto = pd.DataFrame(
    [(dia, k, v) for k, v in pred.items()],
    columns=["Fecha","Producto","Cantidad"]
)

# ---------- COMPRAS ----------
def calcular_compras(produccion, recetas, bodega):
    df = produccion.merge(recetas, on="Producto", how="left")
    df["Necesario"] = df["Cantidad"] * df["Cantidad_por_plato"]

    compras = df.groupby("Insumo")["Necesario"].sum().reset_index()
    compras = compras.merge(bodega, on="Insumo", how="left")

    compras["Stock_actual"] = compras["Stock_actual"].fillna(0)
    compras["Compra"] = (compras["Necesario"] - compras["Stock_actual"]).clip(lower=0)

    return compras.sort_values("Compra", ascending=False)

compras = calcular_compras(produccion_auto, recetas, bodega)

# ---------- FUDO CLASIFICACIÓN ----------
cocina_keywords = ['Comida','Burgu','Platos','Entrada','Tapas','Sand','Pizza','Vegan']

def clasificar(cat):
    for k in cocina_keywords:
        if k.lower() in str(cat).lower():
            return "Cocina"
    return "Barra"

fudo["Tipo"] = fudo["Categoría"].apply(clasificar)
cocina = fudo[fudo["Tipo"] == "Cocina"].copy()

# ---------- COSTOS SIMULADOS ----------
def estimar_costo(row):
    precio = row["Precio"]
    nombre = str(row["Producto"]).lower()

    if "ceviche" in nombre:
        return precio * 0.55
    elif "burger" in nombre:
        return precio * 0.45
    elif "pizza" in nombre:
        return precio * 0.40
    elif "bowl" in nombre:
        return precio * 0.50
    elif "papas" in nombre:
        return precio * 0.30
    else:
        return precio * 0.50

cocina["Costo_simulado"] = cocina.apply(
    lambda row: estimar_costo(row) if row["Costo base"] == 0 else row["Costo base"],
    axis=1
)

# ---------- RENTABILIDAD ----------
cocina["Margen"] = cocina["Precio"] - cocina["Costo_simulado"]

rentabilidad_real = cocina.groupby("Producto").agg({
    "Cantidad":"sum",
    "Precio":"mean",
    "Costo_simulado":"mean",
    "Margen":"mean"
}).reset_index()

rentabilidad_real["Rentabilidad %"] = rentabilidad_real["Margen"] / rentabilidad_real["Precio"]
rentabilidad_real = rentabilidad_real.sort_values("Cantidad", ascending=False)

# ---------- CLASIFICACIÓN ----------
def clasificar_producto(row):
    if row["Rentabilidad %"] > 0.6 and row["Cantidad"] > 500:
        return "🟢 Estrella"
    elif row["Rentabilidad %"] > 0.5:
        return "🟡 Buena"
    elif row["Rentabilidad %"] > 0.4:
        return "🟠 Ajustar"
    else:
        return "🔴 Problema"

rentabilidad_real["Tipo"] = rentabilidad_real.apply(clasificar_producto, axis=1)

# ---------- RECOMENDACIONES ----------
def generar_recomendacion(row):
    if row["Rentabilidad %"] > 0.6 and row["Cantidad"] > 500:
        return "🔥 Mantener y destacar"
    elif row["Rentabilidad %"] < 0.4 and row["Cantidad"] > 500:
        return "⚠️ Subir precio"
    elif row["Rentabilidad %"] > 0.6 and row["Cantidad"] < 200:
        return "📢 Promocionar"
    elif row["Rentabilidad %"] < 0.4 and row["Cantidad"] < 200:
        return "❌ Evaluar eliminar"
    else:
        return "🔍 Revisar"

rentabilidad_real["Recomendación"] = rentabilidad_real.apply(generar_recomendacion, axis=1)

# ---------- KPIs ----------
total_compra = compras["Compra"].sum()
top_producto = rentabilidad_real.iloc[0]["Producto"]
top_margen = rentabilidad_real.iloc[0]["Margen"]

k1, k2, k3 = st.columns(3)

with k1:
    st.metric("🛒 Compra total", f"{round(total_compra,1)}")

with k2:
    st.metric("🔥 Top producto", top_producto)

with k3:
    st.metric("💰 Mejor margen", f"{round(top_margen,1)}")

# ---------- TABLAS ----------
st.subheader("🍽️ Producción")
st.dataframe(produccion_auto, use_container_width=True)

st.subheader("🛒 Compras")
st.dataframe(compras, width="stretch")

st.subheader("💰 Rentabilidad")
st.dataframe(
    rentabilidad_real[["Producto","Cantidad","Rentabilidad %","Tipo","Recomendación"]].head(20),
    use_container_width=True
)

# ---------- COPILOTO ----------
st.subheader("🤖 Copiloto Bingo")

pregunta = st.text_input("💬 Pregunta sobre tu negocio")

def responder(pregunta):
    pregunta = pregunta.lower()

    if "comprar" in pregunta:
        top = compras.head(5)
        texto = "Debes comprar:\n"
        for _, row in top.iterrows():
            if row["Compra"] > 0:
                texto += f"- {row['Insumo']}: {round(row['Compra'],2)}\n"
        return texto

    elif "cocinar" in pregunta:
        texto = "Producción sugerida:\n"
        for _, row in produccion_auto.iterrows():
            texto += f"- {row['Producto']}: {row['Cantidad']}\n"
        return texto

    elif "rentable" in pregunta:
        top = rentabilidad_real.head(5)
        texto = "Más rentables:\n"
        for _, row in top.iterrows():
            texto += f"- {row['Producto']}\n"
        return texto

    else:
        return "Puedes preguntar sobre compras, producción o rentabilidad 😉"

if pregunta:
    st.success(responder(pregunta))