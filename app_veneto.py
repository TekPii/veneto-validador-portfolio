import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Vêneto Compliance",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# BANCO DE DADOS
# ==========================================
def inicializar_banco(nome_banco="veneto_portfolios.db"):

    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        perfil TEXT NOT NULL,
        patrimonio REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        classe TEXT NOT NULL,
        emissor TEXT NOT NULL,
        rating TEXT,
        vencimento TEXT,
        percentual REAL NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()


def salvar_portfolio_no_banco(portfolio, nome_banco="veneto_portfolios.db"):

    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO clientes (nome, perfil, patrimonio)
        VALUES (?, ?, ?);
        """, (
            portfolio["cliente"],
            portfolio["perfil"],
            portfolio["patrimonio"]
        ))

        cliente_id = cursor.lastrowid

        for ativo in portfolio["ativos"]:

            cursor.execute("""
            INSERT INTO ativos (
                cliente_id,
                nome,
                classe,
                emissor,
                rating,
                vencimento,
                percentual
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                cliente_id,
                ativo["nome"],
                ativo["classe"],
                ativo["emissor"],
                ativo["rating"],
                ativo["vencimento"],
                ativo["percentual"]
            ))

        conn.commit()

    except sqlite3.Error as e:

        st.error(f"Erro ao salvar no banco: {e}")
        conn.rollback()

    finally:
        conn.close()


def listar_clientes_banco(nome_banco="veneto_portfolios.db"):

    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, perfil
    FROM clientes;
    """)

    clientes = cursor.fetchall()

    conn.close()

    return clientes


def carregar_portfolio_do_banco(cliente_id, nome_banco="veneto_portfolios.db"):

    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome, perfil, patrimonio
    FROM clientes
    WHERE id = ?;
    """, (cliente_id,))

    dados_cliente = cursor.fetchone()

    if not dados_cliente:
        conn.close()
        return None

    cursor.execute("""
    SELECT nome, classe, emissor, rating, vencimento, percentual
    FROM ativos
    WHERE cliente_id = ?;
    """, (cliente_id,))

    linhas_ativos = cursor.fetchall()

    conn.close()

    ativos = []

    for linha in linhas_ativos:

        ativos.append({
            "nome": linha[0],
            "classe": linha[1],
            "emissor": linha[2],
            "rating": linha[3],
            "vencimento": linha[4],
            "percentual": linha[5]
        })

    return {
        "cliente": dados_cliente[0],
        "perfil": dados_cliente[1],
        "patrimonio": dados_cliente[2],
        "ativos": ativos
    }

# ==========================================
# REGRAS DE VALIDAÇÃO
# ==========================================
def validar_limites_classe(portfolio):

    violacoes = []

    alocacao = {
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 0,
        "7": 0
    }

    for ativo in portfolio["ativos"]:

        classe_id = ativo["classe"]

        if classe_id in alocacao:
            alocacao[classe_id] += ativo["percentual"]

    rf_total = alocacao["1"] + alocacao["2"]

    if rf_total < 20:
        violacoes.append(f"[Regra 2.1] Renda Fixa total é {rf_total}%. Mínimo: 20%.")

    if rf_total > 70:
        violacoes.append(f"[Regra 2.1] Renda Fixa total é {rf_total}%. Máximo: 70%.")

    if alocacao["1"] > 70:
        violacoes.append(f"[Regra 2.1] Renda Fixa Pública é {alocacao['1']}%. Máximo: 70%.")

    if alocacao["2"] > 30:
        violacoes.append(f"[Regra 2.1] Renda Fixa Privada é {alocacao['2']}%. Máximo: 30%.")

    if alocacao["3"] > 50:
        violacoes.append(f"[Regra 2.1] Renda Variável é {alocacao['3']}%. Máximo: 50%.")

    if alocacao["4"] > 30:
        violacoes.append(f"[Regra 2.1] Multimercado é {alocacao['4']}%. Máximo: 30%.")

    if alocacao["5"] > 20:
        violacoes.append(f"[Regra 2.1] FIIs representam {alocacao['5']}%. Máximo: 20%.")

    if alocacao["6"] > 5:
        violacoes.append(f"[Regra 2.1] Criptoativos representam {alocacao['6']}%. Máximo: 5%.")

    if alocacao["7"] < 5:
        violacoes.append(f"[Regra 2.1] Caixa é {alocacao['7']}%. Mínimo exigido: 5%.")

    return violacoes


def validar_concentracao_emissor(portfolio):

    violacoes = []

    emissores = {}

    for ativo in portfolio["ativos"]:

        emissor = ativo["emissor"].strip()
        classe = ativo["classe"]
        nome = ativo["nome"].strip()

        # Renda Fixa Pública e Tesouro Nacional: isentos do limite de concentração
        if classe == "1" or emissor.upper() == "TESOURO NACIONAL":
            continue

        # Caixa: isento
        if classe == "7":
            continue

        # Para fundos/ETFs sem emissor definido (classes 3, 4, 5, 6):
        # usa o nome do ativo como identificador, pois fundos individuais
        # estão sujeitos ao limite de 15% (Regra 2.2)
        if emissor in ("", "—", "-"):
            if classe in ("3", "4", "5", "6"):
                chave = nome  # trata o próprio fundo/ativo como emissor
            else:
                continue  # outros sem emissor: ignora
        else:
            chave = emissor

        emissores[chave] = emissores.get(chave, 0) + ativo["percentual"]

    for chave, percentual in emissores.items():

        if percentual > 15:

            violacoes.append(
                f"[Regra 2.2] Concentração em '{chave}' é {percentual:.1f}%. Máximo: 15%."
            )

    return violacoes


def validar_perfil_risco(portfolio):

    violacoes = []

    perfil = portfolio["perfil"].upper()

    rf_total = sum(
        a["percentual"]
        for a in portfolio["ativos"]
        if a["classe"] in ["1", "2"]
    )

    risco_total = sum(
        a["percentual"]
        for a in portfolio["ativos"]
        if a["classe"] in ["3", "5", "6"]
    )

    if perfil == "CONSERVADOR":

        if risco_total > 20:
            violacoes.append(
                f"[Regra 2.3] Perfil Conservador: Risco = {risco_total}%. Máximo: 20%."
            )

        if rf_total < 50:
            violacoes.append(
                f"[Regra 2.3] Perfil Conservador: RF = {rf_total}%. Mínimo: 50%."
            )

    elif perfil == "MODERADO":

        if risco_total > 40:
            violacoes.append(
                f"[Regra 2.3] Perfil Moderado: Risco = {risco_total}%. Máximo: 40%."
            )

    return violacoes


def validar_vencimentos(portfolio):

    violacoes = []

    limite_longo_prazo = datetime.strptime("2030-06-01", "%Y-%m-%d")

    limite_curto_prazo = datetime.strptime("2025-12-01", "%Y-%m-%d")

    rf_privada_longo = 0

    rf_total = 0

    rf_liquidez = 0

    # Acumula rf_total para todos os ativos de RF (com ou sem vencimento)
    for ativo in portfolio["ativos"]:
        if ativo["classe"] in ["1", "2"]:
            rf_total += ativo["percentual"]

    for ativo in portfolio["ativos"]:

        if not ativo["vencimento"] or str(ativo["vencimento"]) in ("None", "—", "-", ""):
            # RF Pública sem vencimento conta como líquida (título público = qualquer prazo)
            if ativo["classe"] == "1":
                rf_liquidez += ativo["percentual"]
            continue

        try:

            vencimento_ativo = datetime.strptime(
                str(ativo["vencimento"]),
                "%Y-%m-%d"
            )

        except:
            if ativo["classe"] == "1":
                rf_liquidez += ativo["percentual"]
            continue

        if (
            ativo["classe"] == "2"
            and vencimento_ativo > limite_longo_prazo
        ):
            rf_privada_longo += ativo["percentual"]

        if ativo["classe"] in ["1", "2"]:
            if (
                ativo["classe"] == "1"
                or vencimento_ativo < limite_curto_prazo
            ):
                rf_liquidez += ativo["percentual"]

    if rf_privada_longo > 10:

        violacoes.append(
            f"[Regra 2.4] RF Privada > 5 anos = {rf_privada_longo}%. Máximo: 10%."
        )

    if rf_total > 0:

        pct_liquidez = (rf_liquidez / rf_total) * 100

        if pct_liquidez < 50:

            violacoes.append(
                f"[Regra 2.4] Apenas {pct_liquidez:.2f}% da RF possui alta liquidez."
            )

    return violacoes


def validar_rating(portfolio):

    violacoes = []

    ratings_permitidos = [
        "AAA",
        "AA+",
        "AA",
        "AA-",
        "A+",
        "A",
        "A-"
    ]

    rf_privada_alto_risco = sum(
        a["percentual"]
        for a in portfolio["ativos"]
        if (
            a["classe"] == "2"
            and (
                not a["rating"]
                or a["rating"].strip().upper() not in ratings_permitidos
            )
        )
    )

    if rf_privada_alto_risco > 5:

        violacoes.append(
            f"[Regra 2.5] RF Privada com rating baixo soma {rf_privada_alto_risco}%."
        )

    return violacoes


def excluir_portfolio_do_banco(cliente_id, nome_banco="veneto_portfolios.db"):
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    try:
        cursor.execute("DELETE FROM clientes WHERE id = ?;", (cliente_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao excluir: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def validar_blacklist(portfolio):

    violacoes = []

    blacklist = [
        "BANCO XYZ RESTRITO",
        "FUNDO PROBLEMÁTICO ABC",
        "INCORPORADORA LMN"
    ]

    for ativo in portfolio["ativos"]:

        if ativo["emissor"].strip().upper() in blacklist:

            violacoes.append(
                f"[Regra 2.6] Ativo '{ativo['nome']}' reprovado. Emissor na blacklist."
            )

    return violacoes

# ==========================================
# INICIALIZAÇÃO
# ==========================================
inicializar_banco()

# ==========================================
# INTERFACE
# ==========================================
st.title("💼 Vêneto Family Office")

st.markdown("---")

opcoes_menu = [
    "🏠 Início",
    "➕ Cadastrar Novo Portfólio",
    "📊 Relatório Global Executivo",
    "🔎 Validar Portfólio Individual",
    "🗑️ Excluir Portfólio"
]

if "menu_nav" in st.session_state:
    st.session_state["menu_select"] = st.session_state.pop("menu_nav")

menu = st.sidebar.selectbox(
    "Navegação do Sistema",
    opcoes_menu,
    key="menu_select"
)

# ==========================================
# TELA INICIAL
# ==========================================
if menu == "🏠 Início":

    st.markdown("""
        <style>
            .home-title {
                font-size: 2.8rem;
                font-weight: 800;
                color: #1a1a2e;
                margin-bottom: 0.2rem;
            }
            .home-subtitle {
                font-size: 1.1rem;
                color: #555;
                margin-bottom: 2.5rem;
            }
            .card {
                background: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 16px;
                padding: 2rem 1.5rem;
                text-align: center;
                box-shadow: 0 2px 12px rgba(0,0,0,0.06);
                transition: transform 0.2s, box-shadow 0.2s;
                height: 100%;
            }
            .card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            }
            .card-icon {
                font-size: 2.8rem;
                margin-bottom: 0.8rem;
            }
            .card-title {
                font-size: 1.15rem;
                font-weight: 700;
                color: #1a1a2e;
                margin-bottom: 0.4rem;
            }
            .card-desc {
                font-size: 0.88rem;
                color: #777;
                line-height: 1.5;
            }
            .divider {
                border: none;
                border-top: 1px solid #eee;
                margin: 2rem 0;
            }
            .stat-box {
                background: #f7f9fc;
                border-radius: 12px;
                padding: 1.2rem 1rem;
                text-align: center;
            }
            .stat-num {
                font-size: 2rem;
                font-weight: 800;
                color: #1a1a2e;
            }
            .stat-label {
                font-size: 0.82rem;
                color: #888;
                margin-top: 0.2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="
            background: #fefaf0;
            border: 1px solid #d4a017;
            border-left: 5px solid #d4a017;
            border-radius: 8px;
            padding: 1.1rem 1.4rem;
            margin-bottom: 1.8rem;
            color: #4a3800;
        ">
            <div style="font-weight: 700; font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.4rem;">
                ⚠️ Aviso Importante — Uso Restrito
            </div>
            <div style="font-size: 0.9rem; line-height: 1.65;">
                Este sistema é um <strong>protótipo funcional</strong> desenvolvido exclusivamente para fins de avaliação técnica 
                no âmbito do processo seletivo da <strong>Vêneto Family Office</strong>. 
                Não possui qualquer vínculo oficial com a instituição, não opera com dados reais de clientes 
                e não deve ser utilizado para fins comerciais, regulatórios ou de assessoria de investimentos. 
                Todas as informações inseridas têm caráter meramente demonstrativo.
            </div>
        </div>
    """, unsafe_allow_html=True)
    clientes = listar_clientes_banco()
    total = len(clientes)
    enquadrados = 0
    desenquadrados = 0
    for c in clientes:
        p = carregar_portfolio_do_banco(c[0])
        if p:
            violacoes = []
            violacoes.extend(validar_limites_classe(p))
            violacoes.extend(validar_concentracao_emissor(p))
            violacoes.extend(validar_perfil_risco(p))
            violacoes.extend(validar_vencimentos(p))
            violacoes.extend(validar_rating(p))
            violacoes.extend(validar_blacklist(p))
            if not violacoes:
                enquadrados += 1
            else:
                desenquadrados += 1

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-num">{total}</div>
                <div class="stat-label">Portfólios cadastrados</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-num" style="color:#2e7d32;">✅ {enquadrados}</div>
                <div class="stat-label">Enquadrados</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-num" style="color:#c62828;">❌ {desenquadrados}</div>
                <div class="stat-label">Desenquadrados</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("### O que você deseja fazer?")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
            <div class="card">
                <div class="card-icon">➕</div>
                <div class="card-title">Cadastrar Portfólio</div>
                <div class="card-desc">Registre um novo cliente e seus ativos no sistema.</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ir para Cadastro", use_container_width=True):
            st.session_state["menu_nav"] = "➕ Cadastrar Novo Portfólio"
            st.rerun()

    with col2:
        st.markdown("""
            <div class="card">
                <div class="card-icon">🔎</div>
                <div class="card-title">Validar Portfólio</div>
                <div class="card-desc">Verifique o enquadramento de um cliente específico.</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ir para Validação", use_container_width=True):
            st.session_state["menu_nav"] = "🔎 Validar Portfólio Individual"
            st.rerun()

    with col3:
        st.markdown("""
            <div class="card">
                <div class="card-icon">📊</div>
                <div class="card-title">Relatório Global</div>
                <div class="card-desc">Visão executiva de todos os portfólios cadastrados.</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ir para Relatório", use_container_width=True):
            st.session_state["menu_nav"] = "📊 Relatório Global Executivo"
            st.rerun()

    with col4:
        st.markdown("""
            <div class="card">
                <div class="card-icon">🗑️</div>
                <div class="card-title">Excluir Portfólio</div>
                <div class="card-desc">Remova permanentemente um portfólio do banco de dados.</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ir para Exclusão", use_container_width=True):
            st.session_state["menu_nav"] = "🗑️ Excluir Portfólio"
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="
            border-top: 1px solid #2a2a2a;
            padding-top: 1.2rem;
            text-align: center;
            color: #555;
            font-size: 0.78rem;
            line-height: 1.8;
        ">
            Desenvolvido por <span style="color:#777; font-weight:600;">Thiago Chaves Pena de Oliveira Lopes</span>
            como parte do processo seletivo de estágio na Vêneto Family Office.<br>
            Graduando em <span style="color:#777;">Banco de Dados: Ênfase em Data Analytics</span> — PUCRS Online.
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# CADASTRO
# ==========================================
elif menu == "➕ Cadastrar Novo Portfólio":

    if st.button("← Voltar para o Início"):
        st.session_state["menu_nav"] = "🏠 Início"
        st.rerun()

    st.header("Cadastro de Novo Portfólio")


    classes = {
        "1": "Renda Fixa Pública",
        "2": "Renda Fixa Privada",
        "3": "Renda Variável",
        "4": "Multimercado",
        "5": "FIIs",
        "6": "Criptoativos",
        "7": "Caixa"
    }

    # Barra de progresso de alocação na sidebar
    qtd = int(st.session_state.get("qtd_ativos", 1))
    total_alocado = 0.0
    for i in range(qtd):
        val = st.session_state.get(f"percentual_{i}", "0%")
        try:
            total_alocado += float(str(val).replace("%", "").replace(",", ".").strip())
        except:
            pass

    total_alocado = min(total_alocado, 100.0)
    cor = "#2e7d32" if total_alocado == 100 else "#d4a017" if total_alocado >= 80 else "#1565c0"
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Alocação do Portfólio")
    st.sidebar.progress(int(total_alocado) / 100)
    st.sidebar.markdown(
        f"<div style='text-align:center; font-size:1.4rem; font-weight:700; color:{cor}'>"
        f"{total_alocado:.1f}% alocado</div>"
        f"<div style='text-align:center; font-size:0.82rem; color:#888;'>"
        f"{100 - total_alocado:.1f}% restante</div>",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")

    # Quantidade fora do form para atualizar os campos em tempo real
    quantidade_ativos = st.number_input(
        "Quantidade de Ativos",
        min_value=1,
        max_value=30,
        step=1,
        key="qtd_ativos"
    )

    nome_cliente = st.text_input("Nome do Cliente")

    perfil = st.selectbox(
        "Perfil de Risco",
        ["Conservador", "Moderado", "Arrojado"]
    )

    patrimonio_str = st.text_input(
        "Patrimônio Total (R$)",
        placeholder="Ex: 2.000.000,00"
    )

    st.markdown("---")
    st.subheader("Ativos")

    ativos = []

    for i in range(int(st.session_state.get("qtd_ativos", 1))):

        st.markdown(f"### Ativo {i+1}")

        nome_ativo = st.text_input(
            f"Nome do Ativo {i+1}",
            key=f"nome_{i}"
        )

        classe = st.selectbox(
            f"Classe do Ativo {i+1}",
            options=list(classes.keys()),
            format_func=lambda x: classes[x],
            key=f"classe_{i}"
        )

        emissor = st.text_input(
            f"Emissor {i+1}",
            key=f"emissor_{i}"
        )

        rating = st.text_input(
            f"Rating {i+1}",
            key=f"rating_{i}"
        )

        sem_vencimento = st.checkbox(
            "Sem data de vencimento",
            key=f"sem_venc_{i}"
        )

        if not sem_vencimento:
            vencimento = st.date_input(
                f"Vencimento {i+1}",
                key=f"vencimento_{i}"
            )
        else:
            vencimento = None

        percentual_str = st.text_input(
            f"Percentual do Ativo {i+1} (%)",
            value="0%",
            key=f"percentual_{i}"
        )

        try:
            percentual = float(
                percentual_str.replace("%", "").replace(",", ".").strip()
            )
        except ValueError:
            percentual = 0.0

        ativos.append({
            "nome": nome_ativo,
            "classe": classe,
            "emissor": emissor,
            "rating": rating,
            "vencimento": str(vencimento) if vencimento else None,
            "percentual": percentual
        })

    st.markdown("---")
    salvar = st.button("Salvar Portfólio", type="primary", use_container_width=True)

    if salvar:

        soma_percentuais = sum(ativo["percentual"] for ativo in ativos)

        try:
            patrimonio = float(
                patrimonio_str.strip()
                .replace("R$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            )
        except ValueError:
            patrimonio = None

        if patrimonio is None:
            st.error("❌ Patrimônio inválido. Use o formato: 2.000.000,00")

        elif soma_percentuais != 100:
            st.error(f"A soma dos percentuais deve ser 100%. Atual: {soma_percentuais}%")

        else:
            portfolio = {
                "cliente": nome_cliente,
                "perfil": perfil,
                "patrimonio": patrimonio,
                "ativos": ativos
            }

            salvar_portfolio_no_banco(portfolio)

            st.session_state["portfolio_salvo"] = portfolio["cliente"]
            st.rerun()

    if "portfolio_salvo" in st.session_state:
        nome_salvo = st.session_state.pop("portfolio_salvo")
        st.success(f"✅ Portfólio de **{nome_salvo}** cadastrado com sucesso!")

# ==========================================
# RELATÓRIO GLOBAL
# ==========================================
elif menu == "📊 Relatório Global Executivo":

    if st.button("← Voltar para o Início"):
        st.session_state["menu_nav"] = "🏠 Início"
        st.rerun()

    st.header("Visão Executiva")

    clientes = listar_clientes_banco()

    if not clientes:

        st.info("Nenhum portfólio cadastrado.")

    else:

        enquadrados = 0
        desenquadrados = 0

        detalhes_erros = []

        for c in clientes:

            portfolio = carregar_portfolio_do_banco(c[0])

            violacoes = []

            violacoes.extend(validar_limites_classe(portfolio))
            violacoes.extend(validar_concentracao_emissor(portfolio))
            violacoes.extend(validar_perfil_risco(portfolio))
            violacoes.extend(validar_vencimentos(portfolio))
            violacoes.extend(validar_rating(portfolio))
            violacoes.extend(validar_blacklist(portfolio))

            if not violacoes:

                enquadrados += 1

            else:

                desenquadrados += 1

                detalhes_erros.append({
                    "nome": portfolio["cliente"],
                    "erros": violacoes
                })

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(clientes))
        col2.metric("✅ Enquadrados", enquadrados)
        col3.metric("❌ Desenquadrados", desenquadrados)

        st.markdown("### Proporção de Enquadramento")

        # Separa nomes por status para o hover
        nomes_enquadrados = []
        nomes_desenquadrados = []

        for c in clientes:
            p = carregar_portfolio_do_banco(c[0])
            if p:
                v = []
                v.extend(validar_limites_classe(p))
                v.extend(validar_concentracao_emissor(p))
                v.extend(validar_perfil_risco(p))
                v.extend(validar_vencimentos(p))
                v.extend(validar_rating(p))
                v.extend(validar_blacklist(p))
                if not v:
                    nomes_enquadrados.append(p["cliente"])
                else:
                    nomes_desenquadrados.append(p["cliente"])

        hover_enq = "<br>".join(nomes_enquadrados) if nomes_enquadrados else "Nenhum"
        hover_des = "<br>".join(nomes_desenquadrados) if nomes_desenquadrados else "Nenhum"

        fig = go.Figure(data=[
            go.Bar(
                name="Enquadrados",
                x=["Enquadrados"],
                y=[enquadrados],
                marker_color="#2e7d32",
                text=[enquadrados],
                textposition="inside",
                textfont=dict(size=22, color="white"),
                width=0.35,
                hovertemplate=f"<b>✅ Enquadrados: {enquadrados}</b><br><br>{hover_enq}<extra></extra>",
            ),
            go.Bar(
                name="Desenquadrados",
                x=["Desenquadrados"],
                y=[desenquadrados],
                marker_color="#c62828",
                text=[desenquadrados],
                textposition="inside",
                textfont=dict(size=22, color="white"),
                width=0.35,
                hovertemplate=f"<b>❌ Desenquadrados: {desenquadrados}</b><br><br>{hover_des}<extra></extra>",
            )
        ])

        fig.update_layout(
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            xaxis=dict(tickfont=dict(size=15, color="#cccccc")),
            showlegend=False,
            hoverlabel=dict(bgcolor="#1e1e2e", font_size=13, font_color="white")
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if desenquadrados > 0:
            st.error("Existem portfólios desenquadrados.")
            for cliente_erro in detalhes_erros:
                with st.expander(f"❌ {cliente_erro['nome']} — {len(cliente_erro['erros'])} violação(ões)"):
                    for erro in cliente_erro["erros"]:
                        st.warning(erro)

        if enquadrados > 0:
            with st.expander(f"✅ Ver clientes enquadrados ({enquadrados})"):
                for c in clientes:
                    p = carregar_portfolio_do_banco(c[0])
                    if p:
                        v = []
                        v.extend(validar_limites_classe(p))
                        v.extend(validar_concentracao_emissor(p))
                        v.extend(validar_perfil_risco(p))
                        v.extend(validar_vencimentos(p))
                        v.extend(validar_rating(p))
                        v.extend(validar_blacklist(p))
                        if not v:
                            st.success(f"✅ {p['cliente']} — {p['perfil']}")

# ==========================================
# VALIDAÇÃO INDIVIDUAL
# ==========================================
elif menu == "🔎 Validar Portfólio Individual":

    if st.button("← Voltar para o Início"):
        st.session_state["menu_nav"] = "🏠 Início"
        st.rerun()

    st.header("Consulta Individual")

    clientes = listar_clientes_banco()

    if not clientes:

        st.info("Nenhum cliente cadastrado.")

    else:

        nomes_clientes = {
            f"ID: {c[0]} - {c[1]}": c[0]
            for c in clientes
        }

        escolha = st.selectbox(
            "Selecione o Cliente",
            list(nomes_clientes.keys())
        )

        if st.button(
            "Executar Validação",
            type="primary"
        ):

            cliente_id = nomes_clientes[escolha]

            portfolio = carregar_portfolio_do_banco(cliente_id)

            violacoes = []

            violacoes.extend(validar_limites_classe(portfolio))
            violacoes.extend(validar_concentracao_emissor(portfolio))
            violacoes.extend(validar_perfil_risco(portfolio))
            violacoes.extend(validar_vencimentos(portfolio))
            violacoes.extend(validar_rating(portfolio))
            violacoes.extend(validar_blacklist(portfolio))

            if not violacoes:

                st.success("✅ STATUS: ENQUADRADO")

            else:

                st.error("❌ STATUS: DESENQUADRADO")

                for i, erro in enumerate(violacoes, 1):

                    st.warning(f"{i}. {erro}")

            # Exibe o portfólio completo para análise
            st.markdown("---")
            st.markdown("### 📋 Portfólio Completo")

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Cliente", portfolio["cliente"])
            col_b.metric("Perfil", portfolio["perfil"])
            col_c.metric("Patrimônio", f"R$ {portfolio['patrimonio']:,.2f}")

            if portfolio["ativos"]:
                df_port = pd.DataFrame(portfolio["ativos"])
                df_port.columns = ["Nome", "Classe", "Emissor", "Rating", "Vencimento", "% Alocado"]
                df_port["Classe"] = df_port["Classe"].map({
                    "1": "Renda Fixa Pública",
                    "2": "Renda Fixa Privada",
                    "3": "Renda Variável",
                    "4": "Multimercado",
                    "5": "FIIs",
                    "6": "Criptoativos",
                    "7": "Caixa"
                }).fillna(df_port["Classe"])
                df_port["Vencimento"] = df_port["Vencimento"].apply(
                    lambda x: "—" if x in [None, "None", ""] else x
                )
                df_port["% Alocado"] = df_port["% Alocado"].apply(lambda x: f"{x:.1f}%")
                st.dataframe(df_port, use_container_width=True, hide_index=True)

# ==========================================
# EXCLUSÃO DE PORTFÓLIO
# ==========================================
elif menu == "🗑️ Excluir Portfólio":

    if st.button("← Voltar para o Início"):
        st.session_state["menu_nav"] = "🏠 Início"
        st.rerun()

    st.header("Excluir Portfólio")
    st.warning("⚠️ A exclusão é permanente e remove o cliente e todos os seus ativos do banco de dados.")

    clientes = listar_clientes_banco()

    if not clientes:
        st.info("Nenhum cliente cadastrado.")

    else:
        nomes_clientes = {
            f"ID: {c[0]} - {c[1]} ({c[2]})": c[0]
            for c in clientes
        }

        escolha = st.selectbox(
            "Selecione o portfólio que deseja excluir",
            list(nomes_clientes.keys())
        )

        cliente_id = nomes_clientes[escolha]

        # Mostra os dados do portfólio selecionado antes de excluir
        portfolio = carregar_portfolio_do_banco(cliente_id)

        if portfolio:
            with st.expander("📋 Dados do portfólio selecionado", expanded=True):
                st.markdown(f"**Cliente:** {portfolio['cliente']}")
                st.markdown(f"**Perfil:** {portfolio['perfil']}")
                st.markdown(f"**Patrimônio:** R$ {portfolio['patrimonio']:,.2f}")
                st.markdown(f"**Quantidade de ativos:** {len(portfolio['ativos'])}")

                if portfolio["ativos"]:
                    df_ativos = pd.DataFrame(portfolio["ativos"])
                    df_ativos.columns = ["Nome", "Classe", "Emissor", "Rating", "Vencimento", "% Alocado"]
                    st.dataframe(df_ativos, use_container_width=True)

        st.markdown("---")

        # Etapa de confirmação com digitação do nome
        st.markdown("**Para confirmar, digite o nome do cliente abaixo:**")
        confirmacao = st.text_input(
            "Nome do cliente",
            placeholder=portfolio["cliente"] if portfolio else ""
        )

        nome_correto = portfolio["cliente"].strip() if portfolio else ""
        confirmar_ativo = confirmacao.strip() == nome_correto and confirmacao.strip() != ""

        if confirmar_ativo:
            st.success(f"✅ Nome confirmado. Clique no botão para excluir.")

        elif confirmacao.strip() != "":
            st.error("❌ Nome incorreto. Verifique e tente novamente.")

        excluir = st.button(
            "🗑️ Excluir Portfólio Permanentemente",
            type="primary",
            disabled=not confirmar_ativo
        )

        if excluir and confirmar_ativo:
            sucesso = excluir_portfolio_do_banco(cliente_id)
            if sucesso:
                st.success(f"✅ Portfólio de **{nome_correto}** excluído com sucesso!")
                st.rerun()