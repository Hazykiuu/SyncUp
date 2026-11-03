"""Conciliação de gostos: quem combina com quem, em pares ótimos e com explicação.

Entrada: perfis no formato unificado (``perfil_gosto.PerfilGosto``), vindos de
ZIP ou da API. Para cada par calcula o cosseno dos vetores de artistas
ponderados por ranking; a matriz de todos contra todos é usada para:

* ranquear, para cada pessoa, com quem ela mais combina;
* formar pares que maximizam a compatibilidade TOTAL do grupo (emparelhamento
  ótimo por programação dinâmica; com número ímpar, a pessoa restante entra no
  par onde combina melhor, formando um trio);
* explicar cada resultado pelos artistas que mais contribuem e sugerir trocas.

Não mede afinidade pessoal: só a sobreposição dos rankings musicais enviados.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from itertools import combinations

import pandas as pd

from metricas import contribuicoes_cosseno, cosseno, jaccard
from perfil_gosto import PerfilGosto, musicas_favoritas, nomes_exibicao, vetor_artistas

MAXIMO_PESSOAS = 16
# Faixas calibradas com 4 históricos reais (2017–2026). Rankings de top 50 se
# sobrepõem pouco mesmo entre amigos: 10 pontos já indicam muitos favoritos comuns.
NIVEIS = (
    (25.0, 'Sintonia rara', 'Rankings muito parecidos: compartilhar playlists é garantia.'),
    (10.0, 'Alta compatibilidade', 'Vários favoritos em comum, com espaço para descobertas.'),
    (5.0, 'Boa compatibilidade', 'Uma base em comum para começar a trocar músicas.'),
    (1.0, 'Compatibilidade baixa', 'Poucos pontos em comum, mas ótimo para sair da bolha.'),
    (0.0, 'Mundos diferentes', 'Quase nada em comum nos rankings enviados.'),
)


@dataclass(frozen=True)
class Compatibilidade:
    """Resultado de um par, com os motivos."""

    a: str
    b: str
    pontuacao: float  # 0–100
    nivel: str
    descricao: str
    artistas_comuns: list[str]  # ordenados pela contribuição ao cosseno
    musicas_comuns: int
    jaccard_artistas: float
    recomendacoes_para_a: list[str]  # favoritos de B ausentes no ranking de A
    recomendacoes_para_b: list[str]


@dataclass(frozen=True)
class ResultadoConciliacao:
    """Matriz, pares ótimos e detalhes de todos os pares."""

    nomes: list[str]
    matriz: pd.DataFrame
    pares: list[tuple[str, ...]]  # pares (ou um trio) escolhidos
    pontuacao_media_pares: float
    detalhes: dict[frozenset[str], Compatibilidade]
    melhores: dict[str, list[tuple[str, float]]]

    def par(self, x: str, y: str) -> Compatibilidade:
        return self.detalhes[frozenset((x, y))]


def nivel(pontuacao: float) -> tuple[str, str]:
    """Rótulo e frase para uma pontuação de 0 a 100."""
    for limite, rotulo, frase in NIVEIS:
        if pontuacao >= limite:
            return rotulo, frase
    return NIVEIS[-1][1], NIVEIS[-1][2]


def _recomendar(
    origem: dict[str, float], destino: dict[str, float], nomes: dict[str, str], n: int
) -> list[str]:
    """Artistas fortes na origem que não aparecem em nenhum ranking do destino."""
    candidatos = sorted(
        ((peso, chave) for chave, peso in origem.items() if chave not in destino),
        key=lambda x: (-x[0], x[1]),
    )
    return [nomes.get(chave, chave) for _, chave in candidatos[:n]]


def comparar_perfis(a: PerfilGosto, b: PerfilGosto, n_exemplos: int = 8) -> Compatibilidade:
    """Compatibilidade entre duas pessoas, com explicação."""
    va, vb = vetor_artistas(a), vetor_artistas(b)
    valor = cosseno(va, vb) if va and vb else None
    pontuacao = round((valor or 0.0) * 100, 1)
    nomes = {**nomes_exibicao(b), **nomes_exibicao(a)}
    contribuicoes = contribuicoes_cosseno(va, vb) if va and vb else {}
    comuns = [
        nomes.get(chave, chave)
        for chave, c in sorted(contribuicoes.items(), key=lambda x: (-x[1], x[0]))
        if c > 0
    ]
    rotulo, frase = nivel(pontuacao)
    return Compatibilidade(
        a=a.nome,
        b=b.nome,
        pontuacao=pontuacao,
        nivel=rotulo,
        descricao=frase,
        artistas_comuns=comuns,
        musicas_comuns=len(musicas_favoritas(a) & musicas_favoritas(b)),
        jaccard_artistas=jaccard(va.keys(), vb.keys()) or 0.0,
        recomendacoes_para_a=_recomendar(vb, va, nomes_exibicao(b), n_exemplos),
        recomendacoes_para_b=_recomendar(va, vb, nomes_exibicao(a), n_exemplos),
    )


def emparelhamento_otimo(matriz: pd.DataFrame) -> list[tuple[str, ...]]:
    """Pares que maximizam a soma das compatibilidades (exato, até 16 pessoas).

    Com número ímpar, a pessoa sem par entra no par em que tem a maior média de
    compatibilidade com os dois membros, formando um trio.
    """
    nomes = list(matriz.index)
    n = len(nomes)
    if n < 2:
        return [tuple(nomes)] if nomes else []
    valores = matriz.values.tolist()

    @cache
    def melhor(restantes: int) -> tuple[float, tuple[tuple[int, int], ...]]:
        if restantes == 0:
            return 0.0, ()
        i = (restantes & -restantes).bit_length() - 1  # primeiro índice livre
        sem_i = restantes & ~(1 << i)
        opcoes = []
        if bin(restantes).count('1') % 2 == 1:
            # i fica sozinho (só acontece uma vez quando n é ímpar).
            total, pares = melhor(sem_i)
            opcoes.append((total, pares))
        j_bits = sem_i
        while j_bits:
            j = (j_bits & -j_bits).bit_length() - 1
            j_bits &= j_bits - 1
            total, pares = melhor(sem_i & ~(1 << j))
            opcoes.append((total + valores[i][j], ((i, j), *pares)))
        return max(opcoes, key=lambda x: (x[0], [-k for par in x[1] for k in par]))

    _, pares_idx = melhor((1 << n) - 1)
    usados = {k for par in pares_idx for k in par}
    grupos = [list(par) for par in pares_idx]
    sobra = [k for k in range(n) if k not in usados]
    if sobra and grupos:
        s = sobra[0]
        melhor_grupo = max(grupos, key=lambda g: (sum(valores[s][k] for k in g) / len(g), -g[0]))
        melhor_grupo.append(s)
    elif sobra:
        grupos.append(sobra)
    return [tuple(nomes[k] for k in g) for g in grupos]


def conciliar(perfis: list[PerfilGosto]) -> ResultadoConciliacao:
    """Compara todos com todos e forma os pares mais compatíveis."""
    if len(perfis) < 2:
        raise ValueError('Adicione pelo menos duas pessoas para conciliar.')
    if len(perfis) > MAXIMO_PESSOAS:
        raise ValueError(f'Use no máximo {MAXIMO_PESSOAS} pessoas por conciliação.')
    nomes = [p.nome for p in perfis]
    if len(set(nomes)) != len(nomes):
        raise ValueError('Cada pessoa precisa de um nome diferente.')
    detalhes: dict[frozenset[str], Compatibilidade] = {}
    matriz = pd.DataFrame(100.0, index=nomes, columns=nomes)
    for a, b in combinations(perfis, 2):
        c = comparar_perfis(a, b)
        detalhes[frozenset((a.nome, b.nome))] = c
        matriz.loc[a.nome, b.nome] = matriz.loc[b.nome, a.nome] = c.pontuacao
    pares = emparelhamento_otimo(matriz)
    pontuacoes = [
        detalhes[frozenset((x, y))].pontuacao for g in pares for x, y in combinations(g, 2)
    ]
    melhores = {
        nome: sorted(
            ((outro, float(matriz.loc[nome, outro])) for outro in nomes if outro != nome),
            key=lambda x: (-x[1], x[0]),
        )
        for nome in nomes
    }
    return ResultadoConciliacao(
        nomes=nomes,
        matriz=matriz,
        pares=pares,
        pontuacao_media_pares=sum(pontuacoes) / len(pontuacoes) if pontuacoes else 0.0,
        detalhes=detalhes,
        melhores=melhores,
    )
