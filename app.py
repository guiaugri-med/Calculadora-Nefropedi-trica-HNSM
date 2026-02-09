import streamlit as st
import math

st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

st.title("🩺 Calculadora de Nefrologia Pediátrica")
st.caption("Fórmula de Schwartz Original (Método de Jaffé - Não IDMS)")

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📥 Dados do Paciente")
    
    # Seleção da Categoria para definir K
    categoria = st.selectbox(
        "Categoria do Paciente (Definição de K)",
        options=[
            "RN Pré-termo (K=0.33)",
            "RN a termo até 1 ano (K=0.45)",
            "Criança / Adolescente Feminino (K=0.55)",
            "Adolescente Masculino (K=0.70)"
        ]
    )
    
    # Mapeamento da constante K conforme solicitado
    mapa_k = {
        "RN Pré-termo (K=0.33)": 0.33,
        "RN a termo até 1 ano (K=0.45)": 0.45,
        "Criança / Adolescente Feminino (K=0.55)": 0.55,
        "Adolescente Masculino (K=0.70)": 0.70
    }
    k_escolhido = mapa_k[categoria]

    peso = st.number_input("Peso Atual (kg)", min_value=1.0, value=20.0, step=0.1)
    estatura = st.number_input("Estatura (cm)", min_value=30.0, value=110.0, step=1.0)
    creatinina = st.number_input("Creatinina Sérica - Jaffé (mg/dL)", min_value=0.1, value=0.6, step=0.01)

# --- CÁLCULOS TÉCNICOS ---
# 1. Superfície Corporal (Mosteller)
sc = math.sqrt((peso * estatura) / 3600)

# 2. Função Renal (Schwartz 1 - Original)
tfge = (k_escolhido * estatura) / creatinina

# 3. Prednisolona (Teto: 60mg ataque / 40mg manut)
dose_ataque = min(sc * 60, 60.0)
dose_manut = min(sc * 40, 40.0)

# 4. Albumina 20% (Dose: 0.5 g/kg -> 2.5 ml/kg)
vol_albumina = (peso * 0.5) * 5 

# --- EXIBIÇÃO ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Superfície Corporal", value=f"{sc:.2f} m²")
    
with col2:
    color = "normal" if tfge >= 90 else "inverse"
    st.metric(label="TFGe (Schwartz 1)", value=f"{tfge:.1f} mL/min", delta_color=color)

with col3:
    st.metric(label="K Utilizado", value=f"{k_escolhido}")

st.divider()

# --- PRESCRIÇÃO ---
st.subheader("📋 Conduta Sugerida")
c1, c2 = st.columns(2)

with c1:
    st.success(f"**Prednisolona (Ataque):** {dose_ataque:.1f} mg/dia")
    st.info(f"**Albumina 20%:** {vol_albumina:.1f} mL IV")

with c2:
    st.warning(f"**Prednisolona (Manutenção):** {dose_manut:.1f} mg (D.A.)")
    st.write(f"*Furosemida IV Sugerida:* {peso*0.5:.1f} mg")

# --- REFERÊNCIAS ---
with st.expander("📚 Fundamentação Teórica"):
    st.write(f"""
    - **Fórmula:** Schwartz (1976/1984) para creatinina não padronizada.
    - **K Utilizado:** {k_escolhido} conforme categoria selecionada.
    - **Corticoterapia:** Protocolo ISKDC (60mg/m²).
    - **Aviso:** Verifique se o laboratório do hospital utiliza o método de Jaffé.
    """)
