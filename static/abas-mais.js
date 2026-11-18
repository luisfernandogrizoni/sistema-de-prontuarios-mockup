// Barras de abas que não cabem na tela (as abas da ficha, as de Cadastros, as da ficha de saúde...).
//
// Numa tela estreita a barra rola de lado e o que não cabe simplesmente some: ninguém sabe que há mais abas. Aqui, sempre que a barra transborda, aparece um botão (⌄) na ponta
// direita dela; ele abre a lista de TODAS as abas (a atual marcada) e escolher uma é o mesmo que clicar nela. Cabendo tudo, o botão não existe. A aba atual também vem para a vista.
//
// Como usar: ponha `data-mais-abas` na barra que rola (um <nav>, ou o <div class="segmentado"> de links ou botões). O script a envolve num <div class="rolavel-mais"> (ou usa o que a
// página já escreveu, quando a barra precisa de um pai próprio, como a das abas da ficha, que gruda no alto) e acrescenta o botão. A aba atual é a que tem aria-current="true",
// aria-pressed="true" ou a classe `ativo`. Estilos em templates/base.html (.rolavel-mais, .mais-abas, .mais-abas-lista).
(function () {
  "use strict";

  var barras = [];
  var lista = null;           // o menu aberto (um só na página)
  var dona = null;            // a barra a que ele pertence

  function itensDe(rol) {
    return Array.prototype.filter.call(rol.children, function (x) { return x.tagName === "A" || x.tagName === "BUTTON"; });
  }
  function eAtual(item) {
    return item.getAttribute("aria-current") === "true" || item.getAttribute("aria-pressed") === "true" || item.classList.contains("ativo");
  }

  // a aba fica à vista na barra (fora da área coberta pelo botão, na ponta direita)
  function trazer(b, item) {
    var rol = b.rol.getBoundingClientRect(), r = item.getBoundingClientRect();
    var folga = 16, botao = b.botao.hidden ? 0 : b.botao.offsetWidth;
    if (r.left < rol.left + folga) b.rol.scrollLeft += r.left - rol.left - folga;
    else if (r.right > rol.right - botao - folga) b.rol.scrollLeft += r.right - rol.right + botao + folga;
  }

  // cabem todas as abas na largura da barra? As abas são medidas uma em relação à outra (não pelo scrollWidth, que muda com o espaço que o botão reserva)
  function medir(b) {
    var itens = itensDe(b.rol);
    var precisa = false;
    if (itens.length > 1 && b.rol.clientWidth > 0) {
      var estilo = getComputedStyle(b.rol);
      var conteudo = itens[itens.length - 1].getBoundingClientRect().right - itens[0].getBoundingClientRect().left + parseFloat(estilo.paddingLeft) + parseFloat(estilo.paddingRight);
      precisa = conteudo > b.rol.clientWidth + 1;
    }
    if (b.botao.hidden === !precisa) return;
    b.botao.hidden = !precisa;
    b.env.classList.toggle("transborda", precisa);
    if (!precisa) fechar();
  }

  function fechar() {
    if (!lista) return;
    lista.remove();
    dona.botao.setAttribute("aria-expanded", "false");
    lista = dona = null;
  }

  function abrir(b) {
    fechar();
    dona = b;
    lista = document.createElement("div");
    lista.className = "mais-abas-lista";
    lista.setAttribute("role", "menu");
    lista.setAttribute("aria-label", "Todas as abas");
    itensDe(b.rol).forEach(function (item) {
      var x = document.createElement("button");
      x.type = "button";
      x.className = "item-aba";
      x.setAttribute("role", "menuitem");
      Array.prototype.forEach.call(item.childNodes, function (no) { x.appendChild(no.cloneNode(true)); });       // o ícone, o texto e a contagem da aba, como estão nela
      if (eAtual(item)) {
        x.setAttribute("aria-current", "true");
        var marca = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        marca.setAttribute("class", "icone marca");
        marca.setAttribute("aria-hidden", "true");
        marca.innerHTML = '<use href="#i-ok"/>';
        x.appendChild(marca);
      }
      x.addEventListener("click", function () {
        fechar();
        item.click();                                       // escolher aqui é clicar na aba (um link vai para a página, um botão aplica o filtro)
        window.requestAnimationFrame(function () { trazer(b, item); });
        b.botao.focus({ preventScroll: true });
      });
      lista.appendChild(x);
    });
    document.body.appendChild(lista);
    // embaixo do botão; se não cabe embaixo, em cima dele; se não cabe em nenhum, ocupa o espaço que houver e rola por dentro
    var r = b.botao.getBoundingClientRect(), alto = lista.offsetHeight, tela = window.innerHeight, margem = 8;
    var top = r.bottom + 6;
    if (top + alto > tela - margem) {
      if (r.top - 6 - alto >= margem) top = r.top - 6 - alto;
      else if (r.top - 6 > tela - r.bottom - 6) { top = margem; lista.style.maxHeight = Math.max(120, r.top - 6 - margem) + "px"; }
      else lista.style.maxHeight = Math.max(120, tela - top - margem) + "px";
    }
    lista.style.top = Math.round(top) + "px";
    lista.style.right = Math.max(8, document.documentElement.clientWidth - Math.round(r.right)) + "px";
    b.botao.setAttribute("aria-expanded", "true");
    var primeiro = lista.querySelector('[aria-current="true"]') || lista.firstElementChild;
    if (primeiro) primeiro.focus({ preventScroll: true });
  }

  function preparar(rol) {
    var env = rol.parentNode;
    if (!env.classList.contains("rolavel-mais")) {
      env = document.createElement("div");
      env.className = "rolavel-mais";
      rol.parentNode.insertBefore(env, rol);
      env.appendChild(rol);
    }
    rol.classList.add("rolavel");
    var botao = document.createElement("button");
    botao.type = "button";
    botao.className = "mais-abas";
    botao.hidden = true;
    botao.title = "Ver todas as abas";
    botao.setAttribute("aria-label", "Ver todas as abas");
    botao.setAttribute("aria-haspopup", "menu");
    botao.setAttribute("aria-expanded", "false");
    botao.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-chevron"/></svg>';
    env.appendChild(botao);

    var b = { rol: rol, env: env, botao: botao };
    barras.push(b);
    botao.addEventListener("click", function () { if (lista && dona === b) fechar(); else abrir(b); });
    if ("ResizeObserver" in window) {
      var olho = new ResizeObserver(function () { medir(b); });
      olho.observe(rol);
      itensDe(rol).forEach(function (item) { olho.observe(item); });
    }
    medir(b);
    var atual = itensDe(rol).filter(eAtual)[0];
    if (atual) window.requestAnimationFrame(function () { medir(b); trazer(b, atual); });
  }

  function iniciar() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-mais-abas]"), preparar);
    if (!barras.length) return;
    window.addEventListener("resize", function () { barras.forEach(medir); });
    window.addEventListener("scroll", fechar, { passive: true });
    document.addEventListener("pointerdown", function (e) {
      if (lista && !lista.contains(e.target) && !dona.botao.contains(e.target)) fechar();
    });
    document.addEventListener("keydown", function (e) {
      if (!lista) return;
      var itens = Array.prototype.slice.call(lista.children), i = itens.indexOf(document.activeElement);
      if (e.key === "Escape") { var b = dona; fechar(); b.botao.focus({ preventScroll: true }); }
      else if (e.key === "ArrowDown") { e.preventDefault(); itens[(i + 1) % itens.length].focus({ preventScroll: true }); }
      else if (e.key === "ArrowUp") { e.preventDefault(); itens[(i - 1 + itens.length) % itens.length].focus({ preventScroll: true }); }
      else if (e.key === "Home") { e.preventDefault(); itens[0].focus({ preventScroll: true }); }
      else if (e.key === "End") { e.preventDefault(); itens[itens.length - 1].focus({ preventScroll: true }); }
      else if (e.key === "Tab") fechar();
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
