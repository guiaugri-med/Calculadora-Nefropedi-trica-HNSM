import streamlit as st
import math

st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

st.title("🩺 Calculadora de Nefrologia Pediátrica")
st.caption("Fórmula de Schwartz Original (Método de Jaffé - Não IDMS)")

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📥 Dados do Paciente")
    

with st.sidebar:
    st.divider()
    st.error("🚨 **Sinais de Alerta (Red Flags)**")
    with st.expander("Quando chamar o Nefropediatra:"):
        st.write("""
        - **Oligúria/Anúria:** Débito urinário < 1 mL/kg/h após hidratação.
        - **Hematúria Macroscópica:** Risco de Trombose da Veia Renal.
        - **Crise Hipertensiva:** PA > percentil 95 + 12 mmHg para idade/estatura.
        - **Abdome Agudo:** Suspeita de Peritonite Bacteriana Espontânea (PBE).
        - **Dispneia:** Risco de edema pulmonar ou derrame pleural volumoso.
        - **Assimetria de MMII:** Dor ou edema unilateral (risco de TVP).
        - **Corticorresistência:** Persistência de proteinúria 4+ após 8 semanas.
        """)
        
    
with st.sidebar:
    st.header("📥 Dados do Paciente")
    
    # 1. Entrada de Idade Detalhada
    st.write("**Idade do Paciente:**")
    c1, c2, c3 = st.columns(3)
    with c1:
        anos = st.number_input("Anos", min_value=0, max_value=18, value=5)
    with c2:
        meses = st.number_input("Meses", min_value=0, max_value=11, value=0)
    with c3:
        dias = st.number_input("Dias", min_value=0, max_value=30, value=0)

    # 2. Entrada de Sexo (Essencial para Adolescentes)
    sexo = st.radio("Sexo Biológico", ["Feminino", "Masculino"])

    # 3. Lógica Automática para K e Categoria
    # Calculamos a idade total em meses para facilitar a lógica
    idade_total_meses = (anos * 12) + meses

    if idade_total_meses < 12:
        # Se for menor de 1 ano, precisamos saber se foi prematuro
        prematuro = st.toggle("Nasceu prematuro?")
        if prematuro:
            k_escolhido = 0.33
            categoria = "RN Pré-termo"
        else:
            k_escolhido = 0.45
            categoria = "RN a Termo até 1 ano"
    else:
        # Para maiores de 1 ano, a distinção é por sexo e idade (adolescência)
        # Na fórmula original de Schwartz, k=0.70 é para rapazes adolescentes (geralmente > 13 anos)
        if sexo == "Masculino" and anos >= 13:
            k_escolhido = 0.70
            categoria = "Adolescente Masculino"
        else:
            k_escolhido = 0.55
            categoria = "Criança / Adolescente Feminino"

    # Exibição da categoria definida automaticamente
    st.info(f"**Categoria definida:** {categoria} (K = {k_escolhido})")

    st.divider()
    
    # Restante das entradas
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
