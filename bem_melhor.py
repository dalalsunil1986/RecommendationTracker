# -*- coding: utf-8 -*-
#!/usr/bin/env python

# imports
from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
                  abort, render_template, flash, Markup, jsonify

# configuração
DATABASE = 'bem_melhor.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


# aplicação
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent = True)


# funções do banco
def connect_db():
    """Funcao para conectar ao banco de dados da aplicacao"""
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Funcao para inicialização do banco de dados"""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as schema:
            db.cursor().executescript(schema.read())
        db.commit()

@app.before_request
def before_request():
    """Funcao que sera chamada antes de qualquer interacao com o banco"""
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    """Funcao que sera chamada depois de qualquer interacao com o banco"""
    g.db.close()


# view principal
@app.route('/')
def main_page():
    """
    Main page function. It will list the available collaborators and its
    clients.
    """
    cur = g.db.execute('select id, nome from colaboradores order by id asc')
    entries = [ dict(nome = row[1], id = row[0],
        listaIndicacoes = [], 
        indicacoes = 0,
        indicacoesValidas = 0,
        indicacoesAtivadas = 0) for row in cur.fetchall() ]

    cur = g.db.execute('select id, nome, conta, aplicacao, indicacao from clientes order by indicacao asc')
    clientsList = [ dict(id = row[0], nome = row[1],
        contaAberta = True if row[2] else False,
        contaAtiva = True if row[3] else False,
        indicacao = row[4]) for row in cur.fetchall() ]

    for client in clientsList:
        colaborador = entries[client['indicacao'] - 1]
        colaborador['listaIndicacoes'].append(client)
        colaborador['indicacoes'] += 1
        if client['contaAberta']:
            colaborador['indicacoesValidas'] += 1
        if client['contaAtiva']:
            colaborador['indicacoesAtivadas'] += 1

    return render_template('main.html', 
        colaboradores = sorted(entries, key = lambda k: k['indicacoes'], reverse = True),
        listaClientes = clientsList)


@app.route('/add_client', methods = ['POST'])
def add_client():
    cur = g.db.execute('select id from colaboradores where nome=?',
          [ request.form['colab-indicador'] ])

    if cur.fetchall():
        cur = g.db.execute('select id from colaboradores where nome=?',
                [ request.form['colab-indicador'] ])
        colaborador_id = cur.fetchall()[0][0]
        if request.form['cliente']:
            g.db.execute('insert into clientes (nome, indicacao) values (?, ?)',
                    [ request.form['cliente'], colaborador_id ])
            g.db.commit()

    else:
        if (request.form['colab-indicador']):
            g.db.execute('insert into colaboradores (nome) values (?)',
                [ request.form['colab-indicador'] ])
            g.db.commit()
            cur = g.db.execute('select id from colaboradores where nome=?',
                [ request.form['colab-indicador'] ])
            colaborador_id = cur.fetchall()[0][0]

            if request.form['cliente']:
                g.db.execute('insert into clientes (nome, indicacao) values (?, ?)',
                        [ request.form['cliente'], colaborador_id ])
                g.db.commit()
    return redirect(url_for('main_page'))


@app.route('/_remove_client')
def remove_client():
    colab_id = request.args.get('idColaborador', 0, type=int)
    cliente = request.args.get('idCliente', None, type=int)
    g.db.execute('delete from clientes where id=?', [ cliente ])
    g.db.commit()

    if (colab_id):
        listaDeClientes = updated_recommendations(colab_id)
        contasAbertas = map(lambda x: x['contaAberta'], listaDeClientes).count(True)
        contasAtivas = map(lambda x: x['contaAtiva'], listaDeClientes).count(True)

        return jsonify( total = len(listaDeClientes),
                        abertas = contasAbertas,
                        ativas = contasAtivas)


@app.route('/_open_acc')
def open_account():
    cliente_id = request.args.get('idCliente', None, type=int)
    colab_id = request.args.get('idColaborador', 0, type=int)
    checked = request.args.get('checked', 0, type=int)
    
    if (cliente_id):
        g.db.execute('update clientes set conta=? where id=?', 
                [ checked, cliente_id ])
        g.db.commit()

    if (colab_id):
        listaDeClientes = updated_recommendations(colab_id)
        contasAtivas = map(lambda x: x['contaAtiva'], listaDeClientes).count(True)
        contasAbertas = map(lambda x: x['contaAberta'], listaDeClientes).count(True)

        return jsonify( total = len(listaDeClientes), 
                        abertas = contasAbertas,
                        ativas = contasAtivas)

@app.route('/_activate_acc')
def activate_account():
    """
    This view will activate the given account.
    """
    cliente_id = request.args.get('idCliente', None, type=int)
    colab_id = request.args.get('idColaborador', 0, type=int)
    checked = request.args.get('checked', 0, type=int)

    if (cliente_id):
        g.db.execute('update clientes set aplicacao=? where id=?',
                [ checked, cliente_id ])
        g.db.commit()

    if (colab_id):
        listaDeClientes = updated_recommendations(colab_id)
        contasAtivadas = map(lambda x: x['contaAtiva'], listaDeClientes).count(True)
        contasAbertas = map(lambda x: x['contaAberta'], listaDeClientes).count(True)

        return jsonify( total = len(listaDeClientes),
                        ativas = contasAtivadas,
                        abertas = contasAbertas)


def updated_recommendations(colaboradorId):
    """
    This helper function is used to get the recommendations of a certain
    collaborator.
    """
    cur = g.db.execute('select id, nome, conta, aplicacao, indicacao from clientes where indicacao=?', [ colaboradorId ])
    clientsList = [ dict(id = row[0], nome = row[1],
        contaAberta = True if row[2] else False,
        contaAtiva = True if row[3] else False,
        indicacao = row[4]) for row in cur.fetchall() ]
    return clientsList


# execução
if __name__ == '__main__':
    #init_db()
    app.run();