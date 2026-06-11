import streamlit as st
from CoolProp.CoolProp import PropsSI
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="Diagnóstico Técnico - Zé", layout="wide")

st.title("📟 Sistema de Diagnóstico Técnico Avançado - Zé")

# --- BLOCO DE IDENTIFICAÇÃO DO ATENDIMENTO (SEM HORÍMETRO E SEM CÓDIGO DE SERVIÇO) ---
st.subheader("📝 Dados do Atendimento / Ordem de Serviço")
col_cli1, col_cli2, col_cli3 = st.columns(3)
with col_cli1:
    nome_cliente = st.text_input("Nome do Cliente / Empresa:", value="Guaca")
with col_cli2:
    num_serie_maquina = st.text_input("Número de Série da Máquina:", value="123456789")
with col_cli3:
    tecnico_nome = st.text_input("Técnico Responsável:", value="José Bruno (Zé)")

st.divider()

# 1. SELEÇÃO DO FLUIDO REFRIGERANTE
gas = st.selectbox(
    "Escolha o Tipo de Fluido Refrigerante:",
    ["R507A", "R404A", "R22", "R134a"]
)

# 2. SELEÇÃO DO MODELO DO COMPRESSOR
modelo_compressor = st.selectbox(
    "Selecione o Modelo do Compressor:",
    [
        "Bitzer Duplo Estágio 30 HP (S6F-30.2Y)",
        "Bitzer Duplo Estágio 25 HP (S6G-25.2Y)",
        "Bitzer Duplo Estágio 20 HP (S4N-20.2Y)",
        "Bitzer Semi-Hermético 20 HP (4GE-23Y)",
        "Bitzer Semi-Hermético 15 HP (4HE-18Y)",
        "Bitzer Semi-Hermético 10 HP (4EES-4Y)",
        "Bitzer Semi-Hermético 5 HP (2EES-2Y)"
    ]
)

# --- BANCO DE DADOS ATUALIZADO: DADOS DE PLACA REAIS BITZER (380V) ---
if "Duplo Estágio" in modelo_compressor:
    if "30 HP" in modelo_compressor:
        corrente_max_sugerida = 106.0  
    elif "25 HP" in modelo_compressor:
        corrente_max_sugerida = 87.0   
    else: 
        corrente_max_sugerida = 66.0   
    
    t_lop_limite = -60.0  
    t_mop_limite = -25.0  
else:
    if "20 HP" in modelo_compressor:
        corrente_max_sugerida = 40.0   
    elif "15 HP" in modelo_compressor:
        corrente_max_sugerida = 32.0   
    elif "10 HP" in modelo_compressor:
        corrente_max_sugerida = 22.0   
    else: 
        corrente_max_sugerida = 12.0   
    
    t_lop_limite = -25.0
    t_mop_limite = 15.0

st.divider()

# 3. ENTRADAS DO FLUIDO REFRIGERANTE (MANÔMETROS / SENSORES)
st.subheader("🌡️ Parâmetros do Fluido Refrigerante")
col_alta, col_baixa = st.columns(2)
with col_alta:
    pressão_Alta = st.number_input("Pressão de Alta (PSI):", value=200.0, step=1.0)
    temp_liquido = st.number_input("Temp. Sensor Linha de Líquido (°C):", value=30.0, step=0.1)
with col_baixa:
    pressão_Baixa = st.number_input("Pressão de Baixa (PSI):", value=15.0, step=1.0) 
    temp_succao = st.number_input("Temp. Sensor Sucção / Retorno (°C):", value=-15.0, step=0.1)

st.divider()

# 4. ENTRADAS DO CIRCUITO DE ÁGUA
st.subheader("💧 Parâmetros do Circuito de Água (Condensador)")
col_a1, col_a2 = st.columns(2)
with col_a1:
    t_agua_entrada = st.number_input("Água - Entrada do Condensador (Vinda da Torre) (°C):", value=28.0, step=0.1)
with col_a2:
    t_agua_saida = st.number_input("Água - Saída do Condensador (Indo para a Torre) (°C):", value=33.0, step=0.1)

st.divider()

# 5. CAMPOS ELÉTRICOS E DESCARGA
st.subheader("⚡ Parâmetros Elétricos e Cabeçote")
col_e1, col_e2, col_e3 = st.columns(3)
with col_e1:
    tensao = st.number_input("Tensão Medida (V):", value=380.0, step=1.0)
with col_e2:
    corrente_leitura = st.number_input("Corrente de Leitura no Cabo (A):", value=75.0, step=0.1)
with col_e3:
    temp_descarga = st.number_input("Temp. no Tubo de Descarga (°C):", value=80.0, step=0.1)

st.divider()

# 6. STATUS DE PROTEÇÃO (PRESSOSTATO E NÍVEL DE ÓLEO)
st.subheader("🛡️ Travas de Segurança Mecânica")
col_p1, col_p2 = st.columns(2)
with col_p1:
    status_pressostato = st.radio("Status do Pressostato (Alta / Baixa):", ["✅ Contato Fechado (OK)", "🚨 Disparado / Aberto (Falha)"])
with col_p2:
    status_oleo = st.radio("Nível de Óleo no Visor / Sensor:", ["✅ Nível OK / Sensor Alinhado", "🚨 Nível Baixo / Alarme Ativo"])

st.divider()

# Inicializando as variáveis globais para os cálculos e PDF
SR, SH, taxa_compressao, delta_t_agua, approach_condensador = 0.0, 0.0, 0.0, 0.0, 0.0
t_celsius_alta, t_celsius_baixa = 0.0, 0.0
p_lop_str, p_mop_str = "-- PSI", "-- PSI"
texto_diag_gas = "Sem dados"
texto_diag_agua = "Sem dados"
status_envelope = "Sem dados"
status_eletrico = "Sem dados"
status_descarga = "Sem dados"

# --- BLOCO DE CÁLCULOS TÉCNICOS ---
try:
    p_abs_alta = pressão_Alta + 14.696
    p_abs_baixa = pressão_Baixa + 14.696
    taxa_compressao = p_abs_alta / p_abs_baixa

    t_celsius_alta = PropsSI('T', 'P', p_abs_alta * 6894.76, 'Q', 0, gas) - 273.15
    t_celsius_baixa = PropsSI('T', 'P', p_abs_baixa * 6894.76, 'Q', 0, gas) - 273.15

    SR = t_celsius_alta - temp_liquido
    SH = temp_succao - t_celsius_baixa

    delta_t_agua = t_agua_saida - t_agua_entrada
    approach_condensador = t_celsius_alta - t_agua_saida

    try:
        p_lop_psi = (PropsSI('P', 'T', t_lop_limite + 273.15, 'Q', 0, gas) / 6894.76) - 14.696
        p_lop_str = f"{max(0.1, p_lop_psi):.1f} PSI"
    except:
        p_lop_str = "Vacuo"

    try:
        p_mop_psi = (PropsSI('P', 'T', t_mop_limite + 273.15, 'Q', 0, gas) / 6894.76) - 14.696
        p_mop_str = f"{p_mop_psi:.1f} PSI"
    except:
        p_mop_str = "-- PSI"

    # --- EXIBIÇÃO DO PAINEL PRINCIPAL ---
    st.subheader("📊 Painel de Resultados Rápidos")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Subresfriamento (SR)", value=f"{SR:.1f} K")
        st.caption(f"Sat. Condensação: {t_celsius_alta:.1f}°C")
    with c2:
        st.metric(label="Superaquecimento (SH)", value=f"{SH:.1f} K")
        st.caption(f"Sat. Evaporação: {t_celsius_baixa:.1f}°C")
    with c3:
        st.metric(label="Taxa de Compressão", value=f"{taxa_compressao:.1f}:1")

    # --- SEÇÃO EXPLICATIVA DOS ÍNDICES DA ÁGUA ---
    st.write("---")
    st.markdown("**🔬 Índices de Troca Térmica da Água (Análise do Condensador):**")
    ca1, ca2 = st.columns(2)
    with ca1:
        st.metric(label="Delta T da Água (ΔT)", value=f"{delta_t_agua:.1f} K")
        st.info(
            "**Diferença de Temperatura (ΔT) da Água:**\n\n"
            "**Para que serve:** Mede a quantidade de calor que a água está conseguindo retirar do condensador "
            "e levar para a torre de resfriamento. Faixa ideal de trabalho: **3.0 K a 5.0 K**.\n\n"
            "**Análise de Campo:**\n"
            "* **ΔT menor que 3.0 K:** Significa que a água está passando rápido demais pelo condensador sem tempo de absorver calor, "
            "ou que as paredes dos tubos estão com incrustações (sujeira) impedindo a troca.\n"
            "* **ΔT maior que 5.0 K:** Indica falta de vazão de água (bomba fraca, tubulação obstruída ou filtro Y entupido). A água fica "
            "retida no condensador e esquenta demais.\n\n"
            "**Como resolver:** Se o ΔT estiver alto, limpe o filtro Y e cheque o alinhamento da bomba. Se estiver muito baixo com o approach alto, faça o varetamento químico."
        )
    with ca2:
        st.metric(label="Approach do Condensador", value=f"{approach_condensador:.1f} K")
        st.info(
            "**Abordagem (Approach) do Condensador:**\n\n"
            "**Para que serve:** Mede a eficiência real da troca térmica entre o fluido refrigerante e a água de resfriamento. "
            "É a diferença entre a temperatura de saturação do gás (Alta) e a temperatura de saída da água. Faixa ideal: **2.0 K a 4.5 K**.\n\n"
            "**Análise de Campo:**\n"
            "* **Approach maior que 4.5 K:** É o indicador definitivo de **Condensador Sujo / Incrustado**. Mesmo com a água saindo fria, o gás não "
            "consegue transferir calor para ela, elevando a pressão de alta de forma crítica.\n"
            "* **Approach menor que 2.0 K:** Troca perfeita (condensador limpo e vazão de água excelente).\n\n"
            "**Como resolver:** Se o valor passar de 4.5 K, o sistema exige manutenção preventiva imediata através de limpeza química "
            "ou varetamento mecânico dos tubos para remover o isolamento térmico causado pelo lodo/calcário."
        )

    # Limites de Envelope
    st.write("---")
    st.markdown(f"**📐 Limites de Envelope Ativos ({modelo_compressor}):**")
    clop, cmop = st.columns(2)
    with clop:
        st.metric(label="LOP Limite (Mínimo de Baixa)", value=f"{t_lop_limite:.1f} °C", delta=f"({p_lop_str})", delta_color="off")
    with cmop:
        st.metric(label="MOP Limite (Máximo na Partida)", value=f"{t_mop_limite:.1f} °C", delta=f"({p_mop_str})", delta_color="off")

    # --- TEXTOS TRATADOS PARA O DIAGNÓSTICO ---
    sh_alto = SH > 12.0
    sh_baixo = SH < 7.0
    sr_alto = SR > 7.0
    sr_baixo = SR < 3.0

    st.divider()
    st.header("📋 Diagnóstico de Operação do Gás")
    if sh_alto and sr_baixo:
        texto_diag_gas = "ALERTA: FALTA DE REFRIGERANTE -> ADICIONAR FLUIDO REFRIGERANTE"
        st.error(f"🚨 DIAGNÓSTICO: {texto_diag_gas}")
    elif sh_baixo and sr_alto:
        texto_diag_gas = "ALERTA: EXCESSO DE REFRIGERANTE -> RETIRAR / RECOLHER FLUIDO REFRIGERANTE"
        st.error(f"🚨 DIAGNÓSTICO: {texto_diag_gas}")
    elif sh_baixo and sr_baixo:
        texto_diag_gas = "ALERTA: COMPRESSOR INEFICIENTE MECANICAMENTE -> REVISAR PLACAS DE VALVULA / PISTOES"
        st.error(f"🚨 DIAGNÓSTICO: {texto_diag_gas}")
    elif sh_alto:
        texto_diag_gas = "AVISO: VALVULA DE EXPANSAO MUITO FECHADA -> ABRIR A VALVULA DE EXPANSAO"
        st.warning(f"⚠️ DIAGNÓSTICO: {texto_diag_gas}")
    elif sh_baixo:
        texto_diag_gas = "ALERTA: VALVULA DE EXPANSAO MUITO ABERTA -> FECHAR A VALVULA DE EXPANSAO (PERIGO DE GOLPE)"
        st.error(f"🚨 DIAGNÓSTICO: {texto_diag_gas}")
    else:
        texto_diag_gas = "Sistema de fluido refrigerante operando com parametros normais e equilibrados."
        st.success(f"✅ {texto_diag_gas}")

    # --- DIAGNÓSTICO HIDRÁULICO ---
    st.divider()
    st.header("💧 Diagnóstico Hidráulico (Condensador e Torre)")
    if approach_condensador > 4.5:
        texto_diag_agua = "ALERTA: CONDENSADOR SUJO / INCRUSTADO! -> FAZER LIMPEZA / QUIMICA OU VARETAR"
        st.error(f"🚨 DIAGNÓSTICO: {texto_diag_agua}")
    elif delta_t_agua < 3.0:
        texto_diag_agua = "AVISO: AGUA PASSANDO MUITO RAPIDA (OU CONDENSADOR SUJO) -> REDUZIR VAZAO DA BOMBA"
        st.warning(f"⚠️ DIAGNÓSTICO: {texto_diag_agua}")
    elif delta_t_agua > 7.0:
        texto_diag_agua = "AVISO: BAIXO FLUXO DE AGUA NO CONDENSADOR -> VERIFICAR BOMBA / LIMPAR FILTRO Y"
        st.warning(f"⚠️ DIAGNÓSTICO: {texto_diag_agua}")
    else:
        texto_diag_agua = "CONDENSACAO EXCELENTE: Fluxo de agua e troca termica do condensador estao otimos!"
        st.success(f"✅ {texto_diag_agua}")

    # --- PAINEL DE PROTEÇÃO ATIVA ---
    st.divider()
    st.header("🚨 Monitoramento e Alertas Ativos")

    if t_celsius_baixa < t_lop_limite:
        status_envelope = f"ALERTA LOP: Temperatura de Evaporacao ({t_celsius_baixa:.1f} C) abaixo do limite ({t_lop_limite:.1f} C)! Risco de vacuo."
        st.error(f"🚨 {status_envelope}")
    elif t_celsius_baixa > t_mop_limite:
        status_envelope = f"ALERTA MOP: Temperatura de Evaporacao ({t_celsius_baixa:.1f} C) acima do limite MOP ({t_mop_limite:.1f} C)! Risco de sobrecarga."
        st.warning(f"⚠️ {status_envelope}")
    else:
        status_envelope = f"Temperatura de Saturacao da Baixa em {t_celsius_baixa:.1f} C. (Dentro do envelope seguro)."
        st.success(f"✅ {status_envelope}")
    
    if corriente_leitura > corrente_max_sugerida:
        status_eletrico = f"ALERTA ELETRICO: Compressor em Sobrecarga! Corrente medida ({corrente_leitura:.1f} A) passou o limite de placa de {corrente_max_sugerida} A!"
        st.error(f"🚨 {status_eletrico}")
    else:
        status_eletrico = f"Eletrica Normal: Maior corrente lida esta em {corrente_leitura:.1f} A. [Limite de Placa Real: {corrente_max_sugerida} A]"
        st.success(f"⚡ {status_eletrico}")

    if temp_descarga > 110.0:
        status_descarga = f"ALERTA VERMELHO CRITICO: Temperatura de Descarga em {temp_descarga:.1f} C! Risco de quebra mecanica."
        st.error(f"🚨 {status_descarga}")
    elif 90.0 < temp_descarga <= 110.0:
        status_descarga = f"ALERTA AMARELO: Temperatura de Descarga Elevada ({temp_descarga:.1f} C)."
        st.warning(f"⚠️ {status_descarga}")
    elif temp_descarga < 50.0:
        status_descarga = f"ALERTA: Temperatura de Descarga Baixa ({temp_descarga:.1f} C). Risco de retorno de liquido."
        st.error(f"🚨 {status_descarga}")
    else:
        status_descarga = f"Temperatura de Descarga em {temp_descarga:.1f} C. (Faixa segura de trabalho)."
        st.success(f"✅ {status_descarga}")

    if "Falha" in status_pressostato:
        st.error("🚨 BLOQUEIO: Pressostato aberto!")
    if "Alarme Ativo" in status_oleo:
        st.error("🚨 CRÍTICO: Falha no Nível de Óleo no bloco Bitzer!")

except Exception as e:
    st.error("Erro no processamento dos cálculos principais.")

# --- PARECER TÉCNICO COMPLETO DE CAMPO ---
st.divider()
st.subheader("✍️ Parecer Técnico / Observações Adicionais de Campo")
texto_parecer = st.text_area(
    "Digite sua avaliação visual ou observações de problemas encontrados na máquina:",
    value="Equipamento operando sob carga. Filtros limpos e pressões reguladas de acordo com as especificações recomendadas."
)

# ==============================================================================
# SEÇÃO DO PDF ATUALIZADA (SEM HORÍMETRO E SEM CÓDIGO DE SERVIÇO)
# ==============================================================================
def gerar_pdf_completo_bytes():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", size=10)
    
    def purificar(texto):
        subs = [
            ("⚡", ""), ("✅", ""), ("🚨", ""), ("⚠️", ""), ("📟", ""), 
            ("📊", ""), ("🌡️", ""), ("🔬", ""), ("📐", ""), ("📋", ""), 
            ("💧", ""), ("°", " "), ("→", "->"), ("á", "a"), ("é", "e"), 
            ("í", "i"), ("ó", "o"), ("ú", "u"), ("ã", "a"), ("õ", "o"), 
            ("ç", "c"), ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), 
            ("Ú", "U"), ("Ã", "A"), ("Õ", "O"), ("Ç", "C"), ("Δ", "Delta "),
            ("\n", " ")
        ]
        t = str(texto)
        for original, substituto in subs:
            t = t.replace(original, substituto)
        return t

    # Cabeçalho do Laudo
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(180, 10, txt=purificar("LAUDO TECNICO DE DIAGNOSTICO AVANCADO"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(180, 5, txt=purificar(f"Data/Hora de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M')}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # 1. Identificação do Atendimento (Sem Código de Serviço)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("1. Identificacao do Atendimento e Equipamento"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    pdf.cell(90, 6, txt=purificar(f"Cliente / Empresa: {nome_cliente}"))
    pdf.cell(90, 6, txt=purificar(f"Numero de Serie da Maquina: {num_serie_maquina}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Compressor Analisado: {modelo_compressor}"))
    pdf.cell(90, 6, txt=purificar(f"Tecnico Responsavel: {tecnico_nome}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Fluido Refrigerante: {gas}"))
    pdf.cell(90, 6, txt=purificar(f"Tensao de Trabalho Relatada: {tensao} V"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # 2. Parâmetros Termodinâmicos (Gás)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("2. Parametros do Ciclo de Refrigeracao (Gas)"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    pdf.cell(90, 6, txt=purificar(f"Pressao de Alta: {pressão_Alta} PSI"))
    pdf.cell(90, 6, txt=purificar(f"Pressao de Baixa: {pressão_Baixa} PSI"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Sat. Condensacao: {t_celsius_alta:.1f} C"))
    pdf.cell(90, 6, txt=purificar(f"Sat. Evaporacao: {t_celsius_baixa:.1f} C"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Temp. Sensor Linha Liquido: {temp_liquido} C"))
    pdf.cell(90, 6, txt=purificar(f"Temp. Sensor Retorno/Succao: {temp_succao} C"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 7, txt=purificar(f"Subresfriamento (SR): {SR:.1f} K"))
    pdf.cell(60, 7, txt=purificar(f"Superaquecimento (SH): {SH:.1f} K"))
    pdf.cell(60, 7, txt=purificar(f"Taxa de Compressao: {taxa_compressao:.1f}:1"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 3. Parâmetros de Condensação e Hidráulica
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("3. Circuito Hidraulico e Troca Termica (Condensador)"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    pdf.cell(90, 6, txt=purificar(f"Agua - Entrada do Condensador: {t_agua_entrada} C"))
    pdf.cell(90, 6, txt=purificar(f"Agua - Saida do Condensador: {t_agua_saida} C"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Delta T da Agua (DT): {delta_t_agua:.1f} K"))
    pdf.cell(90, 6, txt=purificar(f"Approach do Condensador: {approach_condensador:.1f} K"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 4. Envelopes e Travas de Segurança Mecânica
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("4. Limites de Envelope e Travas de Seguranca"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    pdf.cell(90, 6, txt=purificar(f"Limite LOP Ativo: {t_lop_limite:.1f} C ({p_lop_str})"))
    pdf.cell(90, 6, txt=purificar(f"Limite MOP Ativo: {t_mop_limite:.1f} C ({p_mop_str})"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 6, txt=purificar(f"Status Pressostato: {status_pressostato}"))
    pdf.cell(90, 6, txt=purificar(f"Status Nivel de Oleo: {status_oleo}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # 5. Diagnósticos Completos Coletados
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("5. Diagnostico e Alertas Computados"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(180, 5, txt=purificar("Analise Termica do Gas:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(180, 5, txt=purificar(texto_diag_gas))
    pdf.ln(1)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(180, 5, txt=purificar("Analise do Condensador / Hidraulica:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(180, 5, txt=purificar(texto_diag_agua))
    pdf.ln(1)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(180, 5, txt=purificar("Status de Monitoramento de Protecoes:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(180, 5, txt=purificar(f"Envelope: {status_envelope}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(180, 5, txt=purificar(f"Eletrica: {status_eletrico}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(180, 5, txt=purificar(f"Descarga: {status_descarga}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # 6. Parecer do Especialista
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(180, 8, txt=purificar("6. Parecer do Tecnico / Observacoes de Campo"), new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)
    pdf.multi_cell(180, 5, txt=purificar(texto_parecer))
    
    # Seção de Assinaturas
    pdf.ln(12)
    pos_y = pdf.get_y()
    if pos_y > 230:
        pdf.add_page()
        pos_y = pdf.get_y() + 10
    pdf.line(20, pos_y + 12, 85, pos_y + 12)
    pdf.line(110, pos_y + 12, 175, pos_y + 12)
    pdf.set_y(pos_y + 14)
    pdf.set_x(20)
    pdf.cell(65, 5, txt=purificar("Tecnico Responsavel"), align="C")
    pdf.set_x(110)
    pdf.cell(65, 5, txt=purificar("Cliente / Supervisor"), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf_out = pdf.output()
    if isinstance(pdf_out, bytes):
        return pdf_out
    return bytes(pdf_out)

# --- BOTÃO DE EMISSÃO DO LAUDO ---
st.divider()
try:
    pdf_pronto_bytes = gerar_pdf_completo_bytes()
    st.download_button(
        label="💾 GERAR E SALVAR LAUDO DIAGNÓSTICO EM PDF",
        data=pdf_pronto_bytes,
        file_name=f"Laudo_Tecnico_{nome_cliente}_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
except Exception as e:
    st.error(f"Erro ao estruturar o arquivo PDF para download: {e}")
  
