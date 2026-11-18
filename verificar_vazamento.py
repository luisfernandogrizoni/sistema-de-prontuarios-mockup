"""
Confere se algum dado dos internos foi parar no git.

    python verificar_vazamento.py           # o que entraria no próximo commit (o hook usa este)
    python verificar_vazamento.py --tudo    # todo o histórico, de todas as branches

Procura (1) arquivos que parecem dados — bancos, planilhas, exportações, chaves, .env —,
(2) dentro de qualquer arquivo (inclusive .docx), nomes completos, CPFs e telefones que
existem no banco local e (3) trechos que identificam a INSTITUIÇÃO (nome, endereço, CNPJ,
telefones, e-mails, textos próprios), tirados do pacote de identidade da instituição (identidade.py).
Esses trechos só podem estar no pacote (identidades/casa/) e nos caminhos de mockup.exclui: o
resto do código tem de ficar genérico, porque é ele que o mockup público (publicar_mockup.py) recebe.
Só mostra o NOME DO ARQUIVO e quantas coisas achou, nunca os dados.
Sem o banco local ou sem o pacote (outra máquina), valem só as verificações que dá para fazer.

Bloqueio automático antes de cada commit (uma vez por clone):
    git config core.hooksPath hooks
"""

import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

RAIZ = Path(__file__).parent
BANCO_LOCAL = RAIZ / "instance" / "internos.db"
ARQUIVO_DE_DADOS = re.compile(
    r"(^|/)instance/|(^|/)\.env|\.(db|db-journal|sqlite3?|csv|xlsx?|sql|dump|bak|key|pem)$", re.I)
CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
TELEFONE = re.compile(r"(?<!\d)\(?\d{2}\)?\s?9?\d{4}-?\d{4}(?!\d)")


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").lower()


def digitos(texto):
    return re.sub(r"\D", "", texto or "")


def dados_reais():
    """(regex de nomes, CPFs, telefones) que existem no banco local — vazios se não houver banco."""
    if not BANCO_LOCAL.exists():
        return None, set(), set()
    banco = sqlite3.connect(f"file:{BANCO_LOCAL.as_posix()}?mode=ro", uri=True)
    nomes, cpfs, telefones = set(), set(), set()
    consultas = [("select nome, mae, conjuge, cpf, contato1, contato2, contato3 from pessoas", 3),
                 ("select resp_nome, '', '', resp_cpf, '', '', '' from internacoes", 3)]
    for sql, n_nomes in consultas:
        for linha in banco.execute(sql):
            nomes.update(sem_acento(n).strip() for n in linha[:n_nomes] if len((n or "").split()) >= 2)
            cpfs.add(digitos(linha[3]))
            telefones.update(digitos(t) for t in linha[4:])
    cpfs = {c for c in cpfs if len(c) == 11}
    telefones = {t for t in telefones if len(t) in (10, 11)}
    padrao = re.compile(r"(?<![a-z])(?:" + "|".join(map(re.escape, sorted(nomes))) + r")(?![a-z])") if nomes else None
    return padrao, cpfs, telefones


def caminhos_privados():
    """Os caminhos que só existem no repositório real (mockup.exclui): o pacote da instituição e as ferramentas dela."""
    arquivo = RAIZ / "mockup.exclui"
    if not arquivo.is_file():
        return []
    linhas = (l.strip() for l in arquivo.read_text(encoding="utf-8").splitlines())
    return [l for l in linhas if l and not l.startswith("#")]


def e_privado(caminho):
    """True se o caminho (relativo, com / ) está na lista de mockup.exclui."""
    limpo = caminho.split(" (")[0].replace("\\", "/")
    return any(limpo == p or (p.endswith("/") and limpo.startswith(p)) for p in caminhos_privados())


def _pacotes_da_instituicao():
    """Onde pode estar o pacote de identidade da instituição neste computador: IDENTIDADE_PASTA, instance/identidade ou as pastas de identidades/ (menos a genérica)."""
    candidatos = [os.environ.get("IDENTIDADE_PASTA"), RAIZ / "instance" / "identidade", *sorted((RAIZ / "identidades").glob("*"))]
    return [Path(c) for c in candidatos if c and Path(c).name != "generica" and (Path(c) / "identidade.json").is_file()]


# chaves do pacote que só têm palavras comuns (listas de apoio, o nome curto "Casa de Acolhida"...): não identificam ninguém sozinhas
CHAVES_SEM_IDENTIFICACAO = {"palavras_fracas", "cores_antigas", "apelido", "convenio_apelidos", "convenios"}


def _textos_do_json(valor):
    """Todos os textos de um JSON (valores, em qualquer profundidade), sem as chaves que só têm palavras comuns."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for chave, v in valor.items():
            if chave not in CHAVES_SEM_IDENTIFICACAO:
                yield from _textos_do_json(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _textos_do_json(v)


def dados_da_instituicao():
    """Trechos (sem acento, minúsculos) que identificam a instituição, vindos do pacote dela, menos os que o pacote genérico também tem.
    Lista vazia se não há pacote neste computador."""
    pacotes = _pacotes_da_instituicao()
    if not pacotes:
        return []
    generico = RAIZ / "identidades" / "generica"
    comuns = sem_acento(" ".join(t for arquivo in ("identidade.json", "manual.json") if (generico / arquivo).is_file()
                                 for t in _textos_do_json(json.loads((generico / arquivo).read_text(encoding="utf-8")))))
    trechos = set()
    for pasta in pacotes:
        for arquivo in ("identidade.json", "manual.json"):
            if (pasta / arquivo).is_file():
                for texto in _textos_do_json(json.loads((pasta / arquivo).read_text(encoding="utf-8"))):
                    t = sem_acento(texto).strip()
                    # uma palavra solta ("restauração", "cidade") também é palavra comum: vale só o que tem mais de uma palavra, número, e-mail ou site
                    if len(t) >= 6 and t not in comuns and (" " in t or any(c in t for c in "@./0123456789")):
                        trechos.add(t)
    return sorted(trechos)


def decodificar(conteudo):
    """UTF-8 e, se não for, a codificação antiga do Windows: sem perder as letras acentuadas
    (um 'José' salvo em cp1252 não pode virar 'Jos' e escapar da busca)."""
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", "ignore")


def texto_do_arquivo(caminho, conteudo):
    """Texto legível do arquivo; para .docx/.xlsx, o texto dos XMLs de dentro."""
    if caminho.lower().endswith((".docx", ".xlsx", ".zip")):
        try:
            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                xmls = (decodificar(z.read(n)) for n in z.namelist() if n.endswith(".xml"))
                return re.sub(r"<[^>]+>", "", " ".join(xmls))
        except zipfile.BadZipFile:
            pass
    return decodificar(conteudo)


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, check=True).stdout


def itens_do_proximo_commit():
    for caminho in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode().split("\0"):
        if caminho:
            yield caminho, git("show", f":{caminho}")


def itens_de_todo_o_historico():
    vistos = set()
    for linha in git("rev-list", "--objects", "--all").decode().splitlines():
        sha, _, caminho = linha.partition(" ")
        if caminho and sha not in vistos:
            vistos.add(sha)
            if git("cat-file", "-t", sha).strip() == b"blob":
                yield f"{caminho} ({sha[:7]})", git("cat-file", "blob", sha)


def verificar(itens):
    padrao, cpfs, telefones = dados_reais()
    instituicao = dados_da_instituicao()
    problemas = []
    for caminho, conteudo in itens:
        if ARQUIVO_DE_DADOS.search(caminho.split(" (")[0]):
            problemas.append(f"{caminho}: parece um arquivo de dados (banco, planilha, chave...)")
            continue
        texto = texto_do_arquivo(caminho.split(" (")[0], conteudo)
        achados_nomes = len(set(padrao.findall(sem_acento(texto)))) if padrao else 0
        achados_cpfs = len({digitos(c) for c in CPF.findall(texto)} & cpfs)
        achados_tels = len({digitos(t) for t in TELEFONE.findall(texto)} & telefones)
        if achados_nomes or achados_cpfs or achados_tels:
            problemas.append(f"{caminho}: {achados_nomes} nome(s), {achados_cpfs} CPF(s) e "
                             f"{achados_tels} telefone(s) de pessoas do banco")
        if instituicao and not e_privado(caminho):
            minusculo = sem_acento(texto)
            achados_instituicao = sum(1 for t in instituicao if t in minusculo)
            if achados_instituicao:
                problemas.append(f"{caminho}: {achados_instituicao} trecho(s) que identificam a instituição (nome, endereço, CNPJ, textos próprios)")
    return problemas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tudo = "--tudo" in sys.argv
    problemas = verificar(itens_de_todo_o_historico() if tudo else itens_do_proximo_commit())
    if not problemas:
        print("Nenhum dado de interno encontrado" + (" em todo o histórico." if tudo else " no commit.")
              + ("" if dados_da_instituicao() else " (Sem pacote de identidade neste computador: não conferi os dados da instituição.)"))
        return 0
    print("ATENÇÃO — dados dos internos e da instituição não podem ir para o git:\n")
    print("\n".join(f"  - {p}" for p in problemas))
    print("\nTire isso do commit (git restore --staged <arquivo>) e troque por dados fictícios.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
