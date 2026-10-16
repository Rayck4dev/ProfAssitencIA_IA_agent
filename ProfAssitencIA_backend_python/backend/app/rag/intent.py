"""Extrai da pergunta do professor a etapa, o ano e o componente curricular.

Isso vira **prefixos de código de habilidade** (ex.: "5º ano de matemática" →
``ef05ma``), que o BM25 sozinho nunca conseguiria inferir, já que o texto da
pergunta não contém "EF05MA".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.text import EF_YEAR_GROUPS, strip_accents

_ORDINALS = {
    "primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4, "quinto": 5,
    "sexto": 6, "setimo": 7, "oitavo": 8, "nono": 9,
}
_YEAR_NUM_RE = re.compile(r"\b(\d{1,2})\s*(?:o|a|º|°|ª)?\s*(?:ano|serie)\b")
_YEAR_WORD_RE = re.compile(r"\b(" + "|".join(_ORDINALS) + r")\s+(?:ano|serie)\b")
_SERIE_RE = re.compile(r"\b([123])\s*(?:o|a|º|°|ª)?\s*serie\b")

# palavra-chave (sem acento) -> código do componente no Ensino Fundamental
_EF_KEYWORDS = {
    "matematica": "ma", "calculo": "ma", "fracao": "ma", "fracoes": "ma",
    "portugues": "lp", "lingua portuguesa": "lp", "alfabetizacao": "lp",
    "leitura": "lp", "escrita": "lp", "producao de texto": "lp", "redacao": "lp",
    "ciencias": "ci", "historia": "hi", "geografia": "ge",
    "arte": "ar", "artes": "ar", "educacao fisica": "ef",
    "ensino religioso": "er", "ingles": "li", "lingua inglesa": "li",
}
# palavra-chave -> família de código no Ensino Médio
_EM_KEYWORDS = {
    "matematica": "mat", "portugues": "lp", "lingua portuguesa": "lp",
    "linguagens": "lgg", "ingles": "lgg", "arte": "lgg", "artes": "lgg",
    "ciencias da natureza": "cnt", "fisica": "cnt", "quimica": "cnt", "biologia": "cnt",
    "ciencias humanas": "chs", "historia": "chs", "geografia": "chs",
    "sociologia": "chs", "filosofia": "chs",
}
_EI_FAIXAS = {
    "bebe": "01", "bebes": "01", "creche": "01",
    "criancas bem pequenas": "02",
    "criancas pequenas": "03", "pre-escola": "03", "pre escola": "03",
}


@dataclass
class Intent:
    etapa: str | None = None  # "EI" | "EF" | "EM"
    anos: list[int] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)  # prefixos FTS, em minúsculas

    @property
    def found(self) -> bool:
        return bool(self.prefixes)


def parse_intent(question: str) -> Intent:
    text = strip_accents(question).lower()
    intent = Intent()

    years = {int(m) for m in _YEAR_NUM_RE.findall(text) if 1 <= int(m) <= 9}
    years |= {_ORDINALS[w] for w in _YEAR_WORD_RE.findall(text)}
    series = {int(m) for m in _SERIE_RE.findall(text)}

    em = "ensino medio" in text or bool(series) or "itinerario" in text
    ei = any(k in text for k in ("educacao infantil", "creche", "pre-escola", "pre escola")) \
        or "bebe" in text or "criancas pequenas" in text

    if em:
        intent.etapa = "EM"
        comps = _match(_EM_KEYWORDS, text)
        if "itinerario" in text:
            intent.prefixes = ["emif"]
        else:  # sem componente, o filtro excluiria os trechos narrativos: não filtra
            intent.prefixes = [f"em13{c}" for c in comps]
    elif ei and not years:
        intent.etapa = "EI"
        faixas = [v for k, v in _EI_FAIXAS.items() if k in text]
        intent.prefixes = [f"ei{f}" for f in dict.fromkeys(faixas)]
    elif years:
        intent.etapa = "EF"
        intent.anos = sorted(years)
        comps = _match(_EF_KEYWORDS, text)
        year_keys: list[str] = []
        for y in intent.anos:
            year_keys.append(f"{y:02d}")
            year_keys += [g for g, ys in EF_YEAR_GROUPS.items() if y in ys]
        year_keys = list(dict.fromkeys(year_keys))
        intent.prefixes = [f"ef{k}{c}" for k in year_keys for c in (comps or [""])]
    return intent


def _match(table: dict[str, str], text: str) -> list[str]:
    found = []
    for keyword, code in table.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text) and code not in found:
            found.append(code)
    return found
