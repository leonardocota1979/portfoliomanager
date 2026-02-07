# Guia do Usuário

Este guia explica **o que cada tela faz** e como usar.

## Login
Objetivo: acessar o sistema com usuário/senha.

O que fazer:
1. Digite usuário e senha
2. Clique em **Entrar**

## Minhas Carteiras
Objetivo: listar e acessar todas as carteiras.

Funções:
- **Criar Nova Carteira**: inicia a configuração completa
- **Importar Portfólio**: abre a importação por OCR
- **Dashboard**: abre a carteira
- **Editar**: altera nome, valor total e moeda
- **Deletar**: remove a carteira e dados associados

## Configurar Portfólio
Objetivo: criar carteira do zero.

Passo 1:
- Nome, descrição, valor total e moeda

Passo 2:
- Escolher classes de ativos
- Adicionar classes personalizadas com o nome que quiser
- Remover classes não desejadas (desmarcando/removendo)
- Definir % meta por classe (total = 100%)

## Importar Portfólio (OCR)
Objetivo: importar posições a partir de prints.

Fluxo:
1. Escolha fonte (Schwab / Hardwallet)
2. Adicione print(s)
3. Revise pré-visualização
4. Confirme importação

O sistema:
- extrai ativos e quantidades
- busca preço em tempo real
- solicita classificação por classe quando necessário
- guarda mapeamento para futuros imports

## Dashboard
Objetivo: acompanhar alocação e rebalanceamento.

Funções principais:
- **Atualizar Preços**
- **Adicionar Ativo**
- **Editar Portfólio**
- **Templates (1,2,3)**

Seções:
1. Resumo do portfólio
2. Gráficos (pizza e bullet)
3. Classes com ativos detalhados

## Onde editar cada tela
- Login: `app/templates/login.html`
- Minhas Carteiras: `app/templates/portfolio_list.html`
- Configurar Portfólio: `app/templates/portfolio_setup.html`
- Importar Portfólio: `app/templates/portfolio_import.html`
- Dashboard T1: `app/templates/dashboard.html`
- Dashboard T2: `app/templates/dashboard_v2.html`
- Dashboard T3: `app/templates/dashboard_v3.html`

### Colunas da tabela
- **Qtd**: quantidade do ativo
- **Cotação**: preço atual
- **Valor**: quantidade × preço
- **% Atual / % Meta (Classe)**
- **% Atual / % Meta (Portfólio)**
- **Desvio**
- **Status** e **Comprar/Vender**

## Modais
### Adicionar Ativo
Campos:
- Ticker
- Nome
- Classe
- Quantidade (pode ser auto-calculada)
- % Meta da Classe

### Editar Ativo
Campos:
- Quantidade
- % Meta da Classe
- Preço manual (opcional)

### Editar Portfólio
Campos:
- Nome
- Valor total
- Moeda

## Administração (apenas admin)
URL:
```
/admin/users
```
Funções:
- Criar usuário
- Editar usuário
- Resetar senha
- Remover usuário
Nota:
- O link **Admin** aparece no menu superior apenas para usuários administradores.
