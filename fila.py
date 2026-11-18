"""
A lista de espera: quem espera vaga, em que ordem chamar e o que já foi tentado com cada um.

Regras
  * Cada CATEGORIA tem a sua fila, porque a vaga é por categoria (vagas.py): uma vaga de Caps AD não serve a um particular. A categoria de quem espera é a do convênio dele
    (prontuario.categoria_vaga). Quem ainda está com o convênio "a definir" fica no grupo "Sem categoria definida": entra na conta da espera, mas não é chamado.
  * A ordem de chamada é a de CHEGADA: `Internacao.fila_desde`, carimbado sozinho quando a triagem vira "lista de espera" (modelos.py). A equipe pode ajustar subindo,
    descendo ou levando alguém ao topo (`fila_ordem`, um número na mesma escala do carimbo: quem nunca foi mexido segue a chegada).
  * Quem chamar: a categoria com vaga livre (vagas.py) menos as vagas que já têm dono. Têm dono quem aceitou a vaga ou já tem a internação marcada (agendada para hoje ou
    depois), esteja na fila ou em admissão. Quem pediu para ligar mais tarde (dia combinado ainda não chegou) mantém a posição mas é pulado na hora de chamar.
  * Cada tentativa de contato fica registrada (`ContatoFila`): quando, quem, o resultado e o dia combinado para ligar de novo. Só se acrescenta.
  * "Desistiu" tira a pessoa da fila (a triagem vira desistência); "aceitou" não muda a situação: a pessoa segue na fila até ser admitida, marcada como chamada.

Nada disto fica gravado além do carimbo, da posição manual, do dia de ligar de novo e dos contatos: quem está na fila, a posição e as vagas a chamar são calculados a
cada visita, como os avisos e as vagas.
"""

from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy.orm import joinedload, selectinload

import vagas as quadro_de_vagas
from modelos import ContatoFila, Internacao, db
from prontuario import categoria_vaga, fmt_data, tipo_da_categoria
from validacao import so_digitos

SEM_CATEGORIA = "Sem categoria definida"
LIMITE_DOS_PROXIMOS = 3          # quantos nomes o quadro de vagas da página inicial mostra por categoria com vaga livre

# resultado de uma tentativa de contato: chave -> (rótulo, a tela oferece "ligar de novo em")
RESULTADOS = {
    "nao_atendeu": ("Não atendeu", True),
    "ligar_depois": ("Pediu para ligar mais tarde", True),
    "aceitou": ("Aceitou a vaga", False),
    "recusou": ("Não pode agora (segue na fila)", True),
    "desistiu": ("Desistiu (sai da fila)", False),
}
COM_RETORNO = {chave for chave, (_, retorno) in RESULTADOS.items() if retorno}
ACOES_DE_MOVER = {"subir": "subiu uma posição", "descer": "desceu uma posição", "topo": "foi para o topo da fila"}
ROTULOS_DOS_CONTATOS = (("contato1", "Família / responsável"), ("contato2", "Outro"), ("contato3", "Do próprio"))


def categoria_de(internacao):
    """A categoria da vaga que esta pessoa ocuparia (None enquanto o convênio é "a definir")."""
    return categoria_vaga(internacao.convenio, internacao.contribuicao_valor or 0.0)


def _segundos(momento):
    """O momento numa escala só (segundos desde 2000): é nela que a ordem de chegada e a posição manual se comparam."""
    return (momento - datetime(2000, 1, 1)).total_seconds()


def _chave(internacao):
    """A posição: a manual, se alguém subiu ou desceu a pessoa; senão a hora em que entrou na fila (na falta dela, a do cadastro)."""
    if internacao.fila_ordem is not None:
        base = internacao.fila_ordem
    else:
        base = _segundos(internacao.fila_desde or internacao.criado_em or datetime(2000, 1, 1))
    return (base, internacao.id)


class Entrada:
    """Uma pessoa na fila, com o que a tela mostra dela. Montada por `na_fila`."""

    def __init__(self, internacao, hoje):
        self.internacao = internacao
        self.id = internacao.id
        self.pessoa = internacao.pessoa
        self.nome = internacao.pessoa.nome
        self.categoria = categoria_de(internacao)
        self.tipo = tipo_da_categoria(self.categoria) if self.categoria else "outro"
        self.posicao = None                                  # a vez dela na fila da categoria (preenchida por `na_fila`)
        self.desde = (internacao.fila_desde or internacao.criado_em or datetime.now()).date()
        self.dias_esperando = max(0, (hoje - self.desde).days)
        contatos = internacao.contatos_fila
        self.contatos = list(reversed(contatos))             # do mais recente para o mais antigo
        self.ultimo = contatos[-1] if contatos else None
        self.retornar_em = internacao.fila_retornar_em
        self.aguardando = bool(self.retornar_em and self.retornar_em > hoje)          # pediu para ligar mais tarde: segue na posição, mas ainda não é a vez de ligar
        self.retorno_vencido = bool(self.retornar_em and self.retornar_em <= hoje)
        agendada = internacao.internacao_agendada
        self.agendada = agendada if agendada and agendada >= hoje else None
        self.chamada = bool((self.ultimo and self.ultimo.resultado == "aceitou") or self.agendada)      # a vaga dela já tem dono
        self.telefones = [(rotulo, getattr(internacao.pessoa, campo), so_digitos(getattr(internacao.pessoa, campo)))      # (rótulo, como está escrito, só os números do tel:)
                          for campo, rotulo in ROTULOS_DOS_CONTATOS if getattr(internacao.pessoa, campo)]
        self.responsavel = " · ".join(p for p in (internacao.resp_nome, internacao.parentesco) if p)

    @property
    def desde_fmt(self):
        return fmt_data(self.desde)

    @property
    def espera_txt(self):
        n = self.dias_esperando
        return "chegou hoje" if n == 0 else f"{n} dia{'' if n == 1 else 's'} na fila"


def na_fila(hoje=None):
    """Todos os que estão em "lista de espera", agrupados por categoria e em ordem de chamada: {categoria (ou None): [Entrada, ...]}. A `posicao` de cada um é a vez
    dele na fila da própria categoria."""
    hoje = hoje or date.today()
    internacoes = db.session.execute(
        db.select(Internacao).filter(Internacao.status == "lista_espera")
        .options(joinedload(Internacao.pessoa), selectinload(Internacao.contatos_fila))).scalars().unique().all()
    grupos = defaultdict(list)
    for internacao in sorted(internacoes, key=_chave):
        entrada = Entrada(internacao, hoje)
        grupos[entrada.categoria].append(entrada)
    for entradas in grupos.values():
        for n, entrada in enumerate(entradas, 1):
            entrada.posicao = n
    return dict(grupos)


def _reservadas(hoje, grupos):
    """Vagas que já têm dono, por categoria: quem já tem a internação marcada (hoje ou depois), na fila ou em admissão, e quem na fila aceitou a vaga e ainda não tem
    o dia marcado."""
    marcadas = db.session.execute(
        db.select(Internacao).filter(Internacao.status.in_(("em_admissao", "lista_espera")), Internacao.internacao_agendada >= hoje)).scalars().all()
    reservadas = Counter(categoria_de(i) for i in marcadas)
    reservadas.update(e.categoria for entradas in grupos.values() for e in entradas if e.chamada and not e.agendada)
    return reservadas


def resumo(lista_de_vagas=None, hoje=None):
    """O retrato da fila para as telas:
         categorias  [{categoria, tipo, vaga (o dict de vagas.py ou None), livres, reservadas, a_chamar, entradas, proximos}, ...] das que têm gente esperando, na ordem do
                     quadro de vagas; `proximos` são os primeiros a chamar (tantos quantas as vagas a preencher), `a_chamar` quantas vagas ainda precisam de alguém;
         sem_categoria  as Entrada de quem está com o convênio a definir;
         total  quantos esperam."""
    hoje = hoje or date.today()
    lista_de_vagas = lista_de_vagas if lista_de_vagas is not None else quadro_de_vagas.gerar_vagas()
    grupos = na_fila(hoje)
    reservadas = _reservadas(hoje, grupos)
    por_categoria = {v["categoria"]: v for v in lista_de_vagas}
    ordem = [v["categoria"] for v in lista_de_vagas]
    ordem += sorted(c for c in grupos if c is not None and c not in por_categoria)          # (um convênio desativado e sem ninguém internado já não está no quadro)
    categorias = []
    for categoria in ordem:
        entradas = grupos.get(categoria)
        if not entradas:
            continue
        vaga = por_categoria.get(categoria)
        limite = vaga["limite"] if vaga else None
        livres = max(0, limite - vaga["ocupadas"]) if limite is not None else None
        a_chamar = max(0, livres - reservadas[categoria]) if livres is not None else 0
        candidatos = [e for e in entradas if not e.chamada and not e.aguardando]
        categorias.append({"categoria": categoria, "tipo": entradas[0].tipo, "vaga": vaga, "livres": livres, "reservadas": reservadas[categoria], "a_chamar": a_chamar,
                           "entradas": entradas, "proximos": candidatos[:a_chamar]})
    return {"categorias": categorias, "sem_categoria": grupos.get(None, []), "total": sum(len(v) for v in grupos.values())}


def para_chamar(resumo_da_fila):
    """Só as categorias que têm vaga a preencher e alguém a chamar: {categoria: info}."""
    return {c["categoria"]: c for c in resumo_da_fila["categorias"] if c["proximos"]}


def na_fila_por_categoria(resumo_da_fila):
    """{categoria: quantos esperam}, para o quadro de vagas mostrar "3 na fila" mesmo quando a categoria está lotada."""
    return {c["categoria"]: len(c["entradas"]) for c in resumo_da_fila["categorias"]}


# ---------------------------------------------------------------- o que a equipe faz
def registrar_contato(internacao, quem, resultado, observacao="", retornar_em=None, hoje=None):
    """Anota uma tentativa de contato. Devolve {campo: mensagem}; vazio = deu certo. `quem` é o nome de quem ligou."""
    hoje = hoje or date.today()
    if internacao.status != "lista_espera":
        return {"resultado": "Esta pessoa já não está na lista de espera."}
    if resultado not in RESULTADOS:
        return {"resultado": "Escolha o resultado do contato."}
    if resultado not in COM_RETORNO:
        retornar_em = None                               # aceitou ou desistiu: não há o que ligar de novo (a tela nem oferece o campo)
    elif retornar_em is not None and retornar_em < hoje:
        return {"retornar_em": "O dia para ligar de novo não pode ser antes de hoje."}
    db.session.add(ContatoFila(internacao=internacao, por=quem or "", resultado=resultado, observacao=(observacao or "").strip()[:300], retornar_em=retornar_em))
    internacao.fila_retornar_em = retornar_em
    if resultado == "desistiu":
        internacao.status = "desistiu"                   # sai da fila (modelos._carimbar_a_fila limpa o resto)
    db.session.commit()
    return {}


def mover(internacao, acao):
    """Sobe, desce ou leva ao topo da fila da categoria dela (ACOES_DE_MOVER). Devolve True se a posição mudou."""
    if internacao.status != "lista_espera" or acao not in ACOES_DE_MOVER:
        return False
    fila = [e.internacao for e in na_fila().get(categoria_de(internacao), [])]
    atual = next((n for n, i in enumerate(fila) if i.id == internacao.id), None)
    if atual is None:
        return False
    chaves = [_chave(i)[0] for i in fila]
    UM_MINUTO = 60.0
    if acao == "topo":
        if atual == 0:
            return False
        novo = chaves[0] - UM_MINUTO
    elif acao == "subir":
        if atual == 0:
            return False
        novo = (chaves[atual - 2] + chaves[atual - 1]) / 2 if atual >= 2 else chaves[0] - UM_MINUTO
    else:
        if atual == len(fila) - 1:
            return False
        novo = (chaves[atual + 1] + chaves[atual + 2]) / 2 if atual + 2 < len(fila) else chaves[-1] + UM_MINUTO
    internacao.fila_ordem = novo
    db.session.commit()
    return True
