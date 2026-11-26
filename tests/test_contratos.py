"""Contrato entre os motores (R3-04): regras copiadas à mão no JS e invariantes das métricas.

A paridade compara saídas e só pega uma constante quando os dados cruzam o valor dela.
Aqui o valor é lido do arquivo JS e comparado com o do Python.
"""

from __future__ import annotations

import ast
import inspect
import json
import random
import re
import subprocess

import pytest

import analise
import arquetipos
import componentes
import conciliacao
import convite
import dados
import perfil_gosto
import recursos
import ui.dupla
import wrapped
from configuracao import normalizar_nome
from metricas import cosseno, jaccard, jaccard_ponderado, rbo
from tests.test_paridade_wrapped import NODE, RAIZ

pytestmark = pytest.mark.skipif(NODE is None, reason='Node não instalado')


def _fonte(arquivo: str) -> str:
    return (RAIZ / 'site/app/js' / arquivo).read_text(encoding='utf-8')


def _node(script: str, entrada: object) -> object:
    saida = subprocess.run(
        [NODE, '--input-type=module', '-e', script],
        cwd=RAIZ,
        input=json.dumps(entrada).encode(),
        capture_output=True,
        check=True,
    )
    return json.loads(saida.stdout)


def _expressao(arquivo: str, nome: str) -> str:
    """O lado direito de ``nome = …`` no JS: lista, objeto ou valor simples."""
    achado = re.search(
        rf'\b{nome}\s*=\s*(\[[\s\S]*?\](?=;|\.map\()|\{{[^}}]*\}}|[^,;]+)', _fonte(arquivo)
    )
    assert achado, f'{nome} sumiu de {arquivo}'
    return achado.group(1)


def _familias_python() -> list:
    arvore = ast.parse(inspect.getsource(dados.familia_plataforma))
    laco = next(n for n in ast.walk(arvore) if isinstance(n, ast.For))
    return ast.literal_eval(laco.iter)


def _regra(r) -> list:
    return [r.chave, r.nome, r.icone, r.medida, r.limiar, r.frase, r.formato, r.teto]


def _pares() -> list[tuple[str, str, str, object]]:
    """(rótulo, arquivo JS, nome no JS, valor que o Python usa)."""
    p, r = inspect.signature(rbo).parameters['p'], inspect.signature(rbo).parameters['k']
    assert (p.default, r.default) == (0.9, 50)
    return [
        ('janelas', 'match.js', 'JANELAS_DIAS', perfil_gosto.JANELAS_DIAS),
        ('peso dos períodos', 'match.js', 'PESO_PERIODO', perfil_gosto.PESO_PERIODO),
        ('peso das músicas', 'match.js', 'PESO_MUSICAS', perfil_gosto.PESO_MUSICAS),
        ('tamanho do ranking', 'match.js', 'TAMANHO_RANKING', perfil_gosto.TAMANHO_RANKING),
        ('faixas do Match', 'match.js', 'NIVEIS', conciliacao.NIVEIS),
        ('máximo de pessoas', 'match.js', 'MAXIMO_PESSOAS', conciliacao.MAXIMO_PESSOAS),
        ('amostra mínima', 'match.js', 'AMOSTRA_MINIMA', conciliacao.AMOSTRA_MINIMA),
        ('convite: prefixo', 'convite.js', 'PREFIXO', convite.PREFIXO),
        ('convite: código', 'convite.js', 'MAXIMO_CODIGO', convite.MAXIMO_CODIGO),
        ('convite: JSON', 'convite.js', 'MAXIMO_JSON', convite.MAXIMO_JSON),
        ('convite: nome', 'convite.js', 'MAXIMO_NOME', convite.MAXIMO_NOME),
        ('convite: texto', 'convite.js', 'MAXIMO_TEXTO', convite.MAXIMO_TEXTO),
        ('teto do ZIP', 'historico.js', 'LIMITE_BYTES', dados.LIMITE_BYTES),
        ('play mais longo', 'historico.js', 'TETO_MS', dados.TETO_MS),
        ('famílias de aparelho', 'historico.js', 'FAMILIAS', _familias_python()),
        ('play mínimo', 'calculo.js', 'TEMPO_MINIMO_PLAY_MS', analise.TEMPO_MINIMO_PLAY_MS),
        ('campos conhecidos', 'calculo.js', 'MINIMO_CONHECIDOS', wrapped.MINIMO_CONHECIDOS),
        ('arquétipos', 'calculo.js', 'REGRAS', [_regra(r) for r in arquetipos.REGRAS]),
        ('piso do Wrapped', 'calculo.js', 'MINIMO_PLAYS_WRAPPED', wrapped.MINIMO_PLAYS_WRAPPED),
        ('meia-vida', 'dupla.js', 'MEIA_VIDA_DIAS', analise.MEIA_VIDA_DIAS),
        ('profundidade do RBO', 'dupla.js', 'PROFUNDIDADE_RBO', analise.PROFUNDIDADE_RBO),
        ('top de artistas', 'dupla.js', 'TOP', analise.QUANTIDADE_TOP_ARTISTAS),
        ('top de músicas', 'dupla.js', 'TOP', analise.QUANTIDADE_TOP_MUSICAS),
        ('corrida', 'dupla.js', 'ARTISTAS_CORRIDA', componentes.ARTISTAS_CORRIDA),
        ('quase juntos: janela', 'dupla.js', 'JANELA_MS',
         recursos.JANELA_SINCRONIA_HORAS * 3_600_000),
        ('quase juntos: exemplos', 'dupla.js', 'MAXIMO_EXEMPLOS',
         recursos.MAXIMO_EXEMPLOS_SINCRONIA),
        ('ao mesmo tempo', 'dupla.js', 'MINIMO_JUNTOS_MS', recursos.MINIMO_JUNTOS_S * 1000),
        ('ponte', 'dupla.js', 'MAXIMO_PONTE', recursos.MAXIMO_DESCOBERTAS_POR_DIRECAO),
    ]  # fmt: skip


def test_constantes_do_js_sao_as_do_python() -> None:
    pares = _pares()
    js = _node(
        "let s = ''; for await (const c of process.stdin) s += c;"
        'process.stdout.write(JSON.stringify(JSON.parse(s).map((e) => Function(`return (${e})`)())));',
        [_expressao(arquivo, nome) for _, arquivo, nome, _ in pares],
    )
    diferentes = [
        (rotulo, valor, no_js)
        for (rotulo, _, _, valor), no_js in zip(pares, js, strict=True)
        if json.loads(json.dumps(valor)) != no_js
    ]
    assert not diferentes


def test_copias_do_python_e_literais_do_js() -> None:
    assert perfil_gosto.TEMPO_MINIMO_PLAY_MS == analise.TEMPO_MINIMO_PLAY_MS
    assert wrapped.TEMPO_MINIMO_PLAY_MS == analise.TEMPO_MINIMO_PLAY_MS
    assert 'slice(0, 20), so_a' in _fonte('dupla.js')  # conexões: o mesmo 20 de web/ponte.py
    assert re.search(r'rbo\(a, b, p = 0\.9, k = 50\)', _fonte('dupla.js'))
    for arquivo in ('match-tela.js', 'main.js'):  # o 16 vem da constante
        assert not re.search(r'(<|\ba) 16\b', _fonte(arquivo)), arquivo
    # Diferença intencional (R1-07): só o navegador limita cada JSON do ZIP, para o iOS não fechar.
    assert _expressao('historico.js', 'LIMITE_ENTRADA') == '64 * 1048576'
    assert not hasattr(dados, 'LIMITE_ENTRADA')


def test_batalha_aceita_o_mesmo_tamanho_de_grupo() -> None:
    aceitos = _node(
        "import { validarNomes } from './site/app/js/batalha.js';"
        'process.stdout.write(JSON.stringify([...Array(10).keys()].filter((n) => {'
        ' try { validarNomes([...Array(n).keys()].map((k) => `P${k}`)); return true; } catch { return false; } })));',
        None,
    )
    assert aceitos == list(range(analise.MINIMO_PERFIS_GRUPO, analise.MAXIMO_PERFIS_GRUPO + 1))


def _casos() -> list:
    sorteio = random.Random(11)
    casos = []
    for k in range(500):
        universo = [f'a{i}' for i in range(sorteio.choice([3, 10, 80, 200]))]
        a, b = (
            {x: sorteio.randint(1, 500) for x in sorteio.sample(universo, sorteio.randint(1, len(universo)))}
            for _ in range(2)
        )  # fmt: skip
        if k % 7 == 0:  # pares sem nada em comum
            b = {f'z{x}': v for x, v in b.items()}
        casos.append((a, b, sorted(a, key=a.get, reverse=True), sorted(b, key=b.get, reverse=True)))
    return casos


def _metricas(a, b, ra, rb) -> list[float]:
    return [cosseno(a, b), jaccard(a, b), jaccard_ponderado(a, b), rbo(ra, rb)]


def test_invariantes_das_metricas_nos_dois_motores() -> None:
    """Simetria, identidade, [0, 1], determinismo e Python × JS (tolerância: a soma do JS muda de ordem)."""
    casos = _casos()
    js = _node(
        "import { cosseno, jaccard, ruzicka, rbo } from './site/app/js/dupla.js';"
        "let s = ''; for await (const c of process.stdin) s += c;"
        'const M = (o) => new Map(Object.entries(o));'
        'const f = ([a, b, ra, rb]) => [cosseno(M(a), M(b)), jaccard(Object.keys(a), Object.keys(b)), ruzicka(M(a), M(b)), rbo(ra, rb)];'
        'process.stdout.write(JSON.stringify(JSON.parse(s).map((c) => [f(c), f([c[1], c[0], c[3], c[2]]), f([c[0], c[0], c[2], c[2]]), f(c)])));',
        casos,
    )
    tol = pytest.approx
    for (a, b, ra, rb), (ab_js, ba_js, aa_js, de_novo) in zip(casos, js, strict=True):
        ab = _metricas(a, b, ra, rb)
        assert _metricas(b, a, rb, ra) == tol(ab, abs=1e-12)
        assert ba_js == tol(ab_js, abs=1e-12)
        assert _metricas(a, a, ra, ra) == tol([1] * 4, abs=1e-12)
        assert aa_js == tol([1] * 4, abs=1e-12)
        assert all(-1e-12 <= x <= 1 + 1e-12 for x in ab + ab_js)
        assert _metricas(a, b, ra, rb) == ab and de_novo == ab_js
        assert ab_js == tol(ab, abs=1e-12)


def test_telas_do_pc_e_do_navegador_usam_a_mesma_ponderacao() -> None:
    """R3-01: só as telas; a API (analise.comparar) segue em 'bruta' por causa dos testes e de quem a chama."""
    web = re.search(r"ponderacao: '(\w+)'", _fonte('opcoes.js')).group(1)
    layout = (RAIZ / 'ui/layout.py').read_text(encoding='utf-8')
    pc = re.findall(r"value=(.+?),\s*label='Pondera", layout)
    assert web == 'log1p' and pc and set(pc) == {'PONDERACAO_DAS_TELAS'}
    assert ui.dupla.PONDERACAO_DAS_TELAS == web
    assert inspect.signature(analise.comparar).parameters['ponderacao'].default == 'bruta'


# R1-08: o mesmo nome tem de virar a mesma chave nos dois motores.
NOMES = ['Stra\u00dfe', '\u0131stanbul', 'Istanbul', '\ufb01nal', 'Bey\u200bonc\u00e9',
         '\u03a3\u038a\u03a3\u03a5\u03a6\u039f\u03a3', '\u13a0', '\uab70', '\u13f8']  # fmt: skip


def test_nomes_normalizados_iguais_nos_dois_motores() -> None:
    js = _node(
        "import { normalizarNome } from './site/app/js/historico.js';"
        "let s = ''; for await (const c of process.stdin) s += c;"
        'process.stdout.write(JSON.stringify(JSON.parse(s).map(normalizarNome)));',
        NOMES,
    )
    assert js == [normalizar_nome(n) for n in NOMES]
