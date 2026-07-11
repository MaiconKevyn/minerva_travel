"""Curiosidades e introducoes infantis por pais/cidade para destinos personalizados."""

from minerva_travel.wikimedia_client import normalize_search_text


class DestinationFacts:
    def __init__(self, intro: list[str], curiosities: list[str]) -> None:
        self.intro = intro
        self.curiosities = curiosities


_FACTS: dict[str, DestinationFacts] = {
    "franca": DestinationFacts(
        intro=[
            "A França é um país famoso pela arte, pelos castelos e pelas comidas gostosas.",
            "É lá que fica Paris, conhecida como a Cidade Luz.",
            "Explorar a França é como entrar em um livro de histórias de verdade.",
        ],
        curiosities=[
            "A Torre Eiffel cresce alguns centímetros no verão, porque o ferro estica com o calor.",
            "Os franceses comem cerca de 30 mil toneladas de croissant por ano.",
            "Na França existem mais de 40 mil castelos espalhados pelo país.",
        ],
    ),
    "italia": DestinationFacts(
        intro=[
            "A Itália tem formato de bota no mapa e é cheia de história antiga.",
            "Foi lá que nasceram a pizza, o gelato e os gladiadores de Roma.",
            "Cada cidade italiana parece um museu a céu aberto.",
        ],
        curiosities=[
            "O Coliseu de Roma tinha espaço para mais de 50 mil pessoas, como um estádio de hoje.",
            "Na Itália se jogam moedas na Fontana di Trevi para dar sorte e voltar um dia.",
            "O gelato italiano é servido com uma pazinha, não com bola como o sorvete.",
        ],
    ),
    "espanha": DestinationFacts(
        intro=[
            "A Espanha é um país alegre, com festas coloridas e praças cheias de vida.",
            "Lá as pessoas falam espanhol e adoram dançar flamenco.",
            "Das praias aos castelos, sempre tem algo novo para descobrir.",
        ],
        curiosities=[
            "A Sagrada Família, em Barcelona, está em construção há mais de 140 anos.",
            "Na Espanha existe uma festa em que as pessoas brincam de guerra de tomates.",
            "O almoço espanhol costuma ser bem tarde, perto das 14h ou 15h.",
        ],
    ),
    "portugal": DestinationFacts(
        intro=[
            "Portugal é o país que fala a mesma língua que a gente!",
            "É a terra dos navegadores que cruzaram os oceanos há muitos séculos.",
            "Lá tem bondinhos amarelos, castelos e o famoso pastel de Belém.",
        ],
        curiosities=[
            "A livraria Lello, no Porto, parece saída de um filme de magia.",
            "Lisboa é conhecida como a cidade das sete colinas, cheia de subidas e descidas.",
            "A receita original do pastel de Belém é segredo há quase 200 anos.",
        ],
    ),
    "inglaterra": DestinationFacts(
        intro=[
            "A Inglaterra é a terra dos ônibus vermelhos de dois andares e do chá da tarde.",
            "Em Londres, guardas com chapéus altos protegem o palácio sem se mexer.",
            "Prepare o guarda-chuva: chuvinha rápida faz parte da aventura.",
        ],
        curiosities=[
            "O Big Ben não é a torre: é o nome do sino gigante que mora dentro dela.",
            "No metrô de Londres, o mais antigo do mundo, as portas avisam: mind the gap!",
            "Os corvos da Torre de Londres são protegidos por uma lenda muito antiga.",
        ],
    ),
    "reino unido": DestinationFacts(
        intro=[
            "O Reino Unido junta Inglaterra, Escócia, País de Gales e Irlanda do Norte.",
            "É a terra dos castelos, dos ônibus vermelhos e das lendas de cavaleiros.",
            "Cada cidade tem uma história diferente para contar.",
        ],
        curiosities=[
            "O Big Ben não é a torre: é o nome do sino gigante que mora dentro dela.",
            "Na Escócia, dizem que um monstro amigável mora no lago Ness.",
            "Os guardas reais treinam para ficar horas sem rir nem se mexer.",
        ],
    ),
    "alemanha": DestinationFacts(
        intro=[
            "A Alemanha é famosa pelos castelos de conto de fadas e florestas encantadas.",
            "Foi lá que os irmãos Grimm escreveram histórias como Branca de Neve.",
            "Trens rápidos ligam cidades cheias de praças e mercados.",
        ],
        curiosities=[
            "O castelo de Neuschwanstein inspirou o castelo da Cinderela.",
            "Na Alemanha existem mais de 1.500 tipos diferentes de salsicha.",
            "As crianças alemãs ganham um cone gigante de doces no primeiro dia de aula.",
        ],
    ),
    "grecia": DestinationFacts(
        intro=[
            "A Grécia é a terra dos deuses da mitologia e dos templos antigos.",
            "Suas ilhas têm casinhas brancas com telhados azuis de frente para o mar.",
            "Muitas histórias de heróis que você conhece nasceram aqui.",
        ],
        curiosities=[
            "As Olimpíadas foram inventadas na Grécia há quase 3 mil anos.",
            "O Partenon, em Atenas, tem mais de 2.400 anos e ainda está de pé.",
            "Na Grécia, quebrar pratos em festas é sinal de alegria.",
        ],
    ),
    "estados unidos": DestinationFacts(
        intro=[
            "Os Estados Unidos são gigantes: têm desertos, montanhas, praias e cidades enormes.",
            "É a terra dos parques incríveis e dos arranha-céus que tocam as nuvens.",
            "Cada estado parece um país diferente para explorar.",
        ],
        curiosities=[
            "A Estátua da Liberdade foi um presente da França e chegou em 350 pedaços.",
            "O Grand Canyon é tão grande que dá para ver do espaço.",
            "Em Nova York, o metrô funciona 24 horas por dia, todos os dias.",
        ],
    ),
    "japao": DestinationFacts(
        intro=[
            "O Japão mistura templos antigos com robôs e trens super velozes.",
            "Na primavera, as cerejeiras cobrem as cidades de flores cor-de-rosa.",
            "É um país onde tradição e futuro andam juntos.",
        ],
        curiosities=[
            "Os trens-bala japoneses chegam a 320 km/h e quase nunca atrasam.",
            "No Japão existe uma ilha onde os coelhos mandam: a Ilha dos Coelhos.",
            "Tirar os sapatos antes de entrar em casa é regra importante por lá.",
        ],
    ),
    "brasil": DestinationFacts(
        intro=[
            "O Brasil é o nosso gigante: tem floresta, praia, cachoeira e muita alegria.",
            "É a terra do futebol, do açaí e de bichos que só existem aqui.",
            "Cada região tem comidas, músicas e festas diferentes.",
        ],
        curiosities=[
            "A Amazônia é a maior floresta tropical do mundo.",
            "O Cristo Redentor foi eleito uma das sete maravilhas do mundo moderno.",
            "O Brasil é o único país da América do Sul que fala português.",
        ],
    ),
    "argentina": DestinationFacts(
        intro=[
            "A Argentina é vizinha do Brasil e famosa pelo tango e pelas montanhas geladas.",
            "Em Buenos Aires, as calçadas coloridas do Caminito parecem pintura.",
            "Do deserto às geleiras, é um país de paisagens surpreendentes.",
        ],
        curiosities=[
            "A Patagônia argentina tem geleiras azuis gigantes que estalam e desabam no lago.",
            "O tango nasceu nas ruas de Buenos Aires.",
            "As Cataratas do Iguaçu ficam na divisa entre Argentina e Brasil.",
        ],
    ),
}

_CITY_TO_COUNTRY = {
    "paris": "franca",
    "roma": "italia",
    "veneza": "italia",
    "florenca": "italia",
    "milao": "italia",
    "barcelona": "espanha",
    "madri": "espanha",
    "madrid": "espanha",
    "lisboa": "portugal",
    "porto": "portugal",
    "londres": "inglaterra",
    "berlim": "alemanha",
    "munique": "alemanha",
    "atenas": "grecia",
    "nova york": "estados unidos",
    "nova iorque": "estados unidos",
    "orlando": "estados unidos",
    "toquio": "japao",
    "buenos aires": "argentina",
    "france": "franca",
    "italy": "italia",
    "spain": "espanha",
    "england": "inglaterra",
    "london": "inglaterra",
    "germany": "alemanha",
    "greece": "grecia",
    "japan": "japao",
    "new york": "estados unidos",
    "tokyo": "japao",
}


def lookup_destination_facts(*names: str) -> DestinationFacts | None:
    """Procura curiosidades pelo pais ou pela cidade (o usuario pode digitar qualquer um)."""
    for name in names:
        normalized = normalize_search_text(name or "")
        if not normalized:
            continue
        if normalized in _FACTS:
            return _FACTS[normalized]
        country_key = _CITY_TO_COUNTRY.get(normalized)
        if country_key:
            return _FACTS.get(country_key)
    return None
