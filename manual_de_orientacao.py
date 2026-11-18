"""
Manual de Orientação para Candidatos e Familiares: o texto que a família recebe na internação, escrito com o motor de
documentos (documentos.py), no timbre do sistema.

O TEXTO não mora aqui: vem da identidade da instituição (identidade.py), do arquivo manual.json do pacote. O pacote genérico traz um manual de
exemplo; o de cada instituição traz o dela. Para mudar o manual, é só mudar esse arquivo: cada linha é ["tipo", texto] e o tipo diz como ela sai
no papel:

    h    título de seção (negrito)          sub   subtítulo (negrito, recuado)
    p    parágrafo                          li    item de lista com marcador
    pt   parágrafo que começa com um título em negrito ("TÉRMINO DO TRATAMENTO: ...")
    ft   item de lista que começa com um nome sublinhado ("Disciplina: - o vício ...")
    il   linha recuada embaixo de um item   fim   fecho, centralizado

O texto pode usar {nome}, {apelido}, {nome_maiusculo}, {cidade} e {mantenedora}, que viram os dados da identidade (assim um pacote que só troca
o nome já sai com o nome certo).
"""

import string

from documentos import N, Pagina, Paragrafo, S, Texto
from identidade import atual as identidade

TAMANHO = 11
RECUO, MARCADOR = 720, 360


class _Deixa(dict):
    def __missing__(self, chave):
        return "{" + chave + "}"


def _com_os_dados(texto, marca):
    campos = _Deixa(nome=marca.nome, apelido=marca.apelido, nome_maiusculo=marca.nome.upper(), cidade=marca.cidade, mantenedora=marca.mantenedora)
    return string.Formatter().vformat(texto, (), campos)


def texto():
    """O manual da identidade em uso: lista de (tipo, texto), com os dados da instituição já no lugar."""
    marca = identidade()
    return [(tipo, _com_os_dados(linha, marca)) for tipo, linha in marca.manual["texto"]]


def _bloco(tipo, texto):
    base = {"tamanho": TAMANHO}
    if tipo == "h":
        return Paragrafo([N(texto)], antes=14, depois=4, unido_ao_proximo=True, **base)
    if tipo == "sub":
        return Paragrafo([N(texto)], antes=8, depois=3, recuo=RECUO, unido_ao_proximo=True, **base)
    if tipo == "p":
        return Paragrafo([texto], "justificado", primeira_linha=RECUO, depois=5, **base)
    if tipo == "pt":
        titulo, resto = texto.split("|")
        return Paragrafo([N(titulo), resto], "justificado", primeira_linha=RECUO, antes=4, depois=5, **base)
    if tipo == "li":
        return Paragrafo([texto], "justificado", recuo=RECUO + MARCADOR, suspenso=MARCADOR, numero="•", depois=3, **base)
    if tipo == "ft":
        nome, resto = texto.split("|")
        return Paragrafo([S(nome), " " + resto.lstrip()], "justificado", recuo=RECUO + MARCADOR, suspenso=MARCADOR, numero="•", depois=3, **base)
    if tipo == "il":
        return Paragrafo([texto], "justificado", recuo=RECUO + MARCADOR, depois=3, **base)
    return Paragrafo([N(texto)], "centro", antes=26, **base)                 # fim


def blocos():
    """O manual: capa e, em página nova, o texto."""
    titulo, subtitulo = identidade().manual["capa"]
    capa = [Pagina(),
            Paragrafo([Texto(titulo, negrito=True)], "centro", tamanho=24, fonte="Times New Roman", antes=190),
            Paragrafo([Texto(subtitulo, negrito=True)], "centro", tamanho=24, fonte="Times New Roman", antes=14)]
    corpo = [_bloco(tipo, linha) for tipo, linha in texto()]
    corpo[0].quebra_antes = True
    return capa + corpo
