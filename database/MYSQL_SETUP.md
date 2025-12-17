# 🗄️ MySQL Database Setup Guide

Guia completo para configurar a base de dados MySQL/MariaDB para o Better E-Leilões.

## 📋 Pré-requisitos

- MySQL 8.0+ ou MariaDB 10.5+
- phpMyAdmin (opcional, para gestão visual)
- Python 3.8+ com pip

---

## 🚀 Passo 1: Criar a Base de Dados

### Opção A: Via phpMyAdmin

1. Aceda ao phpMyAdmin (normalmente `http://localhost/phpmyadmin`)
2. Faça login com as suas credenciais MySQL
3. Clique em **"SQL"** no topo
4. Copie e cole todo o conteúdo do ficheiro `mysql_schema.sql`
5. Clique em **"Executar"** (Go)
6. Verifique se a base de dados `eleiloes` foi criada com sucesso

### Opção B: Via linha de comandos

```bash
# Fazer login no MySQL
mysql -u root -p

# Executar o script SQL
source /caminho/para/mysql_schema.sql

# Ou num único comando:
mysql -u root -p < /caminho/para/mysql_schema.sql
```

---

## 🔧 Passo 2: Criar Utilizador da Aplicação (Recomendado)

Por segurança, crie um utilizador específico para a aplicação:

```sql
-- Criar utilizador
CREATE USER 'eleiloes_app'@'localhost' IDENTIFIED BY 'sua_password_segura_aqui';

-- Dar permissões
GRANT SELECT, INSERT, UPDATE, DELETE ON eleiloes.* TO 'eleiloes_app'@'localhost';

-- Aplicar alterações
FLUSH PRIVILEGES;
```

---

## ⚙️ Passo 3: Configurar a Aplicação Python

### 3.1 Instalar dependências MySQL

```bash
cd /home/user/better-e-leiloes/backend
pip install aiomysql==0.2.0 cryptography==41.0.7
```

### 3.2 Criar ficheiro `.env`

Crie o ficheiro `backend/.env` (copie de `.env.example`):

```bash
cp .env.example .env
nano .env  # ou use o seu editor favorito
```

### 3.3 Configurar a connection string

Edite o ficheiro `.env` e configure o `DATABASE_URL`:

```bash
# Formato geral:
# DATABASE_URL=mysql+aiomysql://username:password@host:port/database

# Exemplo com utilizador root (desenvolvimento):
DATABASE_URL=mysql+aiomysql://root:sua_password@localhost:3306/eleiloes

# Exemplo com utilizador da aplicação (produção - recomendado):
DATABASE_URL=mysql+aiomysql://eleiloes_app:sua_password_segura_aqui@localhost:3306/eleiloes

# Para ligação remota:
DATABASE_URL=mysql+aiomysql://eleiloes_app:password@192.168.1.100:3306/eleiloes
```

**⚠️ IMPORTANTE**: Substitua `sua_password` pela password real do MySQL!

---

## 🧪 Passo 4: Testar a Conexão

### Teste rápido via Python:

```python
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def test_connection():
    DATABASE_URL = "mysql+aiomysql://seu_user:sua_password@localhost:3306/eleiloes"

    try:
        engine = create_async_engine(DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT VERSION()")
            version = result.scalar()
            print(f"✅ Conexão bem-sucedida! MySQL versão: {version}")
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")

asyncio.run(test_connection())
```

### Teste com a aplicação:

```bash
cd /home/user/better-e-leiloes/backend
python -c "
import asyncio
from database import init_db

async def test():
    await init_db()
    print('✅ Database inicializada com sucesso!')

asyncio.run(test())
"
```

---

## 📊 Estrutura da Base de Dados

### Tabela Principal: `events`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `reference` | VARCHAR(50) | Chave primária (ex: LO-2024-12345) |
| `tipo_evento` | ENUM | 'imovel' ou 'movel' |
| `valor_base` | DECIMAL(12,2) | Valor base em euros |
| `valor_abertura` | DECIMAL(12,2) | Valor de abertura |
| `valor_minimo` | DECIMAL(12,2) | Valor mínimo |
| `lance_atual` | DECIMAL(12,2) | Lance atual |
| `gps_latitude` | DECIMAL(10,7) | Latitude GPS (imóveis) |
| `gps_longitude` | DECIMAL(10,7) | Longitude GPS (imóveis) |
| `det_tipo` | VARCHAR(100) | Tipo de bem |
| `det_subtipo` | VARCHAR(100) | Subtipo |
| `det_tipologia` | VARCHAR(50) | Tipologia (T2, T3, etc) |
| `det_area_privativa` | DECIMAL(10,2) | Área privativa m² |
| `det_area_dependente` | DECIMAL(10,2) | Área dependente m² |
| `det_area_total` | DECIMAL(10,2) | Área total m² |
| `det_distrito` | VARCHAR(100) | Distrito |
| `det_concelho` | VARCHAR(100) | Concelho |
| `det_freguesia` | VARCHAR(100) | Freguesia |
| `det_matricula` | VARCHAR(50) | Matrícula (veículos) |
| `data_inicio` | DATETIME | Data de início do leilão |
| `data_fim` | DATETIME | Data de fim do leilão |
| `imagens` | JSON | Array de URLs das imagens |
| `descricao` | MEDIUMTEXT | HTML da descrição |
| `observacoes` | MEDIUMTEXT | HTML das observações |
| `onuselimitacoes` | MEDIUMTEXT | HTML dos ónus e limitações |
| `descricao_predial` | MEDIUMTEXT | HTML da descrição predial |
| `cerimonia_encerramento` | MEDIUMTEXT | HTML da cerimónia |
| `agente_execucao` | MEDIUMTEXT | HTML do agente |
| `dados_processo` | MEDIUMTEXT | HTML do processo |
| `scraped_at` | DATETIME | Data do primeiro scrape |
| `updated_at` | DATETIME | Data da última atualização |

### Views Disponíveis

1. **`vw_eventos_ativos`** - Eventos que ainda não terminaram
2. **`vw_imoveis_gps`** - Imóveis com coordenadas GPS
3. **`vw_stats_concelho`** - Estatísticas por concelho

### Stored Procedures

1. **`sp_limpar_eventos_antigos(dias)`** - Remove eventos antigos
2. **`sp_estatisticas_gerais()`** - Estatísticas gerais da BD

---

## 🔍 Queries Úteis

### Ver eventos ativos:
```sql
SELECT * FROM vw_eventos_ativos LIMIT 10;
```

### Contar eventos por tipo:
```sql
SELECT tipo_evento, COUNT(*) as total
FROM events
GROUP BY tipo_evento;
```

### Ver eventos terminando hoje:
```sql
SELECT reference, det_tipo, det_concelho, data_fim
FROM events
WHERE DATE(data_fim) = CURDATE()
ORDER BY data_fim ASC;
```

### Ver eventos com lances recentes:
```sql
SELECT reference, det_tipo, lance_atual, data_fim
FROM events
WHERE lance_atual IS NOT NULL
  AND data_fim > NOW()
ORDER BY updated_at DESC
LIMIT 20;
```

---

## 🐛 Resolução de Problemas

### Erro: "Access denied for user"
- Verifique se a password está correta no `.env`
- Confirme que o utilizador tem permissões: `SHOW GRANTS FOR 'seu_user'@'localhost';`

### Erro: "Unknown database 'eleiloes'"
- Execute o script `mysql_schema.sql` para criar a base de dados

### Erro: "Can't connect to MySQL server"
- Verifique se o MySQL está a correr: `sudo systemctl status mysql`
- Confirme o host e porta no `.env`

### Erro: "No module named 'aiomysql'"
- Instale as dependências: `pip install aiomysql cryptography`

### Erro: "Connection timeout"
- Verifique se a firewall permite conexões na porta 3306
- Para conexões remotas, edite `my.cnf`: `bind-address = 0.0.0.0`

---

## 🔒 Segurança em Produção

1. **Nunca use o utilizador root** em produção
2. **Use passwords fortes** (mínimo 16 caracteres)
3. **Configure SSL/TLS** para conexões remotas
4. **Limite as permissões** (apenas SELECT, INSERT, UPDATE, DELETE)
5. **Faça backups regulares**: `mysqldump eleiloes > backup.sql`
6. **Não commite o ficheiro `.env`** ao git (já está no `.gitignore`)

---

## 📝 Migração de SQLite para MySQL

Se já tem dados em SQLite e quer migrar:

```python
# Script de migração (exemplo básico)
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from database import EventDB, Base

async def migrate():
    # Conexão SQLite
    sqlite_engine = create_async_engine("sqlite+aiosqlite:///./eleiloes.db")

    # Conexão MySQL
    mysql_engine = create_async_engine("mysql+aiomysql://user:pass@localhost/eleiloes")

    # Ler de SQLite e escrever em MySQL
    # ... implementar lógica de migração ...

asyncio.run(migrate())
```

---

## ✅ Checklist de Setup

- [ ] MySQL/MariaDB instalado e a correr
- [ ] Base de dados `eleiloes` criada via `mysql_schema.sql`
- [ ] Utilizador da aplicação criado com permissões corretas
- [ ] Dependências Python instaladas (`aiomysql`, `cryptography`)
- [ ] Ficheiro `.env` criado e configurado
- [ ] `DATABASE_URL` corretamente configurado no `.env`
- [ ] Conexão testada com sucesso
- [ ] Aplicação FastAPI inicia sem erros

---

## 📚 Recursos Adicionais

- [SQLAlchemy Async Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [aiomysql GitHub](https://github.com/aio-libs/aiomysql)
- [MySQL 8.0 Reference](https://dev.mysql.com/doc/refman/8.0/en/)
- [phpMyAdmin Docs](https://docs.phpmyadmin.net/)

---

**🎉 Setup Completo!** A aplicação está pronta para usar MySQL/MariaDB com phpMyAdmin.
