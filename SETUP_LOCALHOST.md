# 🚀 Guia de Setup - Desenvolvimento Local

Este guia explica como configurar e executar o NitroSubs no ambiente de desenvolvimento local.

## 📋 Pré-requisitos

- **Python 3.12+** instalado
- **Node.js 20+** e npm instalados
- **PostgreSQL** rodando localmente (ou acesso a um banco remoto)
- **Git** instalado

---

## 🔧 Configuração do Backend

### 1. Criar ambiente virtual

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações locais:

```bash
# Banco de Dados Local
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_do_banco
DATABASE_SCHEMA=nitro_finance_dev

# JWT (use uma chave secreta forte em produção)
JWT_SECRET_KEY=dev_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# Cotação (não precisa alterar)
AWESOME_API_URL=https://economia.awesomeapi.com.br/json/last/USD-BRL

# CORS (não precisa definir em dev, já aceita localhost por padrão)
# CORS_ORIGINS=
```

**Importante:** 
- Substitua `usuario`, `senha` e `nome_do_banco` pelos seus dados do PostgreSQL
- O schema `nitro_finance_dev` será criado automaticamente pelo Alembic

### 4. Criar banco de dados

Conecte no PostgreSQL e crie o banco:

```sql
CREATE DATABASE nome_do_banco;
```

### 5. Rodar migrations

```bash
alembic upgrade head
```

Isso criará todas as tabelas no schema `nitro_finance_dev`.

### 6. Iniciar o servidor backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O backend estará disponível em: **http://localhost:8000**

API Docs: **http://localhost:8000/docs**

---

## 🎨 Configuração do Frontend

### 1. Instalar dependências

```bash
cd frontend
npm install
```

### 2. Configurar variáveis de ambiente

O frontend já está configurado para usar o proxy do Vite em desenvolvimento. Não é necessário criar `.env` para desenvolvimento local.

Se quiser criar um `.env` para referência:

```bash
# Em dev, o Vite faz proxy automático de /api para http://localhost:8000
# Não precisa definir VITE_API_URL em desenvolvimento local

# Use true apenas para desenvolver sem backend (dados mock)
VITE_USE_MOCK=false
```

### 3. Iniciar o servidor de desenvolvimento

```bash
npm run dev
```

O frontend estará disponível em: **http://localhost:5173**

---

## ✅ Verificação

1. **Backend rodando**: Acesse http://localhost:8000/docs e veja a documentação da API
2. **Frontend rodando**: Acesse http://localhost:5173 e veja a interface
3. **Conexão**: O frontend faz requisições para `/api/*` que são automaticamente redirecionadas para `http://localhost:8000` via proxy do Vite

---

## 🔐 Criar usuário administrador

Para criar um usuário administrador, use o script:

```bash
cd backend
python scripts/create_admin.py
```

Siga as instruções no terminal para criar o primeiro usuário.

---

## 🐛 Troubleshooting

### Erro de conexão com banco de dados

- Verifique se o PostgreSQL está rodando
- Confirme as credenciais no `.env`
- Teste a conexão: `psql -h localhost -U usuario -d nome_do_banco`

### Erro de CORS

- O backend já aceita `http://localhost:5173` por padrão
- Se ainda houver erro, verifique se o backend está rodando na porta 8000

### Erro de migrations

- Certifique-se de que o banco de dados existe
- Verifique se o schema está configurado corretamente no `.env`
- Tente dropar e recriar o schema: `DROP SCHEMA nitro_finance_dev CASCADE; CREATE SCHEMA nitro_finance_dev;`

### Porta já em uso

- Backend: Altere a porta no comando uvicorn: `--port 8001`
- Frontend: O Vite perguntará se quer usar outra porta automaticamente

---

## 📝 Estrutura de URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 🎯 Próximos Passos

1. Criar um usuário administrador usando o script
2. Fazer login no frontend
3. Começar a desenvolver!
