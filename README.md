📋 Sistema de Chamados Técnicos
Sistema completo para gerenciamento de chamados técnicos com autenticação, níveis de acesso e notificações por email.

🚀 Funcionalidades Rápidas
✅ Auto-cadastro de usuários

✅ 3 níveis de acesso: Admin, Técnico e Usuário Padrão

✅ Criação e acompanhamento de chamados

✅ Notificações por email para técnicos

✅ Dashboard com estatísticas

✅ Soft delete e restauração de usuários

✅ Histórico completo de alterações

✅ API RESTful para integrações

✅ Perfil de usuário com edição e alteração de senha

⚙️ Tecnologias
Backend: Python, Flask, SQLAlchemy

Frontend: Bootstrap 5, jQuery

Banco: SQLite (dev) / PostgreSQL (prod)

Email: Flask-Mail

📦 Instalação Rápida
# 1. Clonar/ criar pasta
mkdir sistema_chamados && cd sistema_chamados

# 2. Criar requirements.txt
echo -e "Flask==2.3.2\nFlask-SQLAlchemy==3.0.5\nFlask-Login==0.6.2\nFlask-WTF==1.1.1\nFlask-Mail==0.9.1\nWerkzeug==2.3.6\nemail-validator==2.0.0\npython-dotenv==1.0.0" > requirements.txt

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar pastas
mkdir templates static

# 5. Configurar .env
echo "SECRET_KEY=chave-secreta
DATABASE_URL=sqlite:///chamados.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha
MAIL_DEFAULT_SENDER=seu-email@gmail.com
TECNICO_EMAIL=tecnico@empresa.com" > .env

# 6. Executar
python app.py

Acesse: http://localhost:5000

Admin: admin@empresa.com / admin123

📁 Estrutura Principal
sistema_chamados/
├── app.py              # Aplicação principal
├── models.py           # Modelos do banco
├── forms.py            # Formulários
├── templates/          # HTML
└── static/             # CSS

👥 Níveis de Acesso
Funcionalidade	    Usuário	Técnico	Admin
Criar chamados	      ✅	    ✅	   ✅
Ver próprios chamados	✅   	✅     ✅
Ver todos chamados	  ❌	    ✅	   ✅
Atualizar chamados  	❌   	✅    ✅
Gerenciar usuários	  ❌	    ❌  	✅
Soft delete	          ❌    	❌	  ✅
Notificações email  	❌   	✅	  ✅
📡 Principais Rotas
/ - Redireciona para login

/login - Página de login

/cadastro - Auto-cadastro

/dashboard - Página inicial

/perfil - Perfil do usuário

/chamados - Lista de chamados

/chamados/novo - Criar chamado

/usuarios - Gerenciar usuários (admin)

/api/chamados - API JSON

🔧 Comandos Úteis
# Recriar banco (se erro de coluna)
rm chamados.db && python app.py

# Verificar email disponível
curl "http://localhost:5000/verificar-email?email=teste@email.com"

📱 Screenshots
Login: Formulário com link para cadastro

Dashboard: Cards com estatísticas e últimos chamados

Perfil: Dados do usuário, estatísticas e opções de edição

Chamados: Lista com filtros e paginação

⚡ Em Produção
Para produção, altere no .env:

DATABASE_URL=postgresql://usuario:senha@localhost/db

SECRET_KEY - use uma chave forte

Configure email corretamente (Gmail: use senha de app)

🐛 Problemas Comuns
Erro	                 Solução
no such column	       rm chamados.db e reinicie
Email não envia        Verifique configurações SMTP
Usuário não loga       Admin deve ativar o usuário
