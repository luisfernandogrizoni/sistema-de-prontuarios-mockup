// A caixa "para imprimir" e o preview das folhas ao lado (padrões de interface). Serve à aba Imprimir da ficha e à página de Relatórios.
//
// A página marca a área com [data-impressos] (data-ver: o endereço das folhas; data-docx: o do arquivo Word) e põe dentro:
//   input[data-chave]            uma caixinha por documento (o que está marcado entra no preview, em "Imprimir os escolhidos" e em "Baixar Word")
//   [data-marcar-todos]          o botão "Selecionar tudo" / "Desmarcar tudo"
//   [data-selecao]               a barra de baixo: [data-contagem], [data-imprimir-escolhidos] e [data-baixar]
//   iframe + [data-sem-preview]  o preview (data-src: o que carregar quando a aba abrir) e o aviso de "nada marcado"
//   [data-so-este="chave"]       "Imprimir só este" (marca só ele e imprime); [data-docx-item="chave"]: "Baixar Word" só dele
//   [data-mostrar-com="a,b"]     só aparece enquanto um desses documentos está marcado (ex.: quem assina a declaração)
// As escolhas que vão junto ao endereço (quem assina, anonimizar, colunas...) são controles com:
//   [data-param="nome"]          <select> (vale o valor) ou caixinha única (data-valor se marcada; data-valor-desmarcado se desmarcada)
//   [data-param-grupo="nome"]    um grupo de caixinhas: vale cada uma marcada (repetida), ou juntas com data-juntar=","; com data-padrao="a,b" a escolha
//                                igual ao padrão não é pedida e nenhuma marcada pede "nenhum"; [data-restaurar] dentro do grupo volta ao padrão
//   [data-marca-grupo]           caixinha "todos" de um <fieldset> de caixinhas (os meses de um ano)
// data-sincronizar na área: o endereço da página acompanha a escolha (recarregar a página mantém); data-imprimir-ao-abrir: manda imprimir ao abrir;
// data-carregar-ja: o preview carrega assim que a página abre (na ficha ele espera a aba Imprimir abrir).
(function () {
  function todos(seletor, raiz) { return Array.prototype.slice.call((raiz || document).querySelectorAll(seletor)); }

  todos("[data-impressos]").forEach(function (area) {
    var marcas = todos("input[data-chave]", area), barra = area.querySelector("[data-selecao]"), quadro = area.querySelector("iframe"), vazio = area.querySelector("[data-sem-preview]");
    var todosBotao = area.querySelector("[data-marcar-todos]");
    var sincronizar = area.hasAttribute("data-sincronizar");
    var espera = null;

    var chaves = function () { return marcas.filter(function (m) { return m.checked; }).map(function (m) { return m.getAttribute("data-chave"); }); };
    // o que as escolhas acrescentam ao endereço: "&emissor=3&nomes=completos&colunas=caps-ad..." (vazio se nada)
    var extras = function () {
      var partes = [];
      var pedir = function (nome, valor) { partes.push(encodeURIComponent(nome) + "=" + encodeURIComponent(valor)); };
      todos("[data-param]", area).forEach(function (c) {
        if (c.closest("[hidden]")) return;
        var nome = c.getAttribute("data-param");
        if (c.type === "checkbox") {
          if (c.checked && c.hasAttribute("data-valor")) pedir(nome, c.getAttribute("data-valor"));
          else if (!c.checked && c.hasAttribute("data-valor-desmarcado")) pedir(nome, c.getAttribute("data-valor-desmarcado"));
        } else if (c.value) pedir(nome, c.value);
      });
      todos("[data-param-grupo]", area).forEach(function (g) {
        if (g.closest("[hidden]")) return;
        var nome = g.getAttribute("data-param-grupo");
        var marcadas = todos("input[type=checkbox]", g).filter(function (c) { return c.checked && !c.disabled && !c.hasAttribute("data-marca-grupo"); }).map(function (c) { return c.value; });
        var padrao = g.getAttribute("data-padrao");
        if (padrao !== null) {
          if (marcadas.slice().sort().join(",") === padrao.split(",").filter(Boolean).sort().join(",")) return;      // o padrão do relatório: não precisa pedir
          if (!marcadas.length) { pedir(nome, "nenhum"); return; }
        }
        if (g.hasAttribute("data-juntar")) { if (marcadas.length) pedir(nome, marcadas.join(g.getAttribute("data-juntar"))); }
        else marcadas.forEach(function (v) { pedir(nome, v); });
      });
      return partes.length ? "&" + partes.join("&") : "";
    };

    // imprimir = recarregar o preview com ?imprimir=1: a página das folhas manda imprimir ao abrir (só assim o impresso conta como impresso, na auditoria e na triagem); o "n" garante a recarga
    area.imprimirEscolhidos = function () {
      var lista = chaves().join(",");
      if (!quadro || !lista) return;
      quadro.hidden = false;
      quadro.setAttribute("src", area.getAttribute("data-ver") + "?itens=" + lista + extras() + "&embutido=1&imprimir=1&n=" + Date.now());
    };

    var atualizar = function () {
      var itens = chaves(), lista = itens.join(",");
      todos("[data-mostrar-com]", area).forEach(function (el) {                // (antes de montar o endereço: o que está escondido não conta)
        el.hidden = !el.getAttribute("data-mostrar-com").split(",").some(function (c) { return itens.indexOf(c) >= 0; });
      });
      var pedido = extras();
      if (todosBotao) {
        var tudo = itens.length === marcas.length;
        todosBotao.textContent = tudo ? "Desmarcar tudo" : "Selecionar tudo";
        todosBotao.setAttribute("aria-pressed", tudo ? "true" : "false");
      }
      if (barra) {
        barra.hidden = itens.length === 0;
        barra.querySelector("[data-contagem]").textContent = itens.length + (itens.length === 1 ? " escolhido" : " escolhidos");
        barra.querySelector("[data-baixar]").setAttribute("href", area.getAttribute("data-docx") + "?itens=" + lista + pedido);
      }
      todos("[data-docx-item]", area).forEach(function (a) { a.setAttribute("href", area.getAttribute("data-docx") + "?itens=" + a.getAttribute("data-docx-item") + pedido); });
      if (sincronizar) history.replaceState(null, "", location.pathname + "?itens=" + lista + pedido);
      if (quadro) {
        quadro.hidden = itens.length === 0;
        if (vazio) vazio.hidden = itens.length > 0;
        if (itens.length) {
          var url = area.getAttribute("data-ver") + "?itens=" + lista + pedido + "&embutido=1";
          quadro.setAttribute("data-src", url);                              // (se a aba ainda não abriu, ela carrega já com a escolha)
          if (quadro.getAttribute("src") && quadro.getAttribute("src") !== url) { clearTimeout(espera); espera = setTimeout(function () { quadro.setAttribute("src", url); }, 250); }
        }
      }
    };

    marcas.forEach(function (m) { m.addEventListener("change", atualizar); });
    todos("[data-param], [data-param-grupo] input", area).forEach(function (c) { c.addEventListener("change", atualizar); });
    if (todosBotao) todosBotao.addEventListener("click", function () {
      var marcar = !marcas.every(function (m) { return m.checked; });
      marcas.forEach(function (m) { m.checked = marcar; });
      atualizar();
    });
    if (barra) barra.querySelector("[data-imprimir-escolhidos]").addEventListener("click", function () { area.imprimirEscolhidos(); });
    todos("[data-so-este]", area).forEach(function (b) {                       // "Imprimir só este": marca só ele (o preview mostra o que sai) e imprime
      b.addEventListener("click", function () {
        var menu = b.closest("details"); if (menu) menu.open = false;
        marcas.forEach(function (m) { m.checked = m.getAttribute("data-chave") === b.getAttribute("data-so-este"); });
        atualizar();
        area.imprimirEscolhidos();
      });
    });
    todos("[data-restaurar]", area).forEach(function (b) {                     // "Voltar ao padrão" de um grupo de informações
      b.addEventListener("click", function () {
        var g = b.closest("[data-param-grupo]"), padrao = (g.getAttribute("data-padrao") || "").split(",");
        todos("input[type=checkbox]", g).forEach(function (c) { c.checked = padrao.indexOf(c.value) >= 0; });
        atualizar();
      });
    });
    todos("fieldset", area).forEach(function (ano) {                           // a caixinha "todos" de um grupo (os meses de um ano)
      var geral = ano.querySelector("[data-marca-grupo]");
      if (!geral) return;
      var filhas = todos("input[type=checkbox]:not([data-marca-grupo]):not(:disabled)", ano);
      var conferir = function () {
        var n = filhas.filter(function (c) { return c.checked; }).length;
        geral.checked = filhas.length > 0 && n === filhas.length;
        geral.indeterminate = n > 0 && n < filhas.length;
      };
      geral.addEventListener("change", function () { filhas.forEach(function (c) { c.checked = geral.checked; }); conferir(); atualizar(); });
      filhas.forEach(function (c) { c.addEventListener("change", conferir); });
      conferir();
    });

    atualizar();                                                              // (o navegador devolve as caixinhas marcadas ao voltar à página: o preview acompanha)
    if (area.hasAttribute("data-imprimir-ao-abrir")) area.imprimirEscolhidos();
    else if (area.hasAttribute("data-carregar-ja") && quadro && !quadro.hidden && !quadro.getAttribute("src")) quadro.setAttribute("src", quadro.getAttribute("data-src"));       // (na ficha o preview espera a aba abrir)
  });
})();
