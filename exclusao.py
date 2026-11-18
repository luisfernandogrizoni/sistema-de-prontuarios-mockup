"""
Excluir um registro em duas etapas.

  * Quem não é administrador "exclui": o registro (a triagem ou a internação, e a pessoa, se era o único registro dela)
    é só marcado como excluído. Ele some das listas, da página inicial, das vagas, dos relatórios, das buscas e dos
    avisos, mas continua no banco.
  * O administrador vê o que foi excluído (Cadastros > Lixeira), pode restaurar ou apagar de vez do banco, e também pode
    apagar de vez direto da ficha.

O "some de tudo" é uma regra só, aplicada a TODA consulta ao banco (o gancho `do_orm_execute` abaixo): nenhuma tela
precisa lembrar de filtrar. Quem precisa ver os excluídos (a lixeira, restaurar, apagar) abre `vendo_tudo()`.

O mesmo gancho tem uma segunda regra, que depende de QUEM está pedindo: os registros IMPORTADOS que ainda não foram conferidos com o prontuário físico (Internacao.origem
preenchida e conferido_em vazio; veja conferencia.py) são dado não tratado e só o administrador os vê (a permissão fixa `conferir`). Para os outros funcionários eles somem de
tudo, como os excluídos: listas, buscas, página inicial, vagas, avisos, relatórios, a ficha (404) e as contribuições. A pessoa que só tem registros assim também some. Quem tem um
registro digitado e outro importado ainda não conferido continua aparecendo, só com o digitado. A regra liga em `g.esconder_nao_conferidos` (app.py, logo depois do login); fora de uma
requisição (importador, scripts, backup) nada é escondido. Quem precisa olhar por cima da regra (a checagem de CPF repetido) abre `vendo_nao_conferidos()`.
Este módulo precisa ser importado uma vez na subida do sistema (app.py).
"""

from contextlib import contextmanager
from datetime import datetime

from flask import g, has_app_context
from sqlalchemy import and_, event, exists, func, or_
from sqlalchemy.orm import Session, with_loader_criteria

import anexos
from modelos import AvisoDispensado, Internacao, Pessoa, Rascunho, db

# avisos que citam o registro (avisos.py): ao apagar de vez, as dispensas deles também vão (o SQLite reaproveita ids)
AVISOS_DA_INTERNACAO = ("respcpf", "seminicio", "semtermino", "desistinicio", "agendavencida", "envelope", "rejeicao", "acolhimento")
AVISOS_DA_PESSOA = ("cpf", "tel")


def _vendo_tudo():
    return has_app_context() and g.get("vendo_excluidos", False)


def _escondendo_nao_conferidos():
    return has_app_context() and g.get("esconder_nao_conferidos", False)


def _importada_e_nao_conferida():
    """A condição, na tabela (não na entidade: não passa pela regra de novo): importado (origem preenchida) e ainda sem conferência."""
    t = Internacao.__table__.c
    return and_(func.coalesce(t.origem, "") != "", t.conferido_em.is_(None))


def _internacao_visivel(c):
    return or_(func.coalesce(c.origem, "") == "", c.conferido_em.is_not(None))


def _pessoa_visivel(c):
    """A pessoa some quando só tem registros importados ainda não conferidos (e tem pelo menos um): se tem algum registro digitado ou já conferido, continua."""
    tabela = Internacao.__table__
    t = tabela.c
    viva = t.excluido_em.is_(None)
    # (a tabela dos registros fica DENTRO da subconsulta e só a pessoa de fora é correlacionada: senão uma consulta que já traz os registros no FROM deixaria a subconsulta sem FROM)
    com = lambda condicao: exists().where(and_(t.pessoa_id == c.id, viva, condicao)).select_from(tabela).correlate_except(tabela)
    so_nao_conferidos = and_(com(_importada_e_nao_conferida()), ~com(~_importada_e_nao_conferida()))
    return ~so_nao_conferidos


@event.listens_for(Session, "do_orm_execute")
def _esconder_excluidos(estado):
    """Toda leitura ignora o que foi excluído e, para quem não pode conferir, o que é importado e ainda não foi conferido (as releituras de colunas e as cargas de
    relacionamento já herdam isso)."""
    if not estado.is_select or estado.is_column_load or estado.is_relationship_load:
        return
    if not _vendo_tudo():
        estado.statement = estado.statement.options(
            with_loader_criteria(Internacao, lambda c: c.excluido_em.is_(None), include_aliases=True),
            with_loader_criteria(Pessoa, lambda c: c.excluido_em.is_(None), include_aliases=True))
    if _escondendo_nao_conferidos():
        estado.statement = estado.statement.options(
            with_loader_criteria(Internacao, _internacao_visivel, include_aliases=True),
            with_loader_criteria(Pessoa, _pessoa_visivel, include_aliases=True))


@contextmanager
def vendo_nao_conferidos():
    """Dentro do bloco, as consultas enxergam também os importados que ainda não foram conferidos (só para checagens que não mostram o que acharam: o CPF repetido)."""
    antes = g.get("esconder_nao_conferidos", False)
    g.esconder_nao_conferidos = False
    try:
        yield
    finally:
        g.esconder_nao_conferidos = antes


@contextmanager
def vendo_tudo():
    """Dentro do bloco, as consultas enxergam também os registros excluídos."""
    antes = g.get("vendo_excluidos", False)
    g.vendo_excluidos = True
    try:
        yield
    finally:
        g.vendo_excluidos = antes


# ------------------------------------------------------------------ as ações
def excluir(internacao, usuario=""):
    """Tira o registro de circulação (sem apagar). A pessoa também sai, se este era o único registro dela."""
    agora = datetime.now()
    internacao.excluido_em, internacao.excluido_por = agora, (usuario or "")[:50]
    pessoa = internacao.pessoa
    if not any(outro.id != internacao.id for outro in pessoa.internacoes):     # só enxerga os que não foram excluídos
        pessoa.excluido_em = agora
    db.session.commit()


def restaurar(internacao):
    """Devolve à circulação. Chamar dentro de `vendo_tudo()`."""
    internacao.excluido_em, internacao.excluido_por = None, ""
    internacao.pessoa.excluido_em = None
    db.session.commit()


def apagar(internacao):
    """Apaga do banco: o registro, o que depende dele (parcelas, relatórios) e a pessoa, se não sobrou nenhum registro
    dela. Não tem volta. Chamar dentro de `vendo_tudo()`."""
    pessoa, id_internacao, id_pessoa = internacao.pessoa, internacao.id, internacao.pessoa_id
    arquivos = anexos.arquivos_do_registro(internacao)            # os PDFs dos documentos escaneados: as linhas saem com o registro, os arquivos saem depois
    db.session.delete(internacao)
    db.session.execute(db.delete(Rascunho).filter_by(internacao_id=id_internacao))        # o que alguém digitava sobre este registro
    db.session.flush()
    _limpar_dispensas(AVISOS_DA_INTERNACAO, id_internacao)
    if not db.session.execute(db.select(db.func.count(Internacao.id)).filter_by(pessoa_id=id_pessoa)).scalar():
        db.session.delete(pessoa)
        _limpar_dispensas(AVISOS_DA_PESSOA, id_pessoa)
    db.session.commit()
    anexos.apagar_arquivos(id_internacao, arquivos)


def _limpar_dispensas(prefixos, id_):
    for prefixo in prefixos:
        for chave in db.session.execute(db.select(AvisoDispensado).filter(AvisoDispensado.chave.like(f"{prefixo}:{id_}%"))).scalars():
            if chave.chave == f"{prefixo}:{id_}" or chave.chave.startswith(f"{prefixo}:{id_}:"):
                db.session.delete(chave)


# ------------------------------------------------------------------ a lixeira
def excluidos():
    """Os registros excluídos, o mais recente primeiro. Chamar dentro de `vendo_tudo()`."""
    return db.session.execute(db.select(Internacao).filter(Internacao.excluido_em.isnot(None))
                              .order_by(Internacao.excluido_em.desc(), Internacao.id.desc())).scalars().all()


def quantos_excluidos():
    with vendo_tudo():
        return db.session.execute(db.select(db.func.count(Internacao.id)).filter(Internacao.excluido_em.isnot(None))).scalar()
