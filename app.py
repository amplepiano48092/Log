from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from config import Config
from models import db, Usuario, Chamado, HistoricoChamado
from forms import LoginForm, AutoCadastroForm, CadastroUsuarioForm, ChamadoForm, AtualizarChamadoForm, FiltroChamadosForm

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
            is_admin=True,
            is_tecnico=False,
            ativo=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin@empresa.com / admin123")

# Funções de email
def enviar_email_chamado(chamado, acao):
    try:
        destinatarios = [app.config['TECNICO_EMAIL']]
        
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

def enviar_email_boas_vindas(usuario):
    """Envia email de boas-vindas para novo usuário"""
    try:
        msg = Message(
            subject='Bem-vindo ao Sistema de Chamados',
            recipients=[usuario.email],
            html=f"""
            <h2>Olá {usuario.nome}!</h2>
            <p>Seu cadastro no Sistema de Chamados foi realizado com sucesso.</p>
            <p>Agora você pode abrir chamados e acompanhar o status das suas solicitações.</p>
            <br>
            <p><strong>Dados do cadastro:</strong></p>
            <ul>
                <li>Nome: {usuario.nome}</li>
                <li>Email: {usuario.email}</li>
                <li>Data: {usuario.data_cadastro.strftime('%d/%m/%Y %H:%M')}</li>
            </ul>
            <br>
            <p><a href="{url_for('login', _external=True)}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Acessar o Sistema</a></p>
            <br>
            <p>Em caso de dúvidas, entre em contato com o administrador.</p>
            <p>Atenciosamente,<br>Equipe de Suporte</p>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email de boas-vindas: {e}")
        return False

# Rotas principais
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
                usuario.ultimo_acesso = datetime.utcnow()
                db.session.commit()
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuário inativo. Contate o administrador.', 'danger')
        else:
            flash('Email ou senha inválidos.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_usuario_padrao():
    """Rota pública para auto-cadastro de usuários comuns"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = AutoCadastroForm()
    
    if form.validate_on_submit():
        if Usuario.query.filter_by(email=form.email.data).first():
            flash('Este email já está cadastrado. Faça login.', 'warning')
            return redirect(url_for('login'))
        
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            senha_hash=generate_password_hash(form.senha.data),
            is_admin=False,
            is_tecnico=False,
            ativo=True,
            data_cadastro=datetime.utcnow()
        )
        
        try:
            db.session.add(usuario)
            db.session.commit()
            
            # Enviar email de boas-vindas
            enviar_email_boas_vindas(usuario)
            
            # Fazer login automático
            login_user(usuario)
            usuario.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            
            flash(f'Bem-vindo {usuario.nome}! Seu cadastro foi realizado com sucesso.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao realizar cadastro. Tente novamente.', 'danger')
            print(f"Erro no cadastro: {e}")
    
    return render_template('cadastro_padrao.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def perfil():
    """Página de perfil do usuário com informações detalhadas"""
    # Estatísticas do usuário
    total_chamados = Chamado.query.filter_by(usuario_id=current_user.id).count()
    chamados_abertos = Chamado.query.filter_by(usuario_id=current_user.id, status='aberto').count()
    chamados_andamento = Chamado.query.filter_by(usuario_id=current_user.id, status='em_andamento').count()
    chamados_resolvidos = Chamado.query.filter_by(usuario_id=current_user.id, status='resolvido').count()
    
    # Últimos 5 chamados do usuário
    ultimos_chamados = Chamado.query.filter_by(usuario_id=current_user.id)\
                                   .order_by(Chamado.data_criacao.desc())\
                                   .limit(5).all()
    
    return render_template('perfil.html',
                         total_chamados=total_chamados,
                         chamados_abertos=chamados_abertos,
                         chamados_andamento=chamados_andamento,
                         chamados_resolvidos=chamados_resolvidos,
                         ultimos_chamados=ultimos_chamados)

@app.route('/perfil/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    """Alterar senha do usuário"""
    dados = request.get_json()
    senha_atual = dados.get('senha_atual')
    nova_senha = dados.get('nova_senha')
    
    # Verificar senha atual
    if not check_password_hash(current_user.senha_hash, senha_atual):
        return jsonify({'success': False, 'mensagem': 'Senha atual incorreta!'})
    
    # Validar nova senha
    if len(nova_senha) < 6:
        return jsonify({'success': False, 'mensagem': 'A nova senha deve ter no mínimo 6 caracteres!'})
    
    # Atualizar senha
    current_user.senha_hash = generate_password_hash(nova_senha)
    db.session.commit()
    
    return jsonify({'success': True, 'mensagem': 'Senha alterada com sucesso!'})

@app.route('/perfil/atualizar', methods=['POST'])
@login_required
def atualizar_perfil():
    """Atualizar dados do perfil"""
    dados = request.get_json()
    nome = dados.get('nome')
    email = dados.get('email')
    
    # Verificar se email já existe (se foi alterado)
    if email != current_user.email:
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return jsonify({'success': False, 'mensagem': 'Este email já está em uso por outro usuário!'})
    
    # Atualizar dados
    current_user.nome = nome
    current_user.email = email
    db.session.commit()
    
    return jsonify({'success': True, 'mensagem': 'Perfil atualizado com sucesso!'})

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

# Rotas de chamados
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
        
        historico = HistoricoChamado(
            chamado_id=chamado.id,
            usuario_id=current_user.id,
            acao='criacao',
            descricao='Chamado criado'
        )
        db.session.add(historico)
        db.session.commit()
        
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
    
    # Buscar técnicos disponíveis (apenas para admin)
    tecnicos = []
    if current_user.is_admin:
        tecnicos = Usuario.query.filter_by(is_tecnico=True, ativo=True).all()
    
    return render_template('detalhe_chamado.html', chamado=chamado, historico=historico, tecnicos=tecnicos)

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
    
    if tecnico_id and tecnico_id != '' and int(tecnico_id) != chamado.tecnico_id:
        tecnico = Usuario.query.get(int(tecnico_id))
        if tecnico:
            alteracoes.append(f'Chamado atribuído a {tecnico.nome}')
            chamado.tecnico_id = int(tecnico_id)
    elif tecnico_id == '' and chamado.tecnico_id:
        alteracoes.append(f'Atribuição removida')
        chamado.tecnico_id = None
    
    if alteracoes or comentario:
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
        
        enviar_email_chamado(chamado, 'Chamado atualizado')
        
        flash('Chamado atualizado com sucesso!', 'success')
    else:
        flash('Nenhuma alteração realizada.', 'info')
    
    return redirect(url_for('detalhe_chamado', id=id))

# Rotas de usuários (apenas admin)
@app.route('/usuarios')
@login_required
def listar_usuarios():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios = Usuario.query.filter_by(ativo=True).all()
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
            is_admin=form.is_admin.data,
            is_tecnico=form.is_tecnico.data,
            ativo=True
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

@app.route('/usuarios/<int:id>/excluir', methods=['GET', 'POST'])
@login_required
def excluir_usuario(id):
    """Página de confirmação de exclusão de usuário"""
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem excluir usuários.', 'danger')
        return redirect(url_for('listar_usuarios'))
    
    if current_user.id == id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('listar_usuarios'))
    
    usuario = Usuario.query.get_or_404(id)
    
    chamados_criados = Chamado.query.filter_by(usuario_id=id).count()
    chamados_tecnicos = Chamado.query.filter_by(tecnico_id=id).count()
    
    return render_template('confirmar_exclusao_usuario.html',
                         usuario=usuario,
                         chamados_criados=chamados_criados,
                         chamados_tecnicos=chamados_tecnicos)

@app.route('/usuarios/<int:id>/excluir-permanente', methods=['POST'])
@login_required
def excluir_usuario_permanente(id):
    """Exclusão permanente (apenas se não tiver chamados)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    if current_user.id == id:
        return jsonify({'error': 'Auto-exclusão não permitida'}), 400
    
    usuario = Usuario.query.get_or_404(id)
    
    chamados_criados = Chamado.query.filter_by(usuario_id=id).count()
    chamados_tecnicos = Chamado.query.filter_by(tecnico_id=id).count()
    
    if chamados_criados > 0 or chamados_tecnicos > 0:
        return jsonify({
            'error': 'Usuário possui chamados associados. Use exclusão suave (soft delete).'
        }), 400
    
    try:
        nome = usuario.nome
        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensagem': f'Usuário {nome} excluído permanentemente com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/usuarios/<int:id>/soft-delete', methods=['POST'])
@login_required
def soft_delete_usuario(id):
    """Exclusão suave - mantém histórico mas desativa o usuário"""
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    if current_user.id == id:
        return jsonify({'error': 'Auto-exclusão não permitida'}), 400
    
    usuario = Usuario.query.get_or_404(id)
    
    try:
        usuario.soft_delete(current_user.id)
        db.session.commit()
        
        # Reatribuir chamados abertos
        chamados_abertos = Chamado.query.filter(
            Chamado.tecnico_id == id,
            Chamado.status.in_(['aberto', 'em_andamento'])
        ).all()
        
        for chamado in chamados_abertos:
            chamado.tecnico_id = None
            chamado.status = 'aberto'
            historico = HistoricoChamado(
                chamado_id=chamado.id,
                usuario_id=current_user.id,
                acao='atualizacao',
                descricao=f'Técnico removido automaticamente (usuário excluído)'
            )
            db.session.add(historico)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensagem': f'Usuário {usuario.nome} desativado com sucesso! Chamados reatribuídos.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/usuarios/excluidos')
@login_required
def usuarios_excluidos():
    """Listar usuários excluídos (soft delete)"""
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios_excluidos = Usuario.query.filter_by(ativo=False).all()
    return render_template('usuarios_excluidos.html', usuarios=usuarios_excluidos)

@app.route('/usuarios/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_usuario(id):
    """Restaurar usuário excluído (soft delete)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    usuario = Usuario.query.get_or_404(id)
    
    if usuario.ativo:
        return jsonify({'error': 'Usuário já está ativo'}), 400
    
    try:
        usuario.ativo = True
        usuario.data_exclusao = None
        usuario.excluido_por = None
        if usuario.email.startswith(f"excluido_{usuario.id}_"):
            usuario.email = usuario.email.replace(f"excluido_{usuario.id}_", "")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensagem': f'Usuário {usuario.nome} restaurado com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Rotas utilitárias
@app.route('/verificar-email')
def verificar_email():
    """Rota AJAX para verificar se email já existe"""
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email não fornecido'}), 400
    
    usuario = Usuario.query.filter_by(email=email).first()
    return jsonify({
        'disponivel': usuario is None,
        'mensagem': 'Email disponível' if usuario is None else 'Email já cadastrado'
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