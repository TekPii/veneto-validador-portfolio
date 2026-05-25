import os
import sqlite3
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO E CRIAÇÃO DO BANCO DE DADOS
# ==========================================
def inicializar_banco(nome_banco="veneto_portfolios.db"):
    """ Cria o arquivo de banco de dados e as tabelas caso não existam. """
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    
    # Habilita o suporte a chaves estrangeiras no SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Tabela de Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        perfil TEXT NOT NULL,
        patrimonio REAL NOT NULL
    );
    """)
    
    # Tabela de Ativos (Relacionamento 1:N com Clientes)
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
    """ Insere os dados do dicionário estruturado diretamente nas tabelas SQL. """
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    
    try:
        # 1. Insere o Cliente
        cursor.execute("""
        INSERT INTO clientes (nome, perfil, patrimonio) 
        VALUES (?, ?, ?);
        """, (portfolio["cliente"], portfolio["perfil"], portfolio["patrimonio"]))
        
        cliente_id = cursor.lastrowid # Captura o ID gerado automaticamente
        
        # 2. Insere os Ativos vinculados ao ID do Cliente
        for ativo in portfolio["ativos"]:
            cursor.execute("""
            INSERT INTO ativos (cliente_id, nome, classe, emissor, rating, vencimento, percentual)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (cliente_id, ativo["nome"], ativo["classe"], ativo["emissor"], 
                  ativo["rating"], ativo["vencimento"], ativo["percentual"]))
            
        conn.commit()
        print(f"\n💾 [SQL] Portfólio de '{portfolio['cliente']}' salvo com sucesso no banco de dados!")
    except sqlite3.Error as e:
        print(f"\n❌ Erro ao salvar no banco de dados: {e}")
        conn.rollback()
    finally:
        conn.close()

def listar_clientes_banco(nome_banco="veneto_portfolios.db"):
    """ Retorna a lista de clientes cadastrados no banco para o menu de seleção. """
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, perfil FROM clientes;")
    clientes = cursor.fetchall()
    conn.close()
    return clientes

def carregar_portfolio_do_banco(cliente_id, nome_banco="veneto_portfolios.db"):
    """ Consulta o banco via SQL e reconstrói o dicionário para o validador. """
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    
    # Busca dados do cliente
    cursor.execute("SELECT nome, perfil, patrimonio FROM clientes WHERE id = ?;", (cliente_id,))
    dados_cliente = cursor.fetchone()
    
    if not dados_cliente:
        conn.close()
        return None
        
    # Busca ativos associados
    cursor.execute("SELECT nome, classe, emissor, rating, vencimento, percentual FROM ativos WHERE cliente_id = ?;", (cliente_id,))
    linhas_ativos = cursor.fetchall()
    conn.close()
    
    # Reconstrói a estrutura interna do portfólio
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
# FUNÇÕES DE CAPTURA DE DADOS (INTERFACE)
# ==========================================
def cadastrar_portfolio():
    print("\n" + "="*50)
    print(" NOVO CADASTRO DE PORTFÓLIO ")
    print("="*50)

    cliente = input("Digite o nome do Cliente (Ex: Família Riquetelli): ")
    
    print("\nPerfis disponíveis: 1 - Conservador | 2 - Moderado | 3 - Arrojado")
    opcao_perfil = input("Escolha o Perfil de Risco (1, 2 ou 3): ")
    perfis = {"1": "Conservador", "2": "Moderado", "3": "Arrojado"}
    perfil = perfis.get(opcao_perfil, "Moderado")
    
    while True:
        patrimonio_str = input(f"Digite o Patrimônio Total da {cliente} (R$): ")
        patrimonio_limpo = patrimonio_str.upper().replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            patrimonio = float(patrimonio_limpo)
            break
        except ValueError:
            print("❌ Erro: Digite um valor numérico válido (ex: 5100000 ou 5.100.000,00).")

    ativos = []
    total_percentual = 0.0

    while True:
        print(f"\n--- Adicionando ativo ({total_percentual}%/100% preenchido) ---")
        nome = input("Nome do Ativo (Ex: Tesouro IPCA+ 2028): ")
        
        print("\nClasses: \n1. Renda Fixa Pública \n2. Renda Fixa Privada \n3. Renda Variável \n4. Multimercado \n5. FIIs \n6. Criptoativos \n7. Caixa")
        classe = input("Digite o número da Classe do Ativo: ")
        
        emissor = input("Emissor (Ex: Tesouro Nacional, Banco Alfa): ")
        rating = input("Rating (Deixe em branco se não houver ou não se aplicar): ")
        vencimento = input("Data de Vencimento (Formato AAAA-MM-DD ou deixe em branco): ")
        
        while True:
            percentual_str = input("Percentual alocado neste ativo (%): ")
            percentual_limpo = percentual_str.replace("%", "").replace(" ", "").replace(",", ".")
            try:
                percentual = float(percentual_limpo)
                break
            except ValueError:
                print("❌ Erro: Digite um valor numérico válido (ex: 15 ou 15.5).")
                
        total_percentual += percentual

        ativos.append({
            "nome": nome,
            "classe": classe,
            "emissor": emissor,
            "rating": rating if rating else None,
            "vencimento": vencimento if vencimento.strip() != "" else None,
            "percentual": percentual
        })

        if total_percentual >= 100:
            print("\n✅ O portfólio atingiu 100% de alocação.")
            break
            
        continuar = input("\nDeseja adicionar mais um ativo? (S/N): ")
        if continuar.upper() != 'S':
            break

    portfolio = {
        "cliente": cliente,
        "perfil": perfil,
        "patrimonio": patrimonio,
        "ativos": ativos
    }
    
    # Salva automaticamente no banco após o término do preenchimento
    salvar_portfolio_no_banco(portfolio)
    return portfolio

# ==========================================
# REGRAS DE VALIDAÇÃO DE INVESTIMENTOS
# ==========================================
def validar_limites_classe(portfolio):
    violacoes = []
    alocacao = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0}
    for ativo in portfolio["ativos"]:
        classe_id = ativo["classe"]
        if classe_id in alocacao:
            alocacao[classe_id] += ativo["percentual"]
            
    rf_total = alocacao["1"] + alocacao["2"]
    
    if rf_total < 20: violacoes.append(f"[Regra 2.1] Renda Fixa total é {rf_total}%. Mínimo: 20%.")
    if rf_total > 70: violacoes.append(f"[Regra 2.1] Renda Fixa total é {rf_total}%. Máximo: 70%.")
    if alocacao["1"] > 70: violacoes.append(f"[Regra 2.1] Renda Fixa Pública é {alocacao['1']}%. Máximo: 70%.")
    if alocacao["2"] > 30: violacoes.append(f"[Regra 2.1] Renda Fixa Privada é {alocacao['2']}%. Máximo: 30%.")
    if alocacao["3"] > 50: violacoes.append(f"[Regra 2.1] Renda Variável é {alocacao['3']}%. Máximo: 50%.")
    if alocacao["4"] > 30: violacoes.append(f"[Regra 2.1] Multimercado é {alocacao['4']}%. Máximo: 30%.")
    if alocacao["5"] > 20: violacoes.append(f"[Regra 2.1] FIIs representam {alocacao['5']}%. Máximo: 20%.")
    if alocacao["6"] > 5: violacoes.append(f"[Regra 2.1] Criptoativos representam {alocacao['6']}%. Máximo: 5%.")
    if alocacao["7"] < 5: violacoes.append(f"[Regra 2.1] Caixa é {alocacao['7']}%. Mínimo exigido: 5%.")
    return violacoes

def validar_concentracao_emissor(portfolio):
    violacoes = []
    emissores = {}
    for ativo in portfolio["ativos"]:
        emissor = ativo["emissor"].strip()
        classe = ativo["classe"]
        
        # Ignora Títulos Públicos, Caixa (classe 7) ou ativos onde o emissor foi deixado em branco
        if classe == "1" or emissor.upper() == "TESOURO NACIONAL" or classe == "7" or emissor == "":
            continue
            
        emissores[emissor] = emissores.get(emissor, 0) + ativo["percentual"]
        
    for emissor, percentual in emissores.items():
        if percentual > 15:
            violacoes.append(f"[Regra 2.2] Concentração no emissor '{emissor}' é {percentual}%. Máximo permitido é 15%.")
            
    return violacoes

def validar_perfil_risco(portfolio):
    violacoes = []
    perfil = portfolio["perfil"].upper()
    rf_total = sum(a["percentual"] for a in portfolio["ativos"] if a["classe"] in ["1", "2"])
    risco_total = sum(a["percentual"] for a in portfolio["ativos"] if a["classe"] in ["3", "5", "6"])
    
    if perfil == "CONSERVADOR":
        if risco_total > 20: violacoes.append(f"[Regra 2.3] Perfil Conservador: Risco (RV+FIIs+Cripto) = {risco_total}%. Máximo: 20%.")
        if rf_total < 50: violacoes.append(f"[Regra 2.3] Perfil Conservador: Renda Fixa total = {rf_total}%. Mínimo: 50%.")
    elif perfil == "MODERADO":
        if risco_total > 40: violacoes.append(f"[Regra 2.3] Perfil Moderado: Risco (RV+FIIs+Cripto) = {risco_total}%. Máximo: 40%.")
    return violacoes

def validar_vencimentos(portfolio):
    violacoes = []
    data_referencia = datetime.strptime("2025-06-01", "%Y-%m-%d")
    limite_longo_prazo = datetime.strptime("2030-06-01", "%Y-%m-%d")
    limite_curto_prazo = datetime.strptime("2025-12-01", "%Y-%m-%d")
    
    rf_privada_longo = 0
    rf_total = 0
    rf_liquidez = 0
    
    for ativo in portfolio["ativos"]:
        if not ativo["vencimento"] or ativo["vencimento"].strip() == "": continue
        try:
            vencimento_ativo = datetime.strptime(ativo["vencimento"], "%Y-%m-%d")
        except ValueError: continue
        
        if ativo["classe"] == "2" and vencimento_ativo > limite_longo_prazo:
            rf_privada_longo += ativo["percentual"]
                
        if ativo["classe"] in ["1", "2"]:
            rf_total += ativo["percentual"]
            if ativo["classe"] == "1" or vencimento_ativo < limite_curto_prazo:
                rf_liquidez += ativo["percentual"]
                
    if rf_privada_longo > 10:
        violacoes.append(f"[Regra 2.4] RF Privada > 5 anos = {rf_privada_longo}%. Máximo: 10%.")
    if rf_total > 0:
        pct_liquidez = (rf_liquidez / rf_total) * 100
        if pct_liquidez < 50:
            violacoes.append(f"[Regra 2.4] Apenas {pct_liquidez:.2f}% da RF possui alta liquidez. Mínimo: 50%.")
    return violacoes

def validar_rating(portfolio):
    violacoes = []
    ratings_permitidos = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-"]
    rf_privada_alto_risco = 0
    for ativo in portfolio["ativos"]:
        if ativo["classe"] == "2":
            rating = ativo["rating"]
            if not rating or rating.strip().upper() not in ratings_permitidos:
                rf_privada_alto_risco += ativo["percentual"]
                
    if rf_privada_alto_risco > 5:
        violacoes.append(f"[Regra 2.5] RF Privada com rating abaixo de 'A-' soma {rf_privada_alto_risco}%. Máximo: 5%.")
    return violacoes

def carregar_blacklist(caminho_arquivo="blacklist.txt"):
    blacklist = []
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                emissor = linha.strip().upper()
                if emissor: blacklist.append(emissor)
    else:
        emissores_padrao = ["BANCO XYZ RESTRITO", "FUNDO PROBLEMÁTICO ABC", "INCORPORADORA LMN"]
        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            for emissor in emissores_padrao:
                arquivo.write(emissor + "\n")
        blacklist = emissores_padrao
    return blacklist

def validar_blacklist(portfolio):
    violacoes = []
    blacklist_atualizada = carregar_blacklist()
    for ativo in portfolio["ativos"]:
        if ativo["emissor"].strip().upper() in blacklist_atualizada:
            violacoes.append(f"[Regra 2.6] Ativo '{ativo['nome']}' reprovado. Emissor na Blacklist.")
    return violacoes

# ==========================================
# MOTOR PRINCIPAL DE PROCESSAMENTO
# ==========================================
def processar_portfolio(portfolio):
        print("\n" + "="*60)
        print(f" RELATÓRIO DE ENQUADRAMENTO: {portfolio['cliente'].upper()} ")
        print("="*60)
        
        violacoes = []
        violacoes.extend(validar_limites_classe(portfolio))
        violacoes.extend(validar_concentracao_emissor(portfolio))
        violacoes.extend(validar_perfil_risco(portfolio))
        violacoes.extend(validar_vencimentos(portfolio))
        violacoes.extend(validar_rating(portfolio))
        violacoes.extend(validar_blacklist(portfolio))
        
        if not violacoes:
            print(">> STATUS: ENQUADRADO ✅")
            print("Nenhuma violação às regras da Política de Investimentos foi encontrada.")
        else:
            print(">> STATUS: DESENQUADRADO ❌")
            print(f"Foram encontradas {len(violacoes)} violação(ões):")
            for i, erro in enumerate(violacoes, 1):
                print(f"  {i}. {erro}")
                
        print("="*60 + "\n")
        
def gerar_relatorio_global():
            print("\n" + "="*60)
            print(" 📊 RELATÓRIO GLOBAL DE ENQUADRAMENTO - VÊNETO ")
            print("="*60)
            
            clientes = listar_clientes_banco()
            if not clientes:
                print("📭 Nenhum portfólio cadastrado no banco de dados para gerar o relatório.")
                return

            total_portfolios = len(clientes)
            enquadrados = 0
            desenquadrados = 0
            detalhes_erros = []

            for cliente in clientes:
                cliente_id = cliente[0]
                nome_cliente = cliente[1]
                portfolio = carregar_portfolio_do_banco(cliente_id)
                
                if portfolio:
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
                        detalhes_erros.append((nome_cliente, violacoes))

            # Exibição do Painel Executivo
            print(f"Total de Portfólios Analisados: {total_portfolios}")
            print(f"✅ Enquadrados: {enquadrados}")
            print(f"❌ Desenquadrados: {desenquadrados}")

            if desenquadrados > 0:
                print("\n--- DETALHAMENTO DOS DESENQUADRADOS ---")
                for nome, erros in detalhes_erros:
                    print(f"\nCliente: {nome.upper()}")
                    for i, erro in enumerate(erros, 1):
                        print(f"  {i}. {erro}")
            
            print("="*60 + "\n")

# ==========================================
# MENU INTERATIVO PRINCIPAL DO SISTEMA
# ==========================================
if __name__ == "__main__":
    inicializar_banco() # Garante que o banco e tabelas SQL existam ao ligar o app
    
    while True:
        print("\n" + "="*50)
        print(" SISTEMA DE COMPLIANCE - VÊNETO FAMILY OFFICE ")
        print("="*50)
        print("1. Cadastrar Novo Portfólio (Salva no Banco SQL)")
        print("2. Carregar e Validar Portfólio do Banco")
        print("3. Gerar Relatório Global (Visão Executiva)")
        print("4. Sair")
        
        opcao = input("\nEscolha uma opção (1, 2, 3 ou 4): ").strip()
        
        if opcao == "1":
            portfolio = cadastrar_portfolio()
            processar_portfolio(portfolio)
            
        elif opcao == "2":
            clientes = listar_clientes_banco()
            if not clientes:
                print("\n📭 Nenhum cliente cadastrado no banco de dados ainda.")
                continue
                
            print("\n--- Selecione um Cliente no Banco SQL ---")
            for c in clientes:
                print(f"ID: {c[0]} | Nome: {c[1]} | Perfil: {c[2]}")
                
            try:
                escolha_id = int(input("\nDigite o ID do cliente que deseja carregar: "))
                portfolio_carregado = carregar_portfolio_do_banco(escolha_id)
                
                if portfolio_carregado:
                    processar_portfolio(portfolio_carregado)
                else:
                    print("❌ ID não encontrado no banco de dados.")
            except ValueError:
                print("❌ Entrada inválida. Digite um número inteiro.")
                
        elif opcao == "3":
            gerar_relatorio_global()

        elif opcao == "4":
            print("\nEncerrando o sistema de Compliance. Até logo!")
            break
        else:
            print("❌ Opção inválida. Escolha entre 1, 2, 3 ou 4.")