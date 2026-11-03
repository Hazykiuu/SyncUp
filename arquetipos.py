"""Arquétipos de escuta da v0.7: regras explicáveis, calibradas para históricos reais.

Cada arquétipo compara uma medida observável com um limiar nomeado. A força é
``valor / limiar`` (≥1 significa que a regra foi atingida). O principal é o de
maior força; os secundários são os dois seguintes. Descrevem hábitos de escuta
no histórico enviado — não medem personalidade, gosto "certo" ou afinidade.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

AVISO_ARQUETIPOS = (
    'Arquétipos são regras sobre hábitos de escuta neste histórico. '
    'Não medem personalidade nem afinidade entre pessoas.'
)


@dataclass(frozen=True)
class RegraArquetipo:
    """Definição de um arquétipo: medida, limiar e textos de apresentação."""

    chave: str
    nome: str
    icone: str
    medida: str
    limiar: float
    frase: str  # Usa {valor} já formatado.
    formato: str = 'pct'  # 'pct' (proporção), 'por100' ou número absoluto
    teto: float = 1.0  # Valor considerado "extremo": intensidade 1.


@dataclass(frozen=True)
class ArquetipoAtingido:
    """Arquétipo avaliado para uma pessoa, com o valor que o justifica."""

    chave: str
    nome: str
    icone: str
    valor: float
    limiar: float
    forca: float
    explicacao: str
    intensidade: float = 0.0  # 0–1 acima do limiar; negativa abaixo dele.


@dataclass(frozen=True)
class PerfilArquetipos:
    """Principal, secundários e todas as avaliações (para transparência)."""

    principal: ArquetipoAtingido
    secundarios: list[ArquetipoAtingido]
    avaliados: list[ArquetipoAtingido]
    quase: list[ArquetipoAtingido]


REGRAS: tuple[RegraArquetipo, ...] = (
    RegraArquetipo(
        'devoto',
        'Devoto(a)',
        '💚',
        'top1',
        0.10,
        'Um único artista ocupa {valor} de tudo o que você ouviu.',
        teto=0.20,
    ),
    RegraArquetipo(
        'explorador',
        'Explorador(a)',
        '🧭',
        'descobertas',
        0.06,
        'A cada 100 plays, você encontrou {valor} artistas diferentes.',
        'por100',
        teto=0.12,
    ),
    RegraArquetipo(
        'coruja',
        'Coruja',
        '🦉',
        'madrugada',
        0.15,
        '{valor} dos seus plays foram entre 0h e 5h59.',
        teto=0.35,
    ),
    RegraArquetipo(
        'madrugador',
        'Madrugador(a)',
        '🌅',
        'manha',
        0.28,
        '{valor} dos seus plays foram de manhã, entre 6h e 11h59.',
        teto=0.45,
    ),
    RegraArquetipo(
        'noturno',
        'Trilha da noite',
        '🌙',
        'noite',
        0.40,
        '{valor} dos seus plays foram entre 18h e 23h59.',
        teto=0.60,
    ),
    RegraArquetipo(
        'fim_de_semana',
        'Fim de semana sonoro',
        '🎉',
        'fim_de_semana',
        0.34,
        '{valor} dos seus plays caíram no sábado ou no domingo.',
        teto=0.50,
    ),
    RegraArquetipo(
        'pulador',
        'Dedo no próximo',
        '⏭️',
        'pulos',
        0.35,
        'Você pulou {valor} das faixas que começou.',
        teto=0.60,
    ),
    RegraArquetipo(
        'aleatorio',
        'Rei/Rainha do aleatório',
        '🔀',
        'aleatorio',
        0.60,
        '{valor} das suas reproduções estavam no modo aleatório.',
        teto=1.0,
    ),
    RegraArquetipo(
        'album',
        'Do começo ao fim',
        '💿',
        'fim_natural',
        0.65,
        '{valor} das faixas tocaram até o fim, sem pular.',
        teto=0.85,
    ),
    RegraArquetipo(
        'maratonista',
        'Maratonista',
        '🔥',
        'sequencia',
        180,
        'Você ouviu música por {valor} dias seguidos.',
        'dias',
        teto=1000,
    ),
    RegraArquetipo(
        'repeat',
        'Modo repeat',
        '🔁',
        'repeticao',
        0.08,
        'Suas 10 músicas favoritas somam {valor} de todos os plays.',
        teto=0.20,
    ),
    RegraArquetipo(
        'offline',
        'Sem sinal, com som',
        '✈️',
        'offline',
        0.20,
        '{valor} das reproduções aconteceram offline.',
        teto=0.60,
    ),
)

EQUILIBRADO = RegraArquetipo(
    'equilibrado',
    'Ouvinte equilibrado(a)',
    '⚖️',
    'nenhuma',
    1.0,
    'Nenhum hábito domina: você distribui a escuta entre horários, artistas e modos.',
)


def formatar_valor(valor: float, formato: str) -> str:
    """Formata o valor de uma regra em pt-BR, sem depender do locale."""
    from formatacao import fmt_num, fmt_pct

    if formato == 'pct':
        return fmt_pct(valor)
    if formato == 'por100':
        return fmt_num(valor * 100, 1)
    return fmt_num(valor)


def classificar(medidas: Mapping[str, float | None]) -> PerfilArquetipos:
    """Avalia todas as regras com medidas disponíveis (``None`` = campo ausente)."""
    avaliados: list[ArquetipoAtingido] = []
    for regra in REGRAS:
        valor = medidas.get(regra.medida)
        if valor is None:
            continue
        valor = float(valor)
        forca = valor / regra.limiar if regra.limiar else 0.0
        if regra.chave == 'album' and (medidas.get('aleatorio') or 0) >= 0.5:
            forca = min(forca, 0.99)  # Ouvir até o fim no aleatório não é "ouvir álbum".
        # Intensidade compara regras de escalas diferentes (dias × proporções).
        if forca >= 1:
            amplitude = max(regra.teto - regra.limiar, 1e-9)
            intensidade = min(1.0, (valor - regra.limiar) / amplitude)
        else:
            intensidade = forca - 1
        avaliados.append(
            ArquetipoAtingido(
                regra.chave,
                regra.nome,
                regra.icone,
                float(valor),
                regra.limiar,
                forca,
                regra.frase.format(valor=formatar_valor(valor, regra.formato)),
                intensidade,
            )
        )
    avaliados.sort(key=lambda a: (-a.intensidade, a.chave))
    atingidos = [a for a in avaliados if a.forca >= 1]
    quase = [a for a in avaliados if 0.8 <= a.forca < 1][:2]
    if atingidos:
        principal, secundarios = atingidos[0], atingidos[1:3]
    else:
        principal = ArquetipoAtingido(
            EQUILIBRADO.chave, EQUILIBRADO.nome, EQUILIBRADO.icone, 0.0, 1.0, 1.0, EQUILIBRADO.frase
        )
        secundarios = []
    return PerfilArquetipos(principal, secundarios, avaliados, quase)
