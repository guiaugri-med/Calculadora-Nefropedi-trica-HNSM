import streamlit as st
import math
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

# --- BANCO DE DADOS LOCAL ---
# Nota: No Streamlit Cloud, o banco SQLite é redefinido se o app reiniciar.
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

# --- FUNÇÃO GERAR PDF (CORREÇÃO DO ERRO DE BYTES) ---
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
    
    # Identificação do Paciente conforme padrão solicitado
    pdf.cell(0, 8, f"Nome do Paciente: {p['nome']}", ln=True)
    pdf.cell(0, 8, f"Leito: {p['leito']}", ln=True)
    pdf.cell(0, 8, f"Data de Admissão: {p['data_admissao']} | Peso na Admissão (Seco): {p['peso_seco']} kg | SC: {p['sc']:.2f} m2", ln=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 10, "1. Controle de Sinais Vitais e Antropometria", ln=True)
    pdf.set_font("helvetica", size=9)
    pdf.multi_cell(0, 5, "Monitorizar a Pressão Arterial (PA) pelo menos 3x ao dia devido ao risco de hipertensão associada à corticoterapia e doença renal.")
    pdf.ln(5)
    
    # Tabela de Monitorização
    pdf.set_font('helvetica', 'B', 8)
    pdf.cell(25, 8, 'Data', 1, 0, 'C')
    pdf.cell(20, 8, 'Hora', 1, 0, 'C')
    pdf.cell(25, 8, 'Peso (jejum)', 1, 0, 'C')
    pdf.cell(30, 8, 'PA (mmHg)', 1, 0, 'C')
    pdf.cell(25, 8, 'FC (bpm)', 1, 0, 'C')
    pdf.cell(25, 8, 'FR (irpm)', 1, 0, 'C')
    pdf.cell(25, 8, 'Temp (C)', 1, 1, 'C')
    
    pdf.set_font('helvetica', '', 8)
    for _, row in hist.iterrows():
        pdf.cell(25, 8, str(row['data']), 1, 0, 'C')
        pdf.cell(20, 8, str(row['hora']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['peso']:.2f}", 1, 0, 'C')
        pdf.cell(30, 8, str(row['pa']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fc']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fr']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['temp']:.1f}", 1, 1, 'C')
        
    # CORREÇÃO AQUI: Retornar como bytes() para evitar erro no Streamlit
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("🩺 Nefropediatria - HNSM")

tab1, tab2, tab3 = st.tabs(["🔢 Cadastro e Cálculos", "📋 Monitorização Diária", "🔎 Histórico e PDF"])

# --- TAB 1: CADASTRO E CÁLCULOS ---
with tab1:
    with st.form("cadastro"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Paciente").upper()
        leito = col2.text_input("Leito")
        data_adm = st.date_input("Data de Admissão", value=datetime.now())
        
        st.write("**Idade:**")
        c1, c2, c3 = st.columns(3)
        anos = c1.number_input("Anos", 0, 18, 5)
        meses = c2.number_input("Meses", 0, 11, 0)
        dias = c3.number_input("Dias", 0, 30, 0)
        sexo = st.radio("Sexo Biológico", ["Feminino", "Masculino"], horizontal=True)
        
        # Lógica Automatizada de K (Schwartz 1)
        # RN pré-termo: 0,33; RN a termo até 1 ano: 0,45; 
        # Crianças/Adolescentes (feminino): 0,55; Adolescentes (masculino): 0,70
        idade_meses = (anos * 12) + meses
        if idade_meses < 12:
            prematuro = st.checkbox("Nasceu prematuro?")
            k = 0.33 if prematuro else 0.45
        else:
            k = 0.70 if (sexo == "Masculino" and anos >= 13) else 0.55
            
        st.info(f"Constante K definida: {k}")
        
        p_seco = st.number_input("Peso na Admissão (kg)", 1.0, 150.0, 20.0)
        estat = st.number_input("Estatura (cm)", 30.0, 200.0, 110.0)
        creat = st.number_input("Creatinina (mg/dL)", 0.1, 10.0, 0.6)
        
        if st.form_submit_button("Salvar Cadastro e Calcular"):
            sc = math.sqrt((p_seco * estat) / 3600)
            tfge = (k * estat) / creat
            dose_at = min(sc * 60, 60.0)
            
            conn = sqlite3.connect('nefroped_merces.db')
            c = conn.cursor()
            c.execute("INSERT INTO pacientes (nome, leito, data_admissao, anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                      (nome, leito, data_adm.strftime("%d/%m/%Y"), anos, meses, dias, sexo, k, p_seco, estat, sc, tfge, dose_at))
            conn.commit()
            conn.close()
            st.success(f"Cadastro de {nome} realizado com sucesso!")

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
                st.success("Dados de monitorização salvos!")

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
            st.write("**Histórico de Monitorização:**")
            st.dataframe(hist[['data', 'hora', 'peso', 'pa', 'fc', 'fr', 'temp']])
            
            pdf_bytes = gerar_pdf(p_sel, hist)
            st.download_button(
                label="📥 Baixar PDF da Ficha de Monitorização",
                data=pdf_bytes,
                file_name=f"Ficha_Monitorizacao_{p_sel['nome']}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Paciente não encontrado.")
        conn.close()

# Sidebar de Alertas
with st.sidebar:
    st.error("🚨 **Sinais de Alerta - Quando chamar o Nefropediatra**")
    st.write("- Oligúria (< 1 mL/kg/h)\n- Hematúria Macroscópica\n- Crise Hipertensiva\n- Dor Abdominal (PBE)")
