"""Normalização de texto, stemmer leve de português e decodificação de códigos.

Tudo aqui é determinístico e sem dependências externas. O mesmo processamento é
aplicado ao indexar os PDFs e ao montar a consulta, então a "qualidade
linguística" do stemmer importa menos do que a sua **consistência**.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------- códigos
# EI03EO01 · EF05MA03 · EF69LP01 · EM13MAT102 · EM13LP02 · EMIFCG01
CODE_RE = re.compile(
    r"\b(?:E[IFM]\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?|EMIF[A-Z]{2,5}\d{2})\b"
)

EF_COMPONENTS = {
    "LP": "Língua Portuguesa",
    "AR": "Arte",
    "EF": "Educação Física",
    "MA": "Matemática",
    "CI": "Ciências",
    "GE": "Geografia",
    "HI": "História",
    "ER": "Ensino Religioso",
    "LI": "Língua Inglesa",
}
EM_AREAS = {
    "LGG": "Linguagens e suas Tecnologias",
    "LP": "Língua Portuguesa",
    "MAT": "Matemática e suas Tecnologias",
    "CNT": "Ciências da Natureza e suas Tecnologias",
    "CHS": "Ciências Humanas e Sociais Aplicadas",
}
EI_CAMPOS = {
    "EO": "O eu, o outro e o nós",
    "CG": "Corpo, gestos e movimentos",
    "TS": "Traços, sons, cores e formas",
    "EF": "Escuta, fala, pensamento e imaginação",
    "ET": "Espaços, tempos, quantidades, relações e transformações",
}
EI_FAIXAS = {
    "01": "bebês (0 a 1 ano e 6 meses)",
    "02": "crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)",
    "03": "crianças pequenas (4 anos a 5 anos e 11 meses)",
}
EF_YEAR_GROUPS = {
    "12": (1, 2),
    "15": (1, 2, 3, 4, 5),
    "35": (3, 4, 5),
    "67": (6, 7),
    "69": (6, 7, 8, 9),
}

_EF_RE = re.compile(r"^EF(\d{2})([A-Z]{2})\d{2}$")
_EI_RE = re.compile(r"^EI(\d{2})([A-Z]{2})\d{2}$")
_EM_RE = re.compile(r"^EM13([A-Z]{2,4})\d{2,3}[A-Z]?$")
_EMIF_RE = re.compile(r"^EMIF([A-Z]{2,5})\d{2}$")


@dataclass(frozen=True)
class CodeInfo:
    etapa: str
    anos: tuple[int, ...]  # vazio quando não se aplica
    componente: str
    descricao: str  # texto legível, ex.: "Ensino Fundamental · 5º ano · Matemática"


def decode_code(code: str) -> CodeInfo | None:
    """Traduz um código de habilidade em etapa/ano/componente."""
    if m := _EF_RE.match(code):
        digits, comp = m.groups()
        if digits in EF_YEAR_GROUPS:
            anos = EF_YEAR_GROUPS[digits]
            label = _years_label(anos)
        else:
            anos = (int(digits),)
            label = f"{int(digits)}º ano"
        componente = EF_COMPONENTS.get(comp, comp)
        return CodeInfo("Ensino Fundamental", anos, componente,
                        f"Ensino Fundamental · {label} · {componente}")
    if m := _EI_RE.match(code):
        faixa, campo = m.groups()
        campo_nome = EI_CAMPOS.get(campo, campo)
        faixa_nome = EI_FAIXAS.get(faixa, faixa)
        return CodeInfo("Educação Infantil", (), campo_nome,
                        f"Educação Infantil · {faixa_nome} · campo \"{campo_nome}\"")
    if m := _EM_RE.match(code):
        area = EM_AREAS.get(m.group(1), m.group(1))
        return CodeInfo("Ensino Médio", (), area, f"Ensino Médio · {area}")
    if _EMIF_RE.match(code):
        return CodeInfo("Ensino Médio", (), "Itinerários Formativos",
                        "Ensino Médio · Itinerários Formativos")
    return None


def _years_label(anos: tuple[int, ...]) -> str:
    if len(anos) == 2:
        return f"{anos[0]}º e {anos[1]}º anos"
    return f"{anos[0]}º ao {anos[-1]}º ano"


# ---------------------------------------------------------------- normalização
def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


_TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    """
    a o as os um uma uns umas de do da dos das em no na nos nas por para pra com sem sob sobre
    entre ate apos ante e ou mas nem que se como quando onde qual quais quem cujo cuja
    ao aos a as ja nao sim mais menos muito muita muitos muitas pouco pouca bem mal tambem
    so apenas ainda alem todo toda todos todas cada outro outra outros outras mesmo mesma
    eu tu ele ela nos vos eles elas me te lhe lhes meu minha meus minhas seu sua seus suas
    nosso nossa nossos nossas este esta estes estas esse essa esses essas isto isso aquilo
    aquele aquela aqueles aquelas ser sao era foi sera ha tem tinha ter tenho temos estar esta
    estao estou fazer faz fazem fiz pode podem posso poderia podemos deve devem deveria vai
    vao ir vou
    plano planos aula aulas crie criar cria elabore elaborar elabora gere gerar gera faca
    monte montar ajude ajudar ajuda quero queria preciso precisava gostaria favor
    voce vc professor professora turma turmas pedido exemplo
    oi ola tudo bom boa dia tarde noite obrigado obrigada obrigadao valeu ok certo entendi
    legal otimo perfeito claro tchau beleza blz
    seguinte segundo conforme tipo forma modo parte partes
    """.split()
)

# Sufixos derivacionais removidos (do mais longo para o mais curto).
_SUFFIXES = (
    "amentos", "amento", "imentos", "imento", "mente", "acoes", "acao", "icoes", "icao",
    "ucoes", "ucao", "adores", "adoras", "ador", "adora", "antes", "ante", "ancia",
    "encia", "idades", "idade", "ismos", "ismo", "istas", "ista", "avel", "ivel",
    "osos", "osas", "oso", "osa", "ivos", "ivas", "ivo", "iva", "icos", "icas", "ico", "ica",
)


def stem(word: str) -> str:
    """Stemmer leve (plural, sufixos comuns, vogal final). Entrada já normalizada."""
    if len(word) <= 3 or any(c.isdigit() for c in word):
        return word
    w = word
    if w.endswith(("oes", "aes", "aos")):
        w = w[:-3] + "ao"
    elif w.endswith("ais") and len(w) > 4:
        w = w[:-3] + "al"
    elif w.endswith("eis") and len(w) > 5:
        w = w[:-3] + "el"
    elif w.endswith("ois") and len(w) > 5:
        w = w[:-3] + "ol"
    elif w.endswith(("res", "zes", "ses")) and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    for suffix in _SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            w = w[: -len(suffix)]
            break
    if len(w) > 5 and w.endswith(("ar", "er", "ir")):
        w = w[:-2]
    if len(w) > 4 and w[-1] in "aeo":
        w = w[:-1]
    return w


def tokenize(text: str, *, drop_stopwords: bool = False) -> list[str]:
    """Texto -> lista de tokens normalizados (minúsculas, sem acento, com stemming).

    Códigos (``EF05MA03``) contêm dígitos e passam intactos, só em minúsculas.
    """
    # "português/inglês/francês" -> forma feminina, para unificar com "portuguesa" etc.
    # (precisa ser feito antes de remover os acentos).
    plain = strip_accents(re.sub(r"ês\b", "esa", text.lower()))
    tokens = []
    for raw in _TOKEN_RE.findall(plain):
        if drop_stopwords and (raw in STOPWORDS or len(raw) < 2 and not raw.isdigit()):
            continue
        tokens.append(stem(raw))
    return tokens


def index_text(text: str, extra: str = "") -> str:
    """Texto que vai para o índice FTS (tokens já normalizados, separados por espaço)."""
    return " ".join(tokenize(text + " " + extra))
