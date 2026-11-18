"""
Desenha a marca do pacote GENÉRICO (logo das telas, ícones do navegador e logos do timbre dos documentos).

Só para refazer a arte: o sistema não roda este arquivo. Precisa do Pillow (`pip install pillow`) e escreve em marca/ e timbre/ ao lado dele.
Para outra instituição, o caminho certo é um pacote de identidade com as próprias imagens (veja identidade.py e docs/identidade.md), não
mexer aqui.

    python identidades/generica/gerar_marca.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent
CASA = (31, 95, 122)            # azul-petróleo
CORACAO = (255, 255, 255)
TEXTO = (24, 32, 40)
SUPER = 4                       # desenha em tamanho 4x e reduz: bordas lisas

FONTES = {
    "negrito": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "normal": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"],
}


def fonte(estilo, tamanho):
    for nome in FONTES[estilo]:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def emblema(lado):
    """A casa com um coração dentro, em `lado` pixels de lado, com fundo transparente."""
    g = lado * SUPER
    img = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pontos = [(0.50, 0.04), (0.97, 0.47), (0.84, 0.47), (0.84, 0.95), (0.16, 0.95), (0.16, 0.47), (0.03, 0.47)]
    d.polygon([(x * g, y * g) for x, y in pontos], fill=CASA)
    centro_x, centro_y, escala = 0.50 * g, 0.625 * g, 0.0155 * g           # o coração (curva clássica), centrado na parte de baixo da casa
    coracao = []
    for passo in range(361):
        t = math.radians(passo)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        coracao.append((centro_x + x * escala, centro_y - y * escala))
    d.polygon(coracao, fill=CORACAO)
    return img.resize((lado, lado), Image.LANCZOS)


def sobre_branco(imagem):
    fundo = Image.new("RGB", imagem.size, (255, 255, 255))
    fundo.paste(imagem, mask=imagem.split()[3])
    return fundo


def centralizado(d, texto, fonte_, y, largura, cor=TEXTO, espaco=0):
    """Escreve `texto` centralizado; `espaco` abre as letras (em pixels)."""
    if espaco:
        total = sum(d.textlength(c, font=fonte_) + espaco for c in texto) - espaco
        x = (largura - total) / 2
        for c in texto:
            d.text((x, y), c, font=fonte_, fill=cor)
            x += d.textlength(c, font=fonte_) + espaco
    else:
        d.text(((largura - d.textlength(texto, font=fonte_)) / 2, y), texto, font=fonte_, fill=cor)


def logo_do_topo():
    """494 x 472, como o timbre de cima dos documentos espera."""
    largura, altura = 494, 472
    img = Image.new("RGB", (largura, altura), (255, 255, 255))
    d = ImageDraw.Draw(img)
    marca = sobre_branco(emblema(300))
    img.paste(marca, ((largura - 300) // 2, 14))
    centralizado(d, "Comunidade Terapêutica", fonte("normal", 29), 322, largura)
    d.line([(100, 370), (largura - 100, 370)], fill=TEXTO, width=2)
    centralizado(d, "CASA EXEMPLO", fonte("negrito", 56), 390, largura)
    return img


def logo_do_rodape():
    """1080 x 1080, o timbre de baixo dos documentos."""
    lado = 1080
    img = Image.new("RGB", (lado, lado), (255, 255, 255))
    d = ImageDraw.Draw(img)
    img.paste(sobre_branco(emblema(640)), ((lado - 640) // 2, 70))
    centralizado(d, "COMUNIDADE", fonte("negrito", 46), 770, lado, espaco=46)
    centralizado(d, "EXEMPLO", fonte("negrito", 150), 850, lado)
    return img


def main():
    (AQUI / "marca").mkdir(exist_ok=True)
    (AQUI / "timbre").mkdir(exist_ok=True)
    grande = emblema(512)
    grande.resize((256, 256), Image.LANCZOS).save(AQUI / "marca" / "logo.png", optimize=True)
    for lado in (32, 48):
        grande.resize((lado, lado), Image.LANCZOS).save(AQUI / "marca" / f"favicon-{lado}.png", optimize=True)
    icone = Image.new("RGB", (180, 180), (255, 255, 255))
    miolo = emblema(148)
    icone.paste(miolo, (16, 16), miolo)
    icone.save(AQUI / "marca" / "apple-touch-icon.png", optimize=True)
    grande.resize((64, 64), Image.LANCZOS).save(AQUI / "marca" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    logo_do_topo().save(AQUI / "timbre" / "logo-topo.jpg", quality=92, optimize=True)
    logo_do_rodape().save(AQUI / "timbre" / "logo-rodape.jpg", quality=90, optimize=True)
    print("marca e timbre desenhados em", AQUI)


if __name__ == "__main__":
    main()
