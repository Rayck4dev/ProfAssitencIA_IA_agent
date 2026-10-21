from __future__ import annotations

import pytest

from app.titles import make_title


@pytest.mark.parametrize("pedido, titulo", [
    ("Crie um plano de aula de matemática para o 5º ano sobre frações, com duração de 50 minutos.",
     "Plano de aula · Matemática · 5º ano · frações"),
    ("Monte uma sequência didática de 4 aulas de história para o 8º ano sobre a república",
     "Sequência didática · História · 8º ano · república"),
    ("aula de matematca pro 5 ano sobre fraçoes", "Aula · Matemática · 5º ano · fraçoes"),
    ("Preciso de ideias de atividade para alfabetização no 2º ano", "Atividade · Língua Portuguesa · 2º ano"),
    ("me ajuda com uma prova de física do ensino médio sobre cinemática",
     "Avaliação · Ciências da Natureza · Ensino Médio · cinemática"),
    ("Planeje uma aula de revisão de ciências para o 6º ano sobre o sistema solar e os planetas do nosso sistema",
     "Aula de revisão · Ciências · 6º ano · sistema solar e os planetas"),
    ("Elabore uma atividade avaliativa de [componente] para o [ano] sobre [tema]", "Atividade avaliativa"),
    ("oi, tudo bem?", "Oi tudo bem"),
    ("", "Nova conversa"),
    ("   ", "Nova conversa"),
])
def test_titulos(pedido, titulo):
    assert make_title(pedido) == titulo


def test_titulo_nunca_passa_do_limite_nem_termina_em_palavra_solta():
    longo = "Crie um plano de aula de matemática para o 5º ano sobre " + "operações com números decimais e frações equivalentes " * 3
    title = make_title(longo)
    assert len(title) <= 70 and not title.endswith(("de", "e", "com"))
