# Lista de espera

Pedido do usuário em 2026-11-16: "melhorar a lista de espera pra saber quando entrar em contato se liberar vaga: ordem de chamada, e tudo mais". Antes, a lista de espera era só uma
**situação** da triagem: sem data de entrada, sem posição e sem registro de contato. Agora é uma tela própria (`/fila`, `fila.py`).

Decisões do usuário (2026-11-16): ordem de **chegada, por categoria, com ajuste manual**; **histórico de contatos + dia para ligar de novo**; aviso de vaga no **sino e no quadro de vagas** da página inicial.

## Como funciona

- **Entra na fila** quem está com a situação *Lista de espera* na triagem (Triagens, na coluna *Situação*). O sistema carimba sozinho o momento da entrada (`Internacao.fila_desde`): é a **ordem de
  chegada**. Voltar a *Em admissão* e depois à lista de espera **não perde o lugar**; sair de vez (admitido, desistência, rejeitado) apaga o carimbo, a posição manual e o dia de ligar de novo.
  Quem já estava na lista antes desta mudança entra com a data do 1º contato (ou a do cadastro).
- **Uma fila por categoria**, porque a vaga é por categoria (uma vaga de Caps AD não serve a um particular). A categoria é a do convênio (`prontuario.categoria_vaga`). Quem está com o convênio
  *a definir* fica no grupo **Sem categoria definida**: conta na espera, mas não é chamado até alguém definir o convênio (*Editar a triagem*).
- **Ajuste manual**: no menu **⋯** de cada linha, *Levar para o topo*, *Subir* e *Descer* (só quem registra triagens). A posição manual (`fila_ordem`) é um número na mesma escala do carimbo,
  então quem nunca foi mexido segue a chegada.
- **Quem chamar** = as vagas livres da categoria (`vagas.py`) **menos as que já têm dono**. Têm dono quem **aceitou a vaga** ou já tem a **internação marcada** (hoje ou depois), esteja na fila
  ou em admissão. Quem **pediu para ligar mais tarde** (o dia combinado ainda não chegou) mantém a posição, mas é **pulado** na hora de chamar. As linhas a chamar ficam em verde, "Chamar agora".
  Categoria sem limite de vagas definido não chama ninguém.
- **Contatos** (`ContatoFila`, só se acrescenta): *Registrar contato* abre uma janela com o resultado — **Não atendeu**, **Pediu para ligar mais tarde**, **Aceitou a vaga**, **Não pode agora (segue na
  fila)** ou **Desistiu (sai da fila)** — uma observação (até 300 caracteres) e, em *Não atendeu*, *Pediu para ligar mais tarde* e *Não pode agora*, o **dia para ligar de novo**. Fica gravado quem ligou, quando e o resultado; a linha mostra o
  último contato e *Todos os contatos* mostra o histórico. *Desistiu* muda a triagem para Desistência (sai da fila). *Aceitou* não muda a situação: a pessoa fica na fila, marcada como chamada, com o botão
  **Internar** (abre o prontuário a partir da triagem) até ser admitida.
- **Telefones** são os do cadastro (família/responsável, outro e do próprio), como links `tel:`.

## Onde aparece

- **Lista de espera** (`/fila`): abas *Triagens | Lista de espera (n)* no alto das duas telas. A *Triagens* perdeu o botão de filtro *Lista de espera* (repetia esta tela); o endereço antigo
  `/triagens?situacao=lista_espera` leva a ela. No celular as abas e o filtro de Triagens ganham o botão ⌄ que lista o que não cabe.
- **Página inicial**: o número *Lista de espera* leva à tela; no quadro de **Vagas por categoria**, a categoria com vaga a preencher mostra *Chamar agora, na ordem da lista de espera* com os nomes e o
  telefone (até 3), e as demais mostram quantos esperam. O quadro de avisos cobra **Lista de espera: ligar de novo** quando o dia combinado chega (some quando o contato é registrado).
- **Sino**: depois de uma **baixa**, se a categoria dela ficou com vaga a preencher e há alguém esperando, quem registra triagens (Escritório e administrador, menos quem deu a baixa) recebe
  *Vaga aberta: chamar fulano (2º da fila)*, que leva à lista de espera. Não repete enquanto a anterior não foi lida.

## Quem faz o quê

- **Ver a lista**: todo mundo que entrou (permissão `ver`); quem só consulta não vê os botões.
- **Registrar contato e reordenar**: a permissão `triagem` (polo Escritório e administrador).
- **Internar**: quem tem `internacao`.
- A trilha de auditoria guarda *abriu a lista de espera*, *registrou contato* (só o resultado) e *mudou a posição*; **nunca** o texto da observação.

## Para o administrador

Sem passo manual: as colunas novas (`fila_desde`, `fila_ordem`, `fila_retornar_em`) e a tabela `contatos_fila` se criam sozinhas na subida (`migracoes.py`, passo 6i).
