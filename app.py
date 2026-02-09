import streamlit as st
import math
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

# --- BANCO DE DADOS ---
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

# --- FUNÇÕES DE PDF (CORRIGIDA) ---
class PDF(FPDF):
    def header(self):
        # Título do Hospital e Setor conforme solicitado
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Ficha de Monitorização Vascular e Metabólica', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Setor: Pediatria - Hospital Nossa Senhora das Mercês', 0, 1, 'C')
        self.ln(10)

def gerar_pdf(dados, historico):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Cabeçalho do Paciente (Layout solicitado)
    pdf.cell(0, 8, f"Nome do Doente: {dados['nome']}", ln=True)
    pdf.cell(0, 8, f"Leito: {dados['leito']} | Data de Admissão: {dados['data_admissao']}", ln=True)
    pdf.cell(0, 8, f"Peso na Admissão (Seco): {dados['peso_seco']} kg | Superfície Corporal: {dados['sc']:.2f} m2", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "1. Controlo de Sinais Vitais e Antropometria", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, "Monitorizar a Pressão Arterial (PA) pelo menos 3x ao dia devido ao risco de hipertensão associada à corticoterapia e doença renal.")
    pdf.ln(5)
    
    # Tabela de Monitorização
    pdf.set_font('Arial', 'B', 9)
    cols = [('Data', 25), ('Hora', 20), ('Peso (kg)', 25), ('PA', 30), ('FC', 25), ('FR', 25), ('Temp', 25)]
    for name, width in cols:
        pdf.cell(width, 8, name, 1, 0, 'C')
    pdf.ln()
    
    pdf.set_font('Arial', size=9)
    for _, row in historico.iterrows():
        pdf.cell(25, 8, str(row['data']), 1, 0, 'C')
        pdf.cell(20, 8, str(row['hora']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['peso']:.2f}", 1, 0, 'C')
        pdf.cell(30, 8, str(row['pa']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fc']), 1, 0, 'C')
        pdf.cell(25, 8, str(row['fr']), 1, 0, 'C')
        pdf.cell(25, 8, f"{row['temp']:.1f}", 1, 0, 'C')
        pdf.ln()
        
    # O CORTE DO ERRO: Removido dest='S' e .encode()
    return pdf.output()

# --- INTERFACE ---
st.title("🩺 Gestão de Nefrologia Pediátrica")

aba_calc, aba_monitor, aba_busca = st.tabs(["🔢 Calculadora e Cadastro", "📋 Monitorização Diária", "🔎 Histórico e PDF"])

# --- ABA 1: CÁLCULO E CADASTRO ---
with aba_calc:
    with st.form("cadastro"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Doente").upper()
        leito = col2.text_input("Leito")
        data_adm = st.date_input("Data de Admissão", value=datetime.now())
        
        st.write("**Idade:**")
        c1, c2, c3 = st.columns(3)
        anos = c1.number_input("Anos", 0, 18, 5)
        meses = c2.number_input("Meses", 0, 11, 0)
        dias = c3.number_input("Dias", 0, 30, 0)
        
        sexo = st.radio("Sexo Biológico", ["Feminino", "Masculino"], horizontal=True)
        
        if (anos * 12 + meses) < 12:
            prematuro = st.checkbox("Nasceu prematuro?")
            k = 0.33 if prematuro else 0.45
        else:
            k = 0.70 if (sexo == "Masculino" and anos >= 13) else 0.55
            
        peso_seco = st.number_input("Peso na Admissão (kg)", 1.0, 150.0, 20.0)
        estatura = st.number_input("Estatura (cm)", 30.0, 200.0, 110.0)
        creatinina = st.number_input("Creatinina (mg/dL)", 0.1, 10.0, 0.6)
        
        if st.form_submit_button("Salvar Cadastro"):
            sc = math.sqrt((peso_seco * estatura) / 3600)
            tfge = (k * estatura) / creatinina
            dose_ataque = min(sc * 60, 60.0)
            
            conn = sqlite3.connect('nefroped_merces.db')
            c = conn.cursor()
            c.execute("INSERT INTO pacientes (nome, leito, data_admissao, anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                      (nome, leito, data_adm.strftime("%d/%m/%Y"), anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque))
            conn.commit()
            conn.close()
            st.success(f"Paciente {nome} salvo com sucesso!")

# --- ABA 2: MONITORIZAÇÃO ---
with aba_monitor:
    conn = sqlite3.connect('nefroped_merces.db')
    pacs = pd.read_sql("SELECT id, nome, leito FROM pacientes", conn)
    conn.close()
    
    if not pacs.empty:
        escolha = st.selectbox("Selecione o Paciente", pacs['nome'] + " (Leito: " + pacs['leito'] + ")")
        pac_id = int(pacs[pacs['nome'] == escolha.split(" (")[0]]['id'].iloc[0])
        
        with st.form("vitais"):
            c1, c2 = st.columns(2)
            d_sv = c1.date_input("Data")
            h_sv = c2.selectbox("Hora", ["08:00", "14:00", "20:00"])
            
            v1, v2, v3, v4, v5 = st.columns(5)
            p_v = v1.number_input("Peso (kg)", 0.0)
            pa_v = v2.text_input("PA (mmHg)")
            fc_v = v3.number_input("FC (bpm)", 0)
            fr_v = v4.number_input("FR (irpm)", 0)
            t_v = v5.number_input("Temp (C)", 30.0, 42.0, 36.5)
            
            if st.form_submit_button("Registrar Sinais Vitais"):
                conn = sqlite3.connect('nefroped_merces.db')
                c = conn.cursor()
                c.execute("INSERT INTO monitorizacao (paciente_id, data, hora, peso, pa, fc, fr, temp) VALUES (?,?,?,?,?,?,?,?)",
                          (pac_id, d_sv.strftime("%d/%m/%Y"), h_sv, p_v, pa_v, fc_v, fr_v, t_v))
                conn.commit()
                conn.close()
                st.success("Dados salvos!")

# --- ABA 3: BUSCA E PDF ---
with aba_busca:
    nome_b = st.text_input("Buscar por Nome").upper()
    if nome_b:
        conn = sqlite3.connect('nefroped_merces.db')
        pac_data = pd.read_sql(f"SELECT * FROM pacientes WHERE nome LIKE '%{nome_b}%'", conn)
        if not pac_data.empty:
            p_id = pac_data.iloc[0]['id']
            st.write(f"### {pac_data.iloc[0]['nome']}")
            
            hist = pd.read_sql(f"SELECT * FROM monitorizacao WHERE paciente_id = {p_id} ORDER BY data DESC, hora DESC", conn)
            st.dataframe(hist[['data', 'hora', 'peso', 'pa', 'fc', 'fr', 'temp']])
            
            pdf_out = gerar_pdf(pac_data.iloc[0], hist)
            st.download_button("📥 Baixar PDF da Ficha", data=pdf_out, file_name=f"Ficha_{nome_b}.pdf", mime="application/pdf")
        conn.close()

# Sidebar de Alertas
with st.sidebar:
    st.error("🚨 **Sinais de Alerta**")
    st.write("- Oligúria (< 1 mL/kg/h)\n- Hematúria Macroscópica\n- Crise Hipertensiva\n- Dor Abdominal (PBE)")
