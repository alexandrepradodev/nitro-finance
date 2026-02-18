# 💳 Nitro Finance

**Versão:** 1.0.0  
**Status:** MVP em desenvolvimento  

## 📌 Visão Geral
O **Nitro Finance** é um **sistema corporativo de gestão de despesas e assinaturas**, criado para centralizar, padronizar e auditar custos recorrentes e pontuais dentro de empresas.

O sistema resolve problemas comuns como:
- Cobranças indevidas por falta de cancelamento  
- Falta de visibilidade consolidada de gastos  
- Ausência de auditoria e rastreabilidade de decisões  
- Dificuldade de controle por empresa, setor e responsável  

O Nitro Finance força **governança financeira**, garantindo que toda despesa tenha responsável, validação periódica e histórico auditável.

---

## 🎯 Objetivos do Projeto
- Centralizar despesas corporativas em um único sistema  
- Gerenciar assinaturas recorrentes (SaaS, serviços, ferramentas)  
- Reduzir desperdícios financeiros  
- Criar rastreabilidade completa de decisões  
- Automatizar alertas de renovação e pendências  
- Facilitar análises financeiras e tomada de decisão  

---

## 🧩 Funcionalidades do MVP (V1)

### 🔹 Gestão de Despesas
- Cadastro de despesas recorrentes e não recorrentes  
- Classificação por empresa, setor, categoria e moeda  
- Controle de status (ativo, em cancelamento, cancelado)  

### 🔹 Validação Mensal
- Fluxo obrigatório de validação mensal por líderes  
- Registro automático de não validações  
- Histórico de confirmações e pendências  

### 🔹 Auditoria Automática
- Registro de todas as ações do sistema  
- Histórico completo de alterações  
- Rastreabilidade por usuário e data  

### 🔹 Alertas Inteligentes
- Alertas de renovação próxima  
- Alertas de pendências de validação  
- Notificações in-app (sem envio externo)  

### 🔹 Dashboards
- Visão consolidada de gastos  
- Totais por empresa, setor e categoria  
- Ranking das maiores despesas  
- Filtros avançados  

### 🔹 Controle de Acesso
- Permissões baseadas em perfil  
- Isolamento de dados por empresa e setor  

---

## 🔐 Perfis de Usuário

| Perfil | Permissões |
|------|-----------|
| **FinanceAdmin** | Acesso total, ativação e cancelamento de despesas |
| **SystemAdmin** | Acesso técnico e auditoria (dados sensíveis mascarados) |
| **Leader** | Validação mensal das despesas do seu setor |
| **User** | Criação de solicitações e acompanhamento |

---

## 📁 Estrutura do repositório

- **`backend/`** — API FastAPI (Python)
- **`frontend/`** — Interface React (Vite + TypeScript)

---

## 🚀 Início Rápido - Desenvolvimento Local

Para configurar o ambiente de desenvolvimento local, consulte o guia completo:

**[📖 SETUP_LOCALHOST.md](SETUP_LOCALHOST.md)**

### Resumo rápido:

1. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate no Windows
   pip install -r requirements.txt
   cp .env.example .env  # Configure suas credenciais do banco
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Acesse:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## 🛠️ Tecnologias Utilizadas

### Backend
- Python  
- FastAPI  
- JWT (JSON Web Tokens)  

### Frontend
- React (pasta `frontend/`)  

### Banco de Dados
- PostgreSQL  

### Infraestrutura
- Nuvem (infraestrutura existente)  
- Docker  

---