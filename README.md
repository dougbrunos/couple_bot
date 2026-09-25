# 🤖 Bot de Casal — Telegram

Assistente virtual para o Telegram projetado para casais organizarem seus compromissos, rotinas e datas importantes com facilidade, notificações automáticas pontuais e sincronização em tempo real.

---

## 🚀 Funcionalidades Principais

- 💑 **Vínculo Seguro de Casal:** Conexão entre os parceiros via código de convite temporário (`CASAL-XXXX`) com expiração de 30 minutos e confirmação mútua.
- 📅 **Criação Guiada de Eventos:**
  - Fluxo passo a passo: Título, data (`DD/MM/AAAA`) e horário (`HH:MM`) com validações inteligentes;
  - Definição de escopo: **Pessoal** (`👤 Eu`), **Parceiro** (`👩 Ela / 👨 Ele`) ou **Compartilhado** (`❤️ Nós dois`);
  - Suporte a regras de recorrência: Diária, Semanal, Mensal e Anual;
  - Lembrete com antecedência configurável (10m, 30m, 1h, 1 dia antes).
- 🔍 **Consultas Rápidas e Organizadas:**
  - `/hoje` — Exibe os compromissos do dia atual agrupados visualmente por participante;
  - `/semana` — Exibe a projeção dos próximos 7 dias com indicação de dias livres;
  - `/eventos` — Lista cronológica dos próximos compromissos ativos.
- 🗑️ **Exclusão Segura e Notificação:**
  - `/delete` — Menu interativo com tela de confirmação antes de remover qualquer evento;
  - Notificação automática ao parceiro em caso de cancelamento de evento compartilhado;
  - Cancelamento em cascata de lembretes pendentes no agendador.
- ⏰ **Sistema de Lembretes Automáticos:**
  - Notificações enviadas pelo Telegram no horário exato configurado;
  - Ações interativas diretamente na mensagem: confirmar leitura (`[✓ OK]`) ou adiar alarme (`[⏰ Adiar]`: 10m, 30m, 1h).

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.12+
- **Framework Telegram:** `python-telegram-bot` (v22+) com `JobQueue` integrado (APScheduler)
- **ORM / Persistência:** `SQLAlchemy` 2.0+ com suporte unificado para **PostgreSQL** (produção via Supabase) e **SQLite** (desenvolvimento local)
- **Driver de Banco:** `psycopg2-binary`
- **Fuso Horário:** `pytz` (padrão `America/Sao_Paulo`)
- **Testes Automatizados:** `pytest` + `anyio` (30 testes unitários e de integração cobrindo fluxos, persistência e segurança)

---

## 📂 Estrutura do Projeto

```text
bot_telegram/
├── app/
│   ├── bot/
│   │   ├── handlers/         # Handlers dos comandos, menus e conversas
│   │   ├── keyboards/        # Teclados inline e botões interativos
│   │   └── states/           # Estados dos fluxos (ConversationHandler)
│   ├── database/
│   │   ├── database.py       # Configuração do engine SQLAlchemy e pooling
│   │   ├── models.py         # Modelos de dados (User, Couple, Event, Reminder)
│   │   └── repositories/     # Operações de banco de dados (CRUD) desacopladas
│   ├── scheduler/
│   │   └── scheduler.py      # Worker periódico de disparo e adiamento de alertas
│   ├── services/             # Regras de negócio e cálculo de recorrências
│   ├── utils/                # Utilitários de data/hora e timezone
│   └── config.py             # Validação e carregamento de variáveis de ambiente
├── tests/                    # Bateria de testes automatizados com pytest
├── .env.example              # Modelo seguro das variáveis necessárias
├── .gitignore                # Proteção contra versionamento de credenciais e caches
├── requirements.txt          # Dependências do projeto
├── main.py                   # Ponto de entrada da aplicação
└── README.md                 # Documentação do projeto
```

---

## ⚙️ Instalação e Execução Local

### 1. Pré-requisitos
- Python 3.12 ou superior instalado;
- Conta no Telegram.

### 2. Criação do Bot no Telegram
1. No Telegram, converse com o [@BotFather](https://t.me/BotFather);
2. Envie o comando `/newbot`;
3. Escolha o nome e o username (terminando em `bot`);
4. Copie o token HTTP API gerado.

### 3. Configuração do Repositório
```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/bot_telegram.git
cd bot_telegram

# Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 4. Configuração das Variáveis de Ambiente
Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:
```env
TELEGRAM_BOT_TOKEN=seu_token_gerado_no_botfather
DATABASE_URL=sqlite:///data/app.db
TIMEZONE=America/Sao_Paulo
```

> **Dica para PostgreSQL / Supabase:** Se for utilizar o Supabase, basta substituir a `DATABASE_URL`:
> ```env
> DATABASE_URL=postgresql://postgres.[REF]:[SENHA]@aws-0-[REGIAO].pooler.supabase.com:5432/postgres
> ```

### 5. Iniciar a Aplicação
Com o ambiente virtual ativado:
```bash
python main.py
```

O bot iniciará o `polling` e o agendador de lembretes automaticamente. No Telegram, abra a conversa com o seu bot e envie `/start`!

---

## ☁️ Deploy Gratuito (24/7 na Nuvem)

Você pode hospedar o bot sem nenhum custo financeiro utilizando a combinação **Supabase + Render**:

### 1. Banco de Dados (Supabase - PostgreSQL Gratuito)
1. Crie uma conta em [supabase.com](https://supabase.com) e inicie um novo projeto;
2. Em **Project Settings** > **Database**, copie a **Connection String** no formato **URI**;
3. As tabelas serão criadas de forma automática na primeira inicialização do bot.

### 2. Hospedagem da Aplicação (Render - Gratuito)
1. Crie uma conta em [render.com](https://render.com) e conecte seu repositório do GitHub;
2. Crie um novo **Web Service** (ou **Background Worker**):
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
3. Na seção **Environment Variables**, cadastre as mesmas chaves do seu `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `DATABASE_URL`
   - `TIMEZONE`
4. Faça o deploy. O Render manterá o bot rodando e verificando os lembretes continuamente!

---

## 🧪 Testes Automatizados

Para executar toda a suíte de testes:
```bash
pytest
```

Para executar com relatório detalhado:
```bash
pytest -v
```

---

## 📖 Comandos Disponíveis no Telegram

| Comando | Descrição |
|---|---|
| `/start` | Inicia o bot, registra o usuário e apresenta o menu principal |
| `/menu` | Abre o menu de atalhos e ações do casal |
| `/ajuda` ou `/help` | Exibe o guia completo de uso e comandos |
| `/add` | Inicia o fluxo conversacional para cadastrar um novo evento |
| `/hoje` | Lista os compromissos do dia corrente agrupados por participante |
| `/semana` | Exibe a agenda dos próximos 7 dias |
| `/eventos` | Lista todos os próximos eventos cronológicos |
| `/delete` | Abre a listagem de eventos com botão de cancelamento |
| `/cancelar` | Cancela qualquer operação ou fluxo interativo em andamento |

---

## 📄 Licença

Este projeto é distribuído sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.
