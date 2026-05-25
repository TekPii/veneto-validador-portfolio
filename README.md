Olá, espero que este texto os encontre bem.

Envio, via links abaixo, a resolução do Case Técnico de Inteligência Comercial. Para esta entrega, adotei uma abordagem de desenvolvimento de software, buscando entregar não apenas a lógica, mas uma ferramenta funcional e escalável para o time de investimentos.

1. Acesso à Ferramenta (Validador Online):

https://veneto-validador-portfolio-fld8kwx9eyxn2s6afykbuf.streamlit.app/

Desenvolvi esta interface para que vocês possam testar a validação dos 6 portfólios sugeridos ou simular novos cenários de forma interativa e imediata.

2. Repositório (Código-Fonte):
https://github.com/TekPii/veneto-validador-portfolio/tree/main

Estrutura da Entrega:

Código-Fonte: Desenvolvido em Python. Temos o arquivo Veneto IA.py, que realiza a validação e um relatório dos portfólios. O arquivo app_veneto.py é a evolução da lógica inicial, e vai além! Oferecendo uma interface web com relatórios globais e gestão de dados. A base de dados (.db) e a Blacklist conectam-se diretamente à ferramenta, garantindo integridade nas verificações.

Uso_de_IA_Thiago_Chaves (PDF): Documentação detalhada sobre o processo de estruturação, as ferramentas de IA utilizadas e a metodologia de resolução adotada.

Relatório: Análise detalhada do enquadramento dos 6 portfólios estudados.

Coloco-me à disposição para detalhar qualquer ponto desta implementação ou discutir as escolhas estratégicas que tomei para resolver o problema proposto.

**PARA O BOM FUNCIONAMENTO É NECESSARIO TODOS OS ARQUIVOS ESTAREM JUNTOS EM UMA MESMA PAGINA**


PARA RODAR O CODIGO app_veneto.py segue o passo a passo:


1. Pré-requisitos:Ter o Python instalado na máquina (versão 3.8 ou superior).  Ter o VS Code instalado.  


2. Configuração do ambiente:Abra a pasta do projeto no seu terminal (ou no terminal integrado do VS Code)
Recomendado: Crie um ambiente virtual para isolar as dependências
Windows: python -m venv venv e depois venv\Scripts\activateMac/
Linux: python3 -m venv venv e depois source venv/bin/activate


Instale as bibliotecas necessárias rodando o comando:

pip install streamlit pandas plotly


3. Execução:Com o ambiente configurado, basta rodar o seguinte comando no terminal:

streamlit run app_veneto.py

O navegador abrirá automaticamente com o seu validador funcional. 

Para Rodar o CODIGO VENETO IA.py

Em seu VSCODE, clique no botão de Play no topo direito, e vá seguindo os passos no Terminal

Atenciosamente,

Thiago Chaves
