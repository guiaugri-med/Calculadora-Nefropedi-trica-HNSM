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
    # Tabela de pacientes e cálculos iniciais
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (id INTEGER PRIMARY KEY, nome TEXT, leito TEXT, data_admissao TEXT, 
                  anos INTEGER, meses INTEGER, dias INTEGER, sexo TEXT, k REAL, 
                  peso_seco REAL, estatura REAL, sc REAL, tfge REAL, dose_ataque REAL)''')
    # Tabela de monitorização diária
    c.execute('''CREATE TABLE IF NOT EXISTS monitorizacao 
                 (id INTEGER PRIMARY KEY, paciente_id INTEGER, data TEXT, hora TEXT, 
                  peso REAL, pa TEXT, fc INTEGER, fr INTEGER, temp REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Hospital Nossa Senhora das Mercês - Setor Pediatria', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Ficha de Monitorização Vascular e Metabólica', 0, 1, 'C')
        self.ln(10)

def gerar_pdf(dados_paciente, historico_clinico):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Cabeçalho do Paciente
    pdf.cell(0, 10, f"Nome: {dados_paciente['nome']} | Leito: {dados_paciente['leito']}", ln=True)
    pdf.cell(0, 10, f"Data de Admissão: {dados_paciente['data_admissao']} | SC: {dados_paciente['sc']:.2f} m2", ln=True)
    pdf.ln(5)
    
    # Tabela de Sinais Vitais
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(20, 10, 'Hora', 1)
    pdf.cell(30, 10, 'Peso (kg)', 1)
    pdf.cell(30, 10, 'PA (mmHg)', 1)
    pdf.cell(30, 10, 'FC (bpm)', 1)
    pdf.cell(30, 10, 'FR (irpm)', 1)
    pdf.cell(30, 10, 'Temp (C)', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 10)
    for _, row in historico_clinico.iterrows():
        pdf.cell(20, 10, str(row['hora']), 1)
        pdf.cell(30, 10, str(row['peso']), 1)
        pdf.cell(30, 10, str(row['pa']), 1)
        pdf.cell(30, 10, str(row['fc']), 1)
        pdf.cell(30, 10, str(row['fr']), 1)
        pdf.cell(30, 10, str(row['temp']), 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🩺 Gestão de Nefrologia Pediátrica")

aba_calc, aba_monitor, aba_busca = st.tabs(["🔢 Calculadora e Cadastro", "📋 Ficha de Monitorização", "🔎 Histórico de Pacientes"])

# --- ABA 1: CALCULADORA E CADASTRO ---
with aba_calc:
    with st.form("cadastro_paciente"):
        col_id1, col_id2 = st.columns(2)
        nome = col_id1.text_input("Nome do Doente")
        leito = col_id2.text_input("Leito")
        data_adm = st.date_input("Data de Admissão")
        
        st.divider()
        col_id3, col_id4, col_id5 = st.columns(3)
        anos = col_id3.number_input("Anos", 0, 18, 5)
        meses = col_id4.number_input("Meses", 0, 11, 0)
        dias = col_id5.number_input("Dias", 0, 30, 0)
        
        sexo = st.radio("Sexo Biológico", ["Feminino", "Masculino"], horizontal=True)
        
        # Lógica de K
        idade_meses = (anos * 12) + meses
        if idade_meses < 12:
            prematuro = st.checkbox("Nasceu prematuro?")
            k = 0.33 if prematuro else 0.45
        else:
            k = 0.70 if (sexo == "Masculino" and anos >= 13) else 0.55
            
        col_cli1, col_cli2, col_cli3 = st.columns(3)
        peso_seco = col_cli1.number_input("Peso na Admissão (kg)", 1.0, 150.0, 20.0)
        estatura = col_cli2.number_input("Estatura (cm)", 30.0, 200.0, 110.0)
        creatinina = col_cli3.number_input("Creatinina (mg/dL)", 0.1, 10.0, 0.6)
        
        btn_salvar = st.form_submit_button("Calcular e Salvar Cadastro")

    if btn_salvar:
        sc = math.sqrt((peso_seco * estatura) / 3600)
        tfge = (k * estatura) / creatinina
        dose_ataque = min(sc * 60, 60.0)
        
        conn = sqlite3.connect('nefroped_merces.db')
        c = conn.cursor()
        c.execute("INSERT INTO pacientes (nome, leito, data_admissao, anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                  (nome.upper(), leito, data_adm.strftime("%d/%m/%Y"), anos, meses, dias, sexo, k, peso_seco, estatura, sc, tfge, dose_ataque))
        conn.commit()
        conn.close()
        st.success(f"Paciente {nome} cadastrado com sucesso! SC: {sc:.2f} m² | TFGe: {tfge:.1f}")

# --- ABA 2: FICHA DE MONITORIZAÇÃO ---
with aba_monitor:
    conn = sqlite3.connect('nefroped_merces.db')
    lista_pacientes = pd.read_sql("SELECT id, nome, leito FROM pacientes", conn)
    conn.close()
    
    if not lista_pacientes.empty:
        escolha = st.selectbox("Selecione o Paciente para Evolução", 
                               lista_pacientes['nome'] + " (Leito: " + lista_pacientes['leito'] + ")")
        paciente_id = int(lista_pacientes[lista_pacientes['nome'] == escolha.split(" (")[0]]['id'].iloc[0])
        
        st.subheader("Inserir Sinais Vitais")
        with st.form("ficha_diaria"):
            col_f1, col_f2 = st.columns(2)
            data_sv = col_f1.date_input("Data do Registro")
            hora_sv = col_f2.selectbox("Hora", ["08:00", "14:00", "20:00"])
            
            col_f3, col_f4, col_f5, col_f6, col_f7 = st.columns(5)
            p_sv = col_f3.number_input("Peso (kg)", 0.0, 150.0)
            pa_sv = col_f4.text_input("PA (mmHg)", placeholder="110/70")
            fc_sv = col_f5.number_input("FC (bpm)", 0, 200)
            fr_sv = col_f6.number_input("FR (irpm)", 0, 60)
            t_sv = col_f7.number_input("Temp (ºC)", 30.0, 42.0, 36.5)
            
            btn_sv = st.form_submit_button("Salvar Registro")
            
        if btn_sv:
            conn = sqlite3.connect('nefroped_merces.db')
            c = conn.cursor()
            c.execute("INSERT INTO monitorizacao (paciente_id, data, hora, peso, pa, fc, fr, temp) VALUES (?,?,?,?,?,?,?,?)",
                      (paciente_id, data_sv.strftime("%d/%m/%Y"), hora_sv, p_sv, pa_sv, fc_sv, fr_sv, t_sv))
            conn.commit()
            conn.close()
            st.success("Sinais vitais registrados!")

# --- ABA 3: BUSCA E PDF ---
with aba_busca:
    nome_busca = st.text_input("Buscar paciente por nome").upper()
    if nome_busca:
        conn = sqlite3.connect('nefroped_merces.db')
        dados = pd.read_sql(f"SELECT * FROM pacientes WHERE nome LIKE '%{nome_busca}%'", conn)
        
        if not dados.empty:
            p_id = dados.iloc[0]['id']
            st.write(f"### Dados de: {dados.iloc[0]['nome']}")
            st.write(f"**Leito:** {dados.iloc[0]['leito']} | **SC:** {dados.iloc[0]['sc']:.2f} m²")
            
            historico = pd.read_sql(f"SELECT * FROM monitorizacao WHERE paciente_id = {p_id} ORDER BY data DESC, hora ASC", conn)
            st.table(historico[['data', 'hora', 'peso', 'pa', 'fc', 'fr', 'temp']])
            
            # Gerar PDF
            pdf_bytes = gerar_pdf(dados.iloc[0], historico)
            st.download_button(label="📥 Gerar e Baixar PDF", 
                               data=pdf_bytes, 
                               file_name=f"Ficha_{dados.iloc[0]['nome']}.pdf", 
                               mime="application/pdf")
            
            email_contato = st.text_input("Enviar para e-mail (opcional)")
            if st.button("Enviar por E-mail"):
                st.info("Funcionalidade de e-mail requer configuração de servidor SMTP. PDF disponível para download acima.")
        else:
            st.error("Paciente não encontrado.")
        conn.close()

# Sidebar de Alertas (Mantida)
with st.sidebar:
    st.error("🚨 **Sinais de Alerta (Red Flags)**")
    with st.expander("Quando chamar o Nefropediatra:"):
        st.write("""
        - **Oligúria/Anúria:** Débito urinário < 1 mL/kg/h.
        - **Hematúria Macroscópica.**
        - **Crise Hipertensiva.**
        - **Abdome Agudo (PBE).**
        """)
        
