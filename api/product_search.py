"""Expansão local e segura de consultas do catálogo salvo.

Não chama serviços externos; a autorização por conta permanece no router.
Termos ficam restritos à gramática segura do filtro OR do PostgREST.
"""

import re
import unicodedata


MAX_SEARCH_LENGTH = 100
MAX_EXPANDED_TERMS = 26

# Agrupamentos explícitos: termos comuns, marcas usadas como sinônimos e contexto.
CAR_WASH = (
    "lavadora de carro", "lava jato", "lava-jato", "lava a jato",
    "lavadora de alta pressao", "lavadora de alta pressão",
    "lavadora de pressao", "lavadora de pressão", "hidrolavadora",
    "lavadora wap", "wap", "vap", "jato de agua", "jato de água",
)
BEDROOM = (
    "quarto", "dormitorio", "dormitório", "cama", "lencol", "lençol",
    "colcha", "travesseiro", "fronha", "edredom", "cobertor",
    "colchao", "colchão", "cabeceira", "guarda roupa", "guarda-roupa",
    "penteadeira", "abajur", "criado mudo", "cortina",
    "roupa de cama", "organizador",
)
KITCHEN = (
    "cozinha", "fogao", "fogão", "cooktop", "panela", "frigideira",
    "air fryer", "fritadeira", "talher", "geladeira", "microondas",
    "micro-ondas", "liquidificador", "batedeira", "cafeteira",
    "organizador",
)
BATHROOM = (
    "banheiro", "lavabo", "chuveiro", "ducha", "box", "vaso sanitario",
    "vaso sanitário", "toalha", "tapete", "saboneteira", "espelho",
    "porta escova",
)
LIVING_ROOM = (
    "sala de estar", "sala", "sofa", "sofá", "rack", "painel tv",
    "mesa de centro", "poltrona", "almofada", "cortina", "tapete",
    "luminaria", "luminária",
)

ROOM_GROUPS = (
    ({"quarto", "quartos", "dormitorio", "dormitorios"}, BEDROOM),
    ({"cozinha", "cozinhas"}, KITCHEN),
    ({"banheiro", "banheiros", "lavabo"}, BATHROOM),
    ({"sala", "salas", "living"}, LIVING_ROOM),
)


def _safe_text(value: str) -> str:
    # Aspas, parênteses, vírgulas, pontos e curingas da sintaxe PostgREST
    # não podem ser injetados no OR; separadores viram espaços.
    safe = re.sub(r"[^\w\s-]", " ", value[:MAX_SEARCH_LENGTH], flags=re.UNICODE)
    safe = safe.replace("_", " ")
    return re.sub(r"\s+", " ", safe).strip()


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def expand_product_search(raw: str) -> list[str]:
    """Expande semântica prática, preservando primeiro a busca literal."""
    original = _safe_text(raw)
    if not original:
        return []
    folded = _fold(original)
    tokens = set(folded.replace("-", " ").split())
    groups = []
    car_wash_context = (
        bool(tokens & {"wap", "vap", "hidrolavadora"})
        or "lava jato" in folded.replace("-", " ")
        or "lava a jato" in folded.replace("-", " ")
        or "alta pressao" in folded
        or ("lavadora" in tokens and bool(tokens & {"carro", "carros", "veiculo", "veiculos", "pressao"}))
    )
    if car_wash_context:
        groups.append(CAR_WASH)
    for triggers, terms in ROOM_GROUPS:
        if tokens & triggers:
            groups.append(terms)
    out = []
    seen = set()
    for term in (original, *(term for group in groups for term in group)):
        safe_term = _safe_text(term)
        normalized = _fold(safe_term)
        if safe_term and normalized not in seen:
            seen.add(normalized)
            out.append(safe_term)
        if len(out) >= MAX_EXPANDED_TERMS:
            break
    return out


def product_search_filter(raw: str) -> str | None:
    """Filtro OR PostgREST só em nome e categoria, sem cláusulas injetáveis."""
    terms = expand_product_search(raw)
    if not terms:
        return None
    clauses = []
    for term in terms:
        clauses.append(f"name.ilike.%{term}%")
        clauses.append(f"category.ilike.%{term}%")
    return ",".join(clauses)
