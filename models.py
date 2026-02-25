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
    is_tecnico = db.Column(db.Boolean, default=False)  # NOVO CAMPO
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    chamados_criados = db.relationship('Chamado', foreign_keys='Chamado.usuario_id', backref='criador', lazy=True)
    chamados_atribuidos = db.relationship('Chamado', foreign_keys='Chamado.tecnico_id', backref='tecnico', lazy=True)
    
    @property
    def papel(self):
        if self.is_admin:
            return "Administrador"
        elif self.is_tecnico:
            return "Técnico"
        else:
            return "Usuário"

class Chamado(db.Model):
    __tablename__ = 'chamados'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='aberto')  # aberto, em_andamento, resolvido, fechado
    prioridade = db.Column(db.String(20), default='media')  # baixa, media, alta, urgente
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_resolucao = db.Column(db.DateTime)
    
    # Chaves estrangeiras
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Campos adicionais
    localizacao = db.Column(db.String(200))
    equipamento = db.Column(db.String(100))
    anexos = db.Column(db.String(500))  # Caminho para arquivos anexados
    
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
    acao = db.Column(db.String(50), nullable=False)  # criacao, atualizacao, mudanca_status, comentario
    descricao = db.Column(db.Text)
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    
    chamado = db.relationship('Chamado', backref='historico')
    usuario = db.relationship('Usuario', backref='acoes')