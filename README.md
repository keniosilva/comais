# Comais · Produção e Estoque

Sistema web para gestão de **produção e estoque de insumos** de uma fábrica de salgados de festa (Comais). MVP desenvolvido como projeto de extensão do curso de Análise e Desenvolvimento de Sistemas.

> **Status:** Incrementos 1, 2 e 3 implementados (login com bloqueio por tentativas, cadastros, encomenda, produção do dia, baixa de insumos, compra, alerta de mínimo e lista de entregas com status). Pendente: modo offline (PWA).

## Problema

A Comais já emite as notas dos pedidos, mas não registra a **produção** nem o **estoque de insumos**. O que produzir e o que comprar depende da memória do dono, que também faz as compras e as entregas. Isso gera falta de insumo, compras emergenciais e produção de última hora.

## Diferencial do MVP

A encomenda, registrada **por cento** e com data e hora de entrega, gera a lista de produção do dia e dá baixa nos insumos pela receita, sem lançamento manual. O sistema convive com o sistema de notas existente, sem substituí-lo.

## Público

- **Usuários diretos:** dono da empresa (celular, em movimento) e funcionária do escritório (computador).
- **Beneficiados indiretos:** equipe de produção, clientes e fornecedores.

## Escopo do MVP

| Código | Requisito | Prioridade |
|---|---|---|
| RF01 | Acesso por login | Obrigatório |
| RF02 | Cadastro de produtos e insumos | Obrigatório |
| RF03 | Cadastro de receita (insumo por cento) | Obrigatório |
| RF04 | Cadastro de encomenda | Obrigatório |
| RF05 | Lista de produção do dia | Obrigatório |
| RF06 | Baixa automática de insumos | Obrigatório |
| RF07 | Registro de compra de insumo | Obrigatório |
| RF08 | Alerta de estoque mínimo | Obrigatório |
| RF09 | Lista de entregas e status | Desejável |

**Fora do escopo:** emissão de notas fiscais, módulo financeiro, aplicativo nativo e portal do cliente.

## Arquitetura e tecnologias

Aplicação **monolítica em camadas** (apresentação, regras de negócio e dados), organizada em Model, View e Template.

| Recurso | Versão prevista | Função |
|---|---|---|
| Python | 3.12 | Linguagem principal |
| Django | 5.2 LTS | Framework web, ORM, autenticação, formulários e testes |
| MySQL | 8.0+ | Banco de dados (InnoDB, transações) |
| mysqlclient | a confirmar | Driver do MySQL |
| Gunicorn | a confirmar | Servidor de aplicação em produção |
| CSS próprio (`static/css/app.css`) | - | Interface responsiva, sem dependência externa |
| Service Worker | nativo | Modo offline e PWA (pendente) |

Confirme as versões nos sites oficiais antes de fixá-las em `requirements.txt`.

## Requisitos não funcionais

- **Segurança:** senhas com hash (PBKDF2 do Django), sessão protegida, validação no servidor, consultas pelo ORM, escape de saída, CSRF, segredos fora do código.
- **Desempenho:** abertura da tela de novo pedido em até 3 s e salvamento em até 2 s, medidos em rede móvel simples.
- **Acessibilidade:** área de toque mínima de 44 px, contraste AA, foco visível, rótulos persistentes e alertas por texto, símbolo e cor.

## Como rodar localmente

```bash
git clone <URL-DO-REPOSITORIO>
cd comais
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # preencha com valores locais (Windows: copy)
python manage.py migrate
python manage.py createsuperuser # acesso ao /admin/ (cadastros)
python manage.py seed_demo --senha "uma-senha-local"   # dados FICTÍCIOS (opcional)
python manage.py runserver
```

- Sistema: <http://127.0.0.1:8000/> · Administração (produtos, insumos, receitas, clientes, usuários): <http://127.0.0.1:8000/admin/>
- Sem `DB_NAME` no `.env`, o sistema usa SQLite local. Para MySQL, crie o banco e o usuário e preencha `DB_*`. O `mysqlclient` pode exigir as bibliotecas de desenvolvimento do MySQL no sistema.
- Perfis: **dono** (registra compras) e **escritório** (consulta e cadastra pedidos). O perfil é definido no cadastro do usuário em `/admin/`.

## Testes

```bash
python manage.py test
```

Cobrem: baixa de insumos pela receita, transação atômica (falha não grava nada), regras do pedido, soma da produção, compra, alerta de mínimo, sequência de status das entregas, bloqueio após 5 logins inválidos, acesso por perfil, escape de HTML, hash de senha e encerramento de sessão.

## Plano de entregas

1. **Incremento 1:** login, cadastros, encomenda e lista de produção.
2. **Incremento 2:** receitas, baixa de insumos, compras e alerta de mínimo.
3. **Incremento 3:** lista de entregas e status (desejável).

## Estrutura do repositório

```
comais/
├── config/          # configurações, URLs
├── contas/          # usuário com perfil (dono/escritório), permissões
├── catalogo/        # produtos, insumos, receitas (+ comando seed_demo)
├── pedidos/         # clientes, pedidos, itens; services.py (regras), forms, views, testes
├── estoque/         # movimentos; services.py (compra, baixa, alerta de mínimo)
├── templates/       # telas (login, menu, novo pedido, painel)
├── static/css/      # estilos
└── docs/            # requisitos, modelo de dados, protótipos e guia de implantação
```

As regras de negócio ficam em `services.py`; as views só validam a entrada e chamam os serviços; o acesso ao banco passa pelo ORM do Django.

## Dados e privacidade

Os dados de demonstração são fictícios. O sistema não coleta CPF, data de nascimento nem dados de pagamento. Segredos e credenciais ficam em variáveis de ambiente e nunca no repositório.

## Alinhamento com a Agenda 2030

ODS 8 (Trabalho Decente e Crescimento Econômico), meta 8.3: apoio à gestão de micro e pequenas empresas. A contribuição é local, restrita à gestão da Comais.

## Autor

Kenio do Nascimento Silva · Elétrica.com Projetos
