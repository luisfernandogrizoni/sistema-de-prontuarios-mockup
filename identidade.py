"""
A identidade da instituição: nome, logos, timbre, endereço, quem assina e os textos que falam em nome dela.

Nada disso mora no código. Tudo vem de um PACOTE DE IDENTIDADE, uma pasta com este formato:

    identidade.json     nome, timbre (cabeçalho e rodapé), cidade, quem assina, convênios de fábrica, textos dos documentos...
    manual.json         o Manual de Orientação que a família recebe (capa e texto)
    marca/              logo.png, favicon.ico, favicon-32.png, favicon-48.png, apple-touch-icon.png   (as telas)
    timbre/             logo-topo.jpg e logo-rodape.jpg                                                (os documentos)

Qual pacote vale (nesta ordem):

  1. a pasta indicada pela variável de ambiente IDENTIDADE_PASTA (para testes);
  2. o pacote de `identidades/<nome>/` indicado pela variável IDENTIDADE (IDENTIDADE=generica força o genérico, por exemplo para tirar capturas de tela);
  3. a pasta `instance/identidade/` (uma instalação que guarda o pacote só no servidor: `instance/` nunca vai para o git);
  4. o único pacote de instituição que existir em `identidades/` além do genérico (no repositório real, privado, é `identidades/casa/`: por isso o
     desenvolvimento e o servidor mostram a instituição sem configurar nada);
  5. o pacote GENÉRICO, `identidades/generica/`, que vem junto do código. É o que o mockup público tem, porque a pasta da instituição não vai para ele
     (publicar_mockup.py; docs/publicacao-do-mockup.md).

Um pacote pode ser parcial: o que ele não traz vem do genérico (arquivos e chaves). Se faltar alguma chave de texto, o sistema avisa
no registro de erros ao subir (`faltando()`), para o texto genérico não aparecer sem ninguém notar num documento da instituição.

As imagens do pacote saem em /static/identidade/... (instalar() troca a rota `static` por uma que sabe disso), e os documentos em Word
leem os mesmos arquivos pelo caminho em disco (`caminho()`).
"""

import json
import os
import string
from pathlib import Path

RAIZ = Path(__file__).parent
PASTA_GENERICA = RAIZ / "identidades" / "generica"
PASTA_DA_INSTANCIA = RAIZ / "instance" / "identidade"
PREFIXO_ESTATICO = "identidade/"          # /static/identidade/marca/logo.png

# as chaves que um pacote precisa ter para a instituição não aparecer com texto do genérico (o genérico é a referência)
CHAVES_DE_TEXTO = "textos"


class _Faltante(dict):
    def __missing__(self, chave):
        return "{" + chave + "}"


def _mesclar(base, extra):
    """`extra` por cima de `base`: dicionários se juntam chave a chave (textos, e-mail, emissor); o resto (listas, textos) é trocado."""
    saida = dict(base)
    for chave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(saida.get(chave), dict):
            saida[chave] = _mesclar(saida[chave], valor)
        else:
            saida[chave] = valor
    return saida


def _ler_json(arquivo):
    return json.loads(Path(arquivo).read_text(encoding="utf-8"))


def _arquivo_em(pasta, relativo):
    """O arquivo `relativo` dentro de `pasta` (ou None). Nunca sai da pasta: '..', caminho absoluto e letra de unidade (C:/...) não passam."""
    if pasta is None:
        return None
    base = Path(pasta).resolve()
    alvo = (base / relativo).resolve()                 # (um caminho absoluto no lugar do relativo troca a base: o is_relative_to abaixo o barra)
    return alvo if alvo.is_relative_to(base) and alvo.is_file() else None


def pacotes_do_repositorio():
    """Os pacotes de instituição que vêm no repositório: as pastas de `identidades/` com identidade.json, menos o genérico."""
    raiz = RAIZ / "identidades"
    if not raiz.is_dir():
        return []
    return sorted(p for p in raiz.iterdir() if p.is_dir() and p.name != "generica" and (p / "identidade.json").is_file())


def pasta_do_pacote():
    """A pasta do pacote da instituição (ou None: vale o genérico)."""
    indicada = os.environ.get("IDENTIDADE_PASTA")
    if indicada:
        pasta = Path(indicada)
        if not (pasta / "identidade.json").is_file():
            raise RuntimeError(f"IDENTIDADE_PASTA aponta para {pasta}, que não tem identidade.json")
        return pasta
    nome = (os.environ.get("IDENTIDADE") or "").strip()
    if nome:
        if nome == "generica":
            return None
        pasta = RAIZ / "identidades" / nome
        if not (pasta / "identidade.json").is_file():
            raise RuntimeError(f"IDENTIDADE={nome}, mas não existe identidades/{nome}/identidade.json")
        return pasta
    if (PASTA_DA_INSTANCIA / "identidade.json").is_file():
        return PASTA_DA_INSTANCIA
    do_repositorio = pacotes_do_repositorio()
    if len(do_repositorio) > 1:
        raise RuntimeError("Há mais de um pacote de instituição em identidades/ (" + ", ".join(p.name for p in do_repositorio) + "): diga qual vale em IDENTIDADE.")
    return do_repositorio[0] if do_repositorio else None


class Identidade:
    """Os dados do pacote em uso. Os campos do identidade.json saem como atributos (`identidade.nome`, `identidade.cidade`...)."""

    def __init__(self, pasta=None):
        self.pasta = Path(pasta) if pasta else None
        generica = _ler_json(PASTA_GENERICA / "identidade.json")
        proprio = _ler_json(self.pasta / "identidade.json") if self.pasta else {}
        self.dados = _mesclar(generica, proprio)
        self._manual = None
        self._faltam = []
        if self.pasta:
            for chave in generica.get(CHAVES_DE_TEXTO, {}):
                if chave not in proprio.get(CHAVES_DE_TEXTO, {}):
                    self._faltam.append(f"{CHAVES_DE_TEXTO}.{chave}")
            if not (self.pasta / "manual.json").is_file():
                self._faltam.append("manual.json")

    # ------------------------------------------------------------ campos
    def __getattr__(self, chave):
        dados = self.__dict__.get("dados", {})
        if chave in dados:
            return dados[chave]
        raise AttributeError(f"a identidade não tem o campo {chave!r}")

    @property
    def generica(self):
        """True quando vale o pacote genérico (nenhum pacote de instituição instalado)."""
        return self.pasta is None

    @property
    def emissor_nome(self):
        return self.dados["emissor"]["nome"]

    @property
    def emissor_cargo(self):
        return self.dados["emissor"]["cargo"]

    @property
    def assinatura_do_email(self):
        """O rodapé de toda mensagem automática que o sistema manda por e-mail."""
        return f"\n\n—\n{self.nome} · {self.sistema}\nMensagem automática: não responda."

    def faltando(self):
        """O que o pacote da instituição não traz (e por isso vem do genérico): lista de nomes, vazia quando está completo."""
        return list(self._faltam)

    # ------------------------------------------------------------ textos
    def texto(self, chave, **campos):
        """Um texto do pacote, com {campo} preenchidos, sem formatação (só o texto corrido)."""
        return "".join(p if isinstance(p, str) else p["n"] for p in self._segmentos(chave, campos))

    def partes(self, chave, **campos):
        """Um texto do pacote como lista de trechos para um parágrafo (documentos.py): texto simples ou N(...) em negrito."""
        from documentos import N
        return [p if isinstance(p, str) else N(p["n"]) for p in self._segmentos(chave, campos)]

    def _segmentos(self, chave, campos):
        bruto = self.dados[CHAVES_DE_TEXTO][chave]
        if isinstance(bruto, str):
            bruto = [bruto]
        formatador = string.Formatter()
        saida = []
        for parte in bruto:
            if isinstance(parte, str):
                saida.append(formatador.vformat(parte, (), _Faltante(campos)))
            else:
                saida.append({"n": formatador.vformat(parte["n"], (), _Faltante(campos))})
        return saida

    # ------------------------------------------------------------ manual
    @property
    def manual(self):
        """O manual de orientação: {"capa": [titulo, subtitulo], "texto": [[tipo, texto], ...]} (manual_de_orientacao.py)."""
        if self._manual is None:
            arquivo = self.pasta / "manual.json" if self.pasta and (self.pasta / "manual.json").is_file() else PASTA_GENERICA / "manual.json"
            self._manual = _ler_json(arquivo)
        return self._manual

    # ------------------------------------------------------------ arquivos
    def caminho(self, relativo):
        """O arquivo da identidade ("marca/logo.png", "timbre/logo-topo.jpg") em disco: o do pacote, ou o do genérico se o pacote não o traz."""
        return _arquivo_em(self.pasta, relativo) or _arquivo_em(PASTA_GENERICA, relativo) or PASTA_GENERICA / relativo

    def url(self, relativo):
        """O endereço da imagem nas páginas."""
        from flask import url_for
        return url_for("static", filename=PREFIXO_ESTATICO + relativo)


_atual = None


def atual():
    """A identidade em uso (lida uma vez por processo)."""
    global _atual
    if _atual is None:
        _atual = Identidade(pasta_do_pacote())
    return _atual


def recarregar(pasta=None, *, forcar=False):
    """Troca a identidade em uso (testes): `pasta` é o pacote; sem ela, volta ao que a configuração manda (ou ao genérico com `forcar`)."""
    global _atual
    _atual = Identidade(pasta) if (pasta or forcar) else Identidade(pasta_do_pacote())
    return _atual


def instalar(app):
    """Liga a identidade ao Flask: a rota `static` passa a servir também /static/identidade/... (do pacote, com o genérico de reserva) e as páginas
    ganham a variável `identidade`. Mantém o endpoint `static`, então todas as regras de acesso dos arquivos estáticos continuam valendo."""
    from flask import abort, send_from_directory

    estatico_original = app.view_functions["static"]

    def servir(filename):
        if filename.startswith(PREFIXO_ESTATICO):
            relativo = filename[len(PREFIXO_ESTATICO):]
            for pasta in (atual().pasta, PASTA_GENERICA):         # o pacote primeiro, o genérico de reserva
                if _arquivo_em(pasta, relativo):
                    return send_from_directory(pasta, relativo)    # (e o send_from_directory confere de novo: recusa ".." e caminhos fora da pasta)
            abort(404)
        return estatico_original(filename=filename)

    app.view_functions["static"] = servir
    app.context_processor(lambda: {"identidade": atual()})
    faltam = atual().faltando()
    if faltam:
        app.logger.warning("Pacote de identidade incompleto (%s): o que falta vem do genérico: %s", atual().pasta, ", ".join(faltam))
    if atual().generica:
        app.logger.info("Identidade: pacote genérico (nenhum pacote da instituição em instance/identidade).")
