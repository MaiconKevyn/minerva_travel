"""A identidade visual do guia, num lugar só.

Antes o estilo vivia espalhado: o prompt das paginas em `page_generation`, o
das artes de ponto turistico em `image_generation`, e as cores fixas dentro do
compositor. Mudar a cara do produto exigia caçar as tres, e elas divergiam.

A referencia e o projeto "Inspired Arts Destinations", de Arantxa Larrea, feito
para um acampamento de arte de criancas de 4 a 13 anos. O que caracteriza:
ilustracao chapada com textura de giz de cera, formas gordas sem contorno,
fundo de uma cor so com grao de papel, motivos cortados pela borda, paleta
curta e tipografia slab em caixa alta com entreletra larga.

Uma adaptacao deliberada: a referencia usa fundos SATURADOS nos cartoes de
titulo. Aqui o fundo e sempre CLARO, porque estas paginas sao impressas em casa
e escritas a lapis. Medido: fundo cobalto chapado consome 65% de tinta e some
com o grafite; o mesmo desenho em fundo claro consome 14%. A propria referencia
faz esse corte — os mapas de caderno em que a crianca desenha sao claros.
"""

from pathlib import Path

# --- paleta -----------------------------------------------------------------
# Destilada das nove pranchas da referencia. Os tons fortes entram como MOTIVO,
# nunca como fundo de pagina inteira.
TERRACOTA = "#B4462F"
PETROLEO = "#1F5F5B"
SALVIA = "#7C9A6D"
MOSTARDA = "#E0A32E"
ROSA = "#E38BA0"
COBALTO = "#2E5FA3"
CREME = "#F4EFE4"
PAPEL = "#FBF8F1"
TINTA = "#2A2118"
SOMBRA = "#8A7B63"

PALETA_PROSA = (
    "terracotta red, deep petrol teal, sage green, mustard yellow, dusty rose and cobalt blue"
)

# --- tipografia -------------------------------------------------------------
_FONTES = Path(__file__).parent / "assets" / "fonts"
FONTE_REGULAR = _FONTES / "ZillaSlab-Regular.ttf"
FONTE_SEMIBOLD = _FONTES / "ZillaSlab-SemiBold.ttf"
FONTE_BOLD = _FONTES / "ZillaSlab-Bold.ttf"

# --- estilo das ilustracoes -------------------------------------------------
# Prosa curta de proposito: prompt longo dilui, e o modelo passa a ignorar o
# fim. Cada frase aqui corresponde a algo visivel na referencia.
ILLUSTRATION_STYLE = (
    "HOUSE STYLE — flat modern children's editorial illustration, drawn digitally with a dry "
    "textured crayon and chalk brush so every shape shows a visible grainy pencil tooth. The "
    "page sits on ONE flat PALE background — soft cream, pale sky blue, pale mint or pale "
    "blush — with a subtle paper grain. Pale is a hard requirement: these pages are printed at "
    "home and written on in pencil. Motifs are simple, chunky and friendly, built from solid "
    "colour shapes with no outline stroke and almost no internal detail; a few are generously "
    "cropped by the page edge so the scene feels larger than the sheet. Strictly limited "
    f"palette: the pale ground plus at most four strong accents from {PALETA_PROSA}. No "
    "gradients, no vignette, no border frame, no ornamental rules, no postmark, no drop "
    "shadows, no white boxes behind anything. Nothing photographic, nothing watercolour, "
    "nothing vintage or Victorian, no neon, no 3D shading, no glossy highlights."
)

# Traco puro. Colorir e ligue-os-pontos precisam de contorno fechado, o que o
# estilo chapado nao da — a crianca pinta dentro da linha.
LINEART_STYLE = (
    "HOUSE STYLE — pure black line art on plain white, drawn with the same confident, chunky "
    "children's hand as the rest of the book: bold even outlines, generous closed shapes, no "
    "shading, no texture, no colour. Absolutely no border frame, no corner ornament, no "
    "postmark and no background wash — the sheet outside the drawing stays pure white."
)

# Como os motivos se arrumam na folha. Vale para toda pagina que recebe painel
# impresso por cima.
COMPOSITION_RULE = (
    "COMPOSITION — keep the central area of the page calm and empty; push the illustrated "
    "motifs to the corners and the outer edges so they frame that emptiness."
)
