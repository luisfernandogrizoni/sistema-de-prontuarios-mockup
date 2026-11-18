# Identidade da instituição

O sistema não tem o nome, a logo, o timbre nem os textos de nenhuma instituição "dentro" do código. Tudo isso vem de um **pacote de
identidade**: uma pasta com os dados e as imagens da instituição (`identidade.py`).

- O pacote **genérico**, a *Casa Exemplo*, vem sempre junto do código, em `identidades/generica/`. É o que aparece quando não há outro.
- O pacote de **uma instituição** é outra pasta de `identidades/` (por exemplo `identidades/minha-casa/`) ou fica só no servidor, em `instance/identidade/`
  (`instance/` nunca vai para o Git).

## O que tem num pacote

```
identidade.json     os dados e os textos (abaixo)
manual.json         o Manual de Orientação que a família recebe (capa e texto)
marca/              logo.png, favicon.ico, favicon-32.png, favicon-48.png, apple-touch-icon.png      (telas)
timbre/             logo-topo.jpg, logo-rodape.jpg                                                  (documentos)
```

`identidade.json`:

| Chave | Para que serve |
|---|---|
| `nome`, `apelido`, `nome_formal`, `sistema`, `mantenedora`, `cidade` | o nome nas telas, nos títulos, nos e-mails e dentro dos documentos ("a Comunidade Terapêutica ... recebeu"); a cidade vai no fecho das declarações |
| `lema`, `endereco_curto` | a capa da ficha de enfermagem |
| `emissor` | quem assina por padrão (nome e cargo), e o primeiro funcionário que o sistema cria numa instalação nova |
| `cabecalho`, `rodape` | o timbre dos documentos: cada linha é uma lista de `[texto, estilo]` (estilos: `b` negrito, `vermelho`, `link`, `serifa`) |
| `declaracao_apresentacao` | a frase que apresenta a entidade na declaração (CNPJ, escritório...) |
| `email` | exemplos que aparecem nas telas e nos comandos, e os padrões do envio de e-mail (`caixa_padrao`, `avisos_padrao`, servidor, porta, segurança) |
| `convenios` | os convênios com que o cadastro nasce numa instalação nova: `[nome, nome na tela, endereço, gratuito, vagas, cor]` |
| `convenio_apelidos` | como a lista de importação chama cada convênio |
| `palavras_fracas` | palavras da instituição que não valem como senha (o nome e a cidade já entram sozinhos) |
| `cores_antigas` | cores de convênio que mudaram de nome: `{"antiga": "nova"}` (a migração troca no banco) |
| `textos` | os trechos dos documentos que falam em nome da instituição (o contrato, o termo, o compromisso, a declaração de próprio punho), com `{interno}` e `{casa}` onde o sistema preenche |

O manual (`manual.json`) é uma lista de `["tipo", "texto"]`, e o texto pode usar `{nome}`, `{apelido}`, `{nome_maiusculo}`, `{cidade}` e
`{mantenedora}`. Os tipos estão explicados em `manual_de_orientacao.py`.

## Qual pacote vale

1. a pasta da variável de ambiente `IDENTIDADE_PASTA` (para testes);
2. o pacote `identidades/<nome>/` indicado pela variável `IDENTIDADE` (`IDENTIDADE=generica` força o genérico, bom para tirar capturas de tela);
3. a pasta `instance/identidade/`;
4. o único pacote de instituição que existir em `identidades/` além do genérico (se houver mais de um, o sistema pede para escolher com `IDENTIDADE`);
5. o pacote genérico.

Um pacote pode ser **parcial**: o que ele não traz (arquivo ou chave) vem do genérico. Se faltar alguma chave de texto ou o manual, o sistema
avisa no registro de erros ao subir e, no servidor real, no quadro de avisos do administrador: o texto genérico não pode aparecer num
documento da instituição sem ninguém notar. O mesmo aviso aparece se o servidor estiver rodando só com o genérico.

As imagens do pacote saem em `/static/identidade/...` (sem login, porque a tela de entrada também mostra a logo) e os documentos em Word leem
os mesmos arquivos em disco.

## Fazer o pacote de uma instituição

Copie `identidades/generica/` para uma pasta nova (`identidades/<nome>/`), troque as imagens (`marca/` e `timbre/`), edite `identidade.json` e
`manual.json` e reinicie o sistema. Para ver o resultado sem mexer na configuração, ligue o sistema com `IDENTIDADE=<nome>`.

`identidades/generica/gerar_marca.py` redesenha a arte do pacote genérico (precisa do Pillow); serve de exemplo do tamanho de cada imagem.

## Para quem mexe no código

- Nada de nome, endereço, CNPJ, telefone ou texto próprio de uma instituição no código nem nos templates: use `identidade.atual()` em Python e a
  variável `identidade` nos templates (`{{ identidade.nome }}`, `{{ identidade.url('marca/logo.png') }}`).
- `verificar_vazamento.py` (o gancho de `git commit`) barra trechos que identificam a instituição fora do pacote dela, lidos do próprio pacote.
