from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from config import Config
from models import db, Usuario, Chamado, HistoricoChamado
from forms import LoginForm, CadastroUsuarioForm, ChamadoForm, AtualizarChamadoForm, FiltroChamadosForm

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar extensões
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Criar tabelas e usuário admin inicial
with app.app_context():
    db.create_all()
    
    # Criar usuário admin se não existir
    if not Usuario.query.filter_by(email='admin@empresa.com').first():
        admin = Usuario(
            nome='Administrador',
            email='admin@empresa.com',
            senha_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin@empresa.com / admin123")

# Função para enviar email
def enviar_email_chamado(chamado, acao):
    try:
        destinatarios = [app.config['TECNICO_EMAIL']]
        
        # Se o chamado tem um técnico atribuído, incluir no email
        if chamado.tecnico and chamado.tecnico.email not in destinatarios:
            destinatarios.append(chamado.tecnico.email)
        
        assunto = f'Chamado #{chamado.id} - {chamado.titulo} - {acao}'
        
        corpo = f"""
        <h2>Chamado Técnico #{chamado.id}</h2>
        <p><strong>Ação:</strong> {acao}</p>
        <p><strong>Título:</strong> {chamado.titulo}</p>
        <p><strong>Descrição:</strong> {chamado.descricao}</p>
        <p><strong>Status:</strong> {chamado.status}</p>
        <p><strong>Prioridade:</strong> {chamado.prioridade}</p>
        <p><strong>Criado por:</strong> {chamado.criador.nome}</p>
        <p><strong>Data de criação:</strong> {chamado.data_criacao.strftime('%d/%m/%Y %H:%M')}</p>
        """
        
        if chamado.localizacao:
            corpo += f'<p><strong>Localização:</strong> {chamado.localizacao}</p>'
        if chamado.equipamento:
            corpo += f'<p><strong>Equipamento:</strong> {chamado.equipamento}</p>'
        if chamado.tecnico:
            corpo += f'<p><strong>Técnico responsável:</strong> {chamado.tecnico.nome}</p>'
        
        corpo += """
        <br>
        <p>Acesse o sistema para mais detalhes.</p>
        """
        
        msg = Message(
            subject=assunto,
            recipients=destinatarios,
            html=corpo
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

# Rotas
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        
        if usuario and check_password_hash(usuario.senha_hash, form.senha.data):
            if usuario.ativo:
                login_user(usuario)
                usuario.data_ultimo_acesso = datetime.utcnow()
                db.session.commit()
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuário inativo. Contate o administrador.', 'danger')
        else:
            flash('Email ou senha inválidos.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas para o dashboard
    total_chamados = Chamado.query.count()
    
    if current_user.is_admin:
        chamados_abertos = Chamado.query.filter_by(status='aberto').count()
        chamados_andamento = Chamado.query.filter_by(status='em_andamento').count()
        chamados_resolvidos = Chamado.query.filter_by(status='resolvido').count()
        meus_chamados = Chamado.query.filter_by(usuario_id=current_user.id).count()
    else:
        chamados_abertos = Chamado.query.filter_by(usuario_id=current_user.id, status='aberto').count()
        chamados_andamento = Chamado.query.filter_by(usuario_id=current_user.id, status='em_andamento').count()
        chamados_resolvidos = Chamado.query.filter_by(usuario_id=current_user.id, status='resolvido').count()
        meus_chamados = Chamado.query.filter_by(usuario_id=current_user.id).count()
    
    # Últimos 5 chamados
    if current_user.is_admin:
        ultimos_chamados = Chamado.query.order_by(Chamado.data_criacao.desc()).limit(5).all()
    else:
        ultimos_chamados = Chamado.query.filter_by(usuario_id=current_user.id).order_by(Chamado.data_criacao.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_chamados=total_chamados,
                         chamados_abertos=chamados_abertos,
                         chamados_andamento=chamados_andamento,
                         chamados_resolvidos=chamados_resolvidos,
                         meus_chamados=meus_chamados,
                         ultimos_chamados=ultimos_chamados)

@app.route('/chamados/novo', methods=['GET', 'POST'])
@login_required
def novo_chamado():
    form = ChamadoForm()
    
    if form.validate_on_submit():
        chamado = Chamado(
            titulo=form.titulo.data,
            descricao=form.descricao.data,
            prioridade=form.prioridade.data,
            localizacao=form.localizacao.data,
            equipamento=form.equipamento.data,
            usuario_id=current_user.id,
            status='aberto'
        )
        
        db.session.add(chamado)
        db.session.commit()
        
        # Registrar no histórico
        historico = HistoricoChamado(
            chamado_id=chamado.id,
            usuario_id=current_user.id,
            acao='criacao',
            descricao='Chamado criado'
        )
        db.session.add(historico)
        db.session.commit()
        
        # Enviar email para o técnico
        enviar_email_chamado(chamado, 'Novo chamado criado')
        
        flash('Chamado criado com sucesso! Notificação enviada ao técnico.', 'success')
        return redirect(url_for('listar_chamados'))
    
    return render_template('criar_chamado.html', form=form)

@app.route('/chamados')
@login_required
def listar_chamados():
    form = FiltroChamadosForm()
    
    # Construir query base
    if current_user.is_admin:
        query = Chamado.query
    else:
        query = Chamado.query.filter_by(usuario_id=current_user.id)
    
    # Aplicar filtros
    status = request.args.get('status', 'todos')
    prioridade = request.args.get('prioridade', 'todos')
    
    if status != 'todos':
        query = query.filter_by(status=status)
    if prioridade != 'todos':
        query = query.filter_by(prioridade=prioridade)
    
    # Ordenar e paginar
    page = request.args.get('page', 1, type=int)
    chamados = query.order_by(Chamado.data_criacao.desc()).paginate(page=page, per_page=10)
    
    return render_template('listar_chamados.html', chamados=chamados, form=form)

@app.route('/chamados/<int:id>')
@login_required
def detalhe_chamado(id):
    chamado = Chamado.query.get_or_404(id)
    
    # Verificar permissão
    if not current_user.is_admin and chamado.usuario_id != current_user.id:
        flash('Você não tem permissão para visualizar este chamado.', 'danger')
        return redirect(url_for('listar_chamados'))
    
    historico = HistoricoChamado.query.filter_by(chamado_id=id).order_by(HistoricoChamado.data_acao.desc()).all()
    
    return render_template('detalhe_chamado.html', chamado=chamado, historico=historico)

@app.route('/chamados/<int:id>/atualizar', methods=['POST'])
@login_required
def atualizar_chamado(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem atualizar chamados.', 'danger')
        return redirect(url_for('detalhe_chamado', id=id))
    
    chamado = Chamado.query.get_or_404(id)
    
    status = request.form.get('status')
    prioridade = request.form.get('prioridade')
    tecnico_id = request.form.get('tecnico_id')
    comentario = request.form.get('comentario')
    
    alteracoes = []
    
    if status and status != chamado.status:
        alteracoes.append(f'Status alterado de {chamado.status} para {status}')
        chamado.status = status
        if status == 'resolvido':
            chamado.data_resolucao = datetime.utcnow()
    
    if prioridade and prioridade != chamado.prioridade:
        alteracoes.append(f'Prioridade alterada de {chamado.prioridade} para {prioridade}')
        chamado.prioridade = prioridade
    
    if tecnico_id and int(tecnico_id) != chamado.tecnico_id:
        tecnico = Usuario.query.get(int(tecnico_id))
        if tecnico:
            alteracoes.append(f'Chamado atribuído a {tecnico.nome}')
            chamado.tecnico_id = int(tecnico_id)
    
    if alteracoes or comentario:
        # Registrar no histórico
        descricao = ', '.join(alteracoes)
        if comentario:
            if descricao:
                descricao += f'. Comentário: {comentario}'
            else:
                descricao = f'Comentário: {comentario}'
        
        historico = HistoricoChamado(
            chamado_id=chamado.id,
            usuario_id=current_user.id,
            acao='atualizacao',
            descricao=descricao
        )
        db.session.add(historico)
        
        chamado.data_atualizacao = datetime.utcnow()
        db.session.commit()
        
        # Enviar email sobre a atualização
        enviar_email_chamado(chamado, 'Chamado atualizado')
        
        flash('Chamado atualizado com sucesso!', 'success')
    else:
        flash('Nenhuma alteração realizada.', 'info')
    
    return redirect(url_for('detalhe_chamado', id=id))

@app.route('/usuarios')
@login_required
def listar_usuarios():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = CadastroUsuarioForm()
    
    if form.validate_on_submit():
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            senha_hash=generate_password_hash(form.senha.data),
            is_admin=form.is_admin.data
        )
        
        db.session.add(usuario)
        db.session.commit()
        
        flash(f'Usuário {usuario.nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    
    return render_template('cadastro_usuario.html', form=form)

@app.route('/usuarios/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_usuario(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    usuario = Usuario.query.get_or_404(id)
    
    if usuario.id == current_user.id:
        return jsonify({'error': 'Não é possível desativar o próprio usuário'}), 400
    
    usuario.ativo = not usuario.ativo
    db.session.commit()
    
    return jsonify({
        'success': True,
        'ativo': usuario.ativo,
        'mensagem': f'Usuário {"ativado" if usuario.ativo else "desativado"} com sucesso!'
    })

@app.route('/api/chamados')
@login_required
def api_chamados():
    if current_user.is_admin:
        chamados = Chamado.query.all()
    else:
        chamados = Chamado.query.filter_by(usuario_id=current_user.id).all()
    
    return jsonify([chamado.to_dict() for chamado in chamados])

if __name__ == '__main__':
    app.run(debug=True)