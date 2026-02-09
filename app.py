import streamlit as st
import math
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

# --- BANCO DE DADOS LOCAL ---
def init_db():
    conn = sqlite3.connect('nefroped_merces.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (id INTEGER PRIMARY KEY, nome TEXT, leito TEXT, data_admissao TEXT, 
                  anos INTEGER, meses INTEGER, dias INTEGER, sexo TEXT, k REAL, 
                  peso_seco REAL, estatura REAL, sc REAL, tfge REAL, dose_ataque REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS monitorizacao 
                 (id INTEGER PRIMARY KEY, paciente_id INTEGER, data TEXT, hora TEXT, 
                  peso REAL, pa TEXT, fc INTEGER, fr INTEGER, temp REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÃO GERAR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'Ficha de Monitorização Vascular e Metabólica', 0, 1, 'C')
        self.set_font('helvetica', '', 10)
        self.cell(0, 5, 'Setor: Pediatria - Hospital Nossa Senhora das Mercês', 0, 1, 'C')
        self.ln(10)

def gerar_pdf(p, hist):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    pdf.cell(0, 8, f"Nome do Paciente: {p['nome']}", ln=True)
    pdf.cell(0, 8, f"Leito: {p['leito']}", ln=True)
    pdf.cell(0, 8, f"Data de Admissão: {p['data_admissao']} | Peso na Admissão (Seco): {p['peso_seco']} kg | SC: {p['sc']:.2f} m2", ln=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 10, "1. Controle de Sinais Vitais e Antropometria", ln=True)
    pdf.set_font("helvetica", size=9)
    pdf.multi_cell(0, 5, "Monitorizar a Pressão Arterial (PA) pelo menos 3x ao dia devido ao risco de hipertensão associada à corticoterapia e doença renal.")
    pdf.ln(5)
    
    pdf.set_font('helvetica', 'B', 8)
    pdf.cell(25, 8, 'Data', 1, 0, 'C')
    pdf.cell(20, 8, 'Hora', 1, 0, 'C')
    pdf.cell(25, 8, 'Peso (kg)', 1, 0, 'C')
    pdf.cell(30, 8, 'PA', 1, 0, 'C')
    pdf.cell(25, 8, 'FC', 1, 0, 'C')
    pdf.cell(25, 8, 'FR', 1, 0, 'C')
    pdf.cell(25, 8, 'Temp', 1, 1, 'C')
    
    pdf.set_font('helvetica', '', 8)
    for _, row in hist.iterrows():
        pdf.cell(25, 8, str(row['data']), 1, 0, 'C')
        pdf.cell(20, 8, str(row['hora']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['peso']:.2f}", 1, 0, 'C')
        pdf.cell(30, 8, str(row['pa']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fc']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fr']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['temp']:.1f}", 1, 1, 'C')
        
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("🩺 Nefropediatria - HNSM")

tab1, tab2, tab3 = st.tabs(["🔢 Cadastro e Cálculos", "📋 Monitorização Diária", "🔎 Histórico e PDF"])

# --- TAB 1: CADASTRO E CÁLCULOS ---
with tab1:
    with st.form("cadastro"):
        col1, col2 = st.columns(2)
        nome_in = col1.text_input("Nome do Paciente").upper()
        leito_in = col2.text_input("Leito")
        data_adm_in = st.date_input("Data de Admissão", value=datetime.now())
        
        st.write("**Idade:**")
        c1, c2, c3 = st.columns(3)
        anos_in = c1.number_input("Anos", 0, 18, 5)
        meses_in = c2.number_input("Meses", 0, 11, 0)
        dias_in = c3.number_input("Dias", 0, 30, 0)
        sexo_in = st.radio("Sexo Biológico", ["Feminino", "Masculino"], horizontal=True)
        
        # Lógica de K
        idade_meses = (anos_in * 12) + meses_in
        if idade_meses < 12:
            prematuro = st.checkbox("Nasceu prematuro?")
            k_final = 0.33 if prematuro else 0.45
        else:
            k_final = 0.70 if (sexo_in == "Masculino" and anos_in >= 13) else 0.55
            
        p_seco_in = st.number_input("Peso na Admissão (kg)", 1.0, 150.0, 20.0)
        estat_in = st.number_input("Estatura (cm)", 30.0, 200.0, 110.0)
        creat_in = st.number_input("Creatinina (mg/dL)", 0.1, 10.0, 0.6)
        
        submit_cadastro = st.form_submit_button("Salvar Cadastro e Calcular")

    if submit_cadastro:
        # Cálculos movidos para dentro da ação do botão
        sc_calc = math.sqrt((p_seco_in * estat_in) / 3600)
        tfge_calc = (k_final * estat_in) / creat_in
        dose_ataque_calc = min(sc_calc * 60, 60.0)
        dose_manut_calc = min(sc_calc * 40, 40.0)
        vol_alb_calc = (p_seco_in * 0.5) * 5

        # Salvar no Banco
        conn = sqlite3.connect('nefroped_merces.db')
        c = conn.cursor()
        c.execute("INSERT INTO pacientes (nome, leito, data_admissao, anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                  (nome_in, leito_in, data_adm_in.strftime("%d/%m/%Y"), anos_in, meses_in, dias_in, sexo_in, k_final, p_seco_in, estat_in, sc_calc, tfge_calc, dose_ataque_calc))
        conn.commit()
        conn.close()

        # Exibição dos resultados (Exclusiva após cálculo)
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Superfície Corporal", f"{sc_calc:.2f} m²")
        m2.metric("TFGe (Schwartz 1)", f"{tfge_calc:.1f} mL/min")
        m3.metric("K Utilizado", f"{k_final}")

        st.subheader("📋 Conduta Sugerida")
        res1, res2 = st.columns(2)
        res1.success(f"**Prednisolona (Ataque):** {dose_ataque_calc:.1f} mg/dia")
        res1.info(f"**Albumina 20%:** {vol_alb_calc:.1f} mL IV")
        res2.warning(f"**Prednisolona (Manutenção):** {dose_manut_calc:.1f} mg (D.A.)")
        res2.write(f"*Furosemida IV Sugerida:* {p_seco_in*0.5:.1f} mg")

# --- TAB 2: MONITORIZAÇÃO ---
with tab2:
    conn = sqlite3.connect('nefroped_merces.db')
    pacs = pd.read_sql("SELECT id, nome, leito FROM pacientes", conn)
    conn.close()
    
    if not pacs.empty:
        escolha = st.selectbox("Selecione o Paciente", pacs['nome'] + " (Leito: " + pacs['leito'] + ")")
        pac_id = int(pacs[pacs['nome'] == escolha.split(" (")[0]]['id'].iloc[0])
        
        with st.form("monitor"):
            c1, c2 = st.columns(2)
            d_reg = c1.date_input("Data do Registro")
            h_reg = c2.selectbox("Hora", ["08:00", "14:00", "20:00"])
            
            v1, v2, v3, v4, v5 = st.columns(5)
            p_v = v1.number_input("Peso (kg)", 0.0)
            pa_v = v2.text_input("PA (mmHg)")
            fc_v = v3.number_input("FC (bpm)", 0)
            fr_v = v4.number_input("FR (irpm)", 0)
            t_v = v5.number_input("Temp (C)", 30.0, 42.0, 36.5)
            
            if st.form_submit_button("Salvar Sinais Vitais"):
                conn = sqlite3.connect('nefroped_merces.db')
                c = conn.cursor()
                c.execute("INSERT INTO monitorizacao (paciente_id, data, hora, peso, pa, fc, fr, temp) VALUES (?,?,?,?,?,?,?,?)",
                          (pac_id, d_reg.strftime("%d/%m/%Y"), h_reg, p_v, pa_v, fc_v, fr_v, t_v))
                conn.commit()
                conn.close()
                st.success("Dados salvos!")

# --- TAB 3: HISTÓRICO E PDF ---
with tab3:
    busca = st.text_input("Buscar Paciente por Nome").upper()
    if busca:
        conn = sqlite3.connect('nefroped_merces.db')
        dados_p = pd.read_sql(f"SELECT * FROM pacientes WHERE nome LIKE '%{busca}%'", conn)
        if not dados_p.empty:
            p_sel = dados_p.iloc[0]
            st.subheader(f"Paciente: {p_sel['nome']}")
            
            hist = pd.read_sql(f"SELECT * FROM monitorizacao WHERE paciente_id = {p_sel['id']} ORDER BY data DESC, hora DESC", conn)
            st.dataframe(hist[['data', 'hora', 'peso', 'pa', 'fc', 'fr', 'temp']])
            
            pdf_bytes = gerar_pdf(p_sel, hist)
            st.download_button("📥 Baixar PDF da Ficha", data=pdf_bytes, file_name=f"Ficha_{p_sel['nome']}.pdf", mime="application/pdf")
        else:
            st.warning("Paciente não encontrado.")
        conn.close()

# Sidebar e Referências (Mantidas)
with st.sidebar:
    st.error("🚨 **Sinais de Alerta**")
    st.write("- Oligúria (< 1 mL/kg/h)\n- Hematúria Macroscópica\n- Crise Hipertensiva\n- Dor Abdominal (PBE)")

with st.expander("📚 Fundamentação Teórica"):
    st.write("""
    - **Fórmula:** Schwartz Original (1976) para creatinina colorimétrica.
    - **Corticoterapia:** Protocolo ISKDC (60mg/m²).
    - **SC:** Fórmula de Mosteller.
    """)
