from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_tecnico = db.Column(db.Boolean, default=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime)
    ativo = db.Column(db.Boolean, default=True)
    data_exclusao = db.Column(db.DateTime, nullable=True)
    excluido_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    chamados_criados = db.relationship('Chamado', foreign_keys='Chamado.usuario_id', backref='criador', lazy=True)
    chamados_atribuidos = db.relationship('Chamado', foreign_keys='Chamado.tecnico_id', backref='tecnico', lazy=True)
    excluidor = db.relationship('Usuario', remote_side=[id], foreign_keys=[excluido_por])
    
    @property
    def papel(self):
        if self.is_admin:
            return "Administrador"
        elif self.is_tecnico:
            return "Técnico"
        else:
            return "Usuário"
    
    def soft_delete(self, usuario_exclusor_id):
        """Soft delete - marca como excluído mas mantém no banco"""
        self.ativo = False
        self.data_exclusao = datetime.utcnow()
        self.excluido_por = usuario_exclusor_id
        # Anonimizar email para evitar conflitos futuros
        self.email = f"excluido_{self.id}_{self.email}"
    
    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Chamado(db.Model):
    __tablename__ = 'chamados'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='aberto')
    prioridade = db.Column(db.String(20), default='media')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_resolucao = db.Column(db.DateTime)
    
    # Chaves estrangeiras
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Campos adicionais
    localizacao = db.Column(db.String(200))
    equipamento = db.Column(db.String(100))
    anexos = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<Chamado {self.id}: {self.titulo}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'status': self.status,
            'prioridade': self.prioridade,
            'data_criacao': self.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'criador': self.criador.nome if self.criador else None,
            'tecnico': self.tecnico.nome if self.tecnico else None,
            'localizacao': self.localizacao,
            'equipamento': self.equipamento
        }

class HistoricoChamado(db.Model):
    __tablename__ = 'historico_chamados'
    
    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamados.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    acao = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text)
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    
    chamado = db.relationship('Chamado', backref='historico')
    usuario = db.relationship('Usuario', backref='acoes')