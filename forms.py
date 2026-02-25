from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import Usuario

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])

class AutoCadastroForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    termos = BooleanField('Li e aceito os termos de uso', validators=[DataRequired()])
    
    def validate_email(self, email):
        usuario = Usuario.query.filter_by(email=email.data).first()
        if usuario:
            raise ValidationError('Este email já está cadastrado.')

class CadastroUsuarioForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    is_admin = BooleanField('Administrador')
    is_tecnico = BooleanField('Técnico')
    
    def validate_email(self, email):
        usuario = Usuario.query.filter_by(email=email.data).first()
        if usuario:
            raise ValidationError('Email já cadastrado.')

class ChamadoForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    prioridade = SelectField('Prioridade', choices=[
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente')
    ], default='media')
    localizacao = StringField('Localização', validators=[Length(max=200)])
    equipamento = StringField('Equipamento', validators=[Length(max=100)])

class AtualizarChamadoForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('resolvido', 'Resolvido'),
        ('fechado', 'Fechado')
    ])
    prioridade = SelectField('Prioridade', choices=[
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente')
    ])
    tecnico_id = SelectField('Atribuir Técnico', coerce=int)
    comentario = TextAreaField('Comentário')

class FiltroChamadosForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('todos', 'Todos'),
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('resolvido', 'Resolvido'),
        ('fechado', 'Fechado')
    ], default='todos')
    prioridade = SelectField('Prioridade', choices=[
        ('todos', 'Todos'),
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente')
    ], default='todos')