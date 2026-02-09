import streamlit as st
import math
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="NefroPed - Mercês", page_icon="🩺", layout="wide")

def init_db():
    conn = sqlite3.connect('pacientes_merces.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS calculos 
                 (nome TEXT, data TEXT, idade_texto TEXT, peso REAL, sc REAL, tfge REAL, dose_ataque REAL)''')
    conn.commit()
    conn.close()

init_db()

def salvar_dados(nome, idade_txt, peso, sc, tfge, dose):
    conn = sqlite3.connect('pacientes_merces.db')
    c = conn.cursor()
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute("INSERT INTO calculos VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (nome.upper(), data_atual, idade_txt, peso, sc, tfge, dose))
    conn.commit()
    conn.close()

# --- FUNÇÃO GERAR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Hospital Nossa Senhora das Mercês - Setor Pediatria', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(dados_paciente, monitoramento=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Relatório de Síndrome Nefrótica Pediátrica", ln=True, align='C')
    pdf.ln(10)
    
    for key, value in dados_paciente.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    
    if monitoramento:
        pdf.ln(10)
        pdf.cell(200, 10, txt="Controle de Sinais Vitais", ln=True, align='L')
        # Tabela simples no PDF pode ser expandida aqui
        
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🩺 Gestão de Síndrome Nefrótica - Pediatria")

aba1, aba2, aba3 = st.tabs(["🔢 Calculadora", "📋 Ficha de Monitorização", "📂 Histórico"])

# --- ABA 1: CALCULADORA (Lógica Original) ---
with aba1:
    with st.sidebar:
        st.header("👤 Identificação")
        nome_paciente = st.text_input("Nome Completo do Paciente")
        leito = st.text_input("Leito")
        
        st.divider()
        st.header("📥 Dados Clínicos")
        c1, c2, c3 = st.columns(3)
        with c1: anos = st.number_input("Anos", 0, 18, 5)
        with c2: meses = st.number_input("Meses", 0, 11, 0)
        with c3: dias = st.number_input("Dias", 0, 30, 0)
        
        sexo = st.radio("Sexo Biológico", ["Feminino", "Masculino"])
        idade_total_meses = (anos * 12) + meses
        
        if idade_total_meses < 12:
            prematuro = st.toggle("Nasceu prematuro?")
            k_escolhido, categoria = (0.33, "RN Pré
