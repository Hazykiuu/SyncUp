"""Compara medianas antes/depois em processos isolados, com caches frio e quente."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

RAIZ = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Medicao:
    """Tempos de processamento em segundos, excluindo importações e inicialização."""

    frio: float
    memoria: float
    parquet: float | None


def _worker(opcoes: dict[str, Any]) -> Medicao:
    """Mede uma rodada com a versão selecionada antes de importar o aplicativo."""
    sys.path.insert(0, opcoes['pasta'])
    from app import comparar, limpar_cache

    if opcoes['interface']:
        from ui import apresentar
    if opcoes['depois']:
        from configuracao import ConfiguracaoCarga
    a, b = opcoes['a'], opcoes['b']

    def executar(config: Any = None) -> None:
        """Usa o mesmo escopo para ambas as versões: núcleo ou núcleo mais apresentação."""
        kwargs = {'configuracao': config} if config is not None else {}
        r = comparar(a, b, 'A', 'B', opcoes['comum'], **kwargs)
        if opcoes['interface']:
            apresentar(r)

    def cronometrar(config: Any = None) -> float:
        """Finaliza coleta de lixo antes da medida; não a desativa durante processamento."""
        gc.collect()
        inicio = perf_counter()
        executar(config)
        return perf_counter() - inicio

    # Aquecimento de imports, templates, alocador e cache do SO fora da medida.
    executar()
    limpar_cache()
    frio = cronometrar()
    memoria = cronometrar()
    parquet = None
    if opcoes['depois'] and opcoes['parquet']:
        # Pasta privada: nunca apaga o .syncup_cache do usuário.
        with tempfile.TemporaryDirectory(prefix='syncup-bench-') as pasta:
            config = ConfiguracaoCarga(usar_cache_disco=True, diretorio_cache=pasta)
            executar(config)  # Prepara disco fora da medida.
            limpar_cache()  # Obriga releitura do Parquet e SHA original.
            parquet = cronometrar(config)
    limpar_cache()
    return Medicao(frio, memoria, parquet)


def medir_versao(
    pasta: Path, a: Path, b: Path, depois: bool, comum: bool, interface: bool, parquet: bool
) -> Medicao:
    """Isola módulos, caches globais e importações da versão medida."""
    opcoes = {
        'pasta': str(pasta.resolve()),
        'a': str(a.resolve()),
        'b': str(b.resolve()),
        'depois': depois,
        'comum': comum,
        'interface': interface,
        'parquet': parquet,
    }
    processo = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), '--worker-json', json.dumps(opcoes)],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, 'GRADIO_ANALYTICS_ENABLED': 'False'},
    )
    return Medicao(**json.loads(processo.stdout))


def comparar_tempos(
    a: Path,
    b: Path,
    referencia: Path,
    repeticoes: int = 3,
    comum: bool = True,
    interface: bool = True,
    parquet: bool = False,
) -> dict[str, Any]:
    """Alterna a ordem antes/depois por rodada e calcula medianas dos tempos brutos."""
    if repeticoes < 1:
        raise ValueError('Use pelo menos uma repetição.')
    if not (referencia / 'app.py').is_file():
        raise ValueError('A referência precisa ser uma pasta contendo app.py.')
    if not a.is_file() or not b.is_file():
        raise ValueError('Informe dois arquivos de histórico existentes.')
    medidas: dict[str, list[dict[str, Any]]] = {'antes': [], 'depois': []}
    for rodada in range(repeticoes):
        ordem = ('antes', 'depois') if rodada % 2 == 0 else ('depois', 'antes')
        for versao in ordem:
            pasta = referencia if versao == 'antes' else RAIZ
            resultado = medir_versao(pasta, a, b, versao == 'depois', comum, interface, parquet)
            medidas[versao].append(asdict(resultado))
        print(f'Rodada {rodada + 1}/{repeticoes} concluída.', file=sys.stderr, flush=True)
    medianas = {}
    for versao, valores in medidas.items():
        medianas[versao] = {}
        for cenario in ('frio', 'memoria', 'parquet'):
            tempos = [v[cenario] for v in valores if v[cenario] is not None]
            medianas[versao][cenario] = median(tempos) if tempos else None
    bibliotecas = {}
    for nome in ('pandas', 'plotly', 'pyarrow'):
        try:
            bibliotecas[nome] = version(nome)
        except PackageNotFoundError:
            bibliotecas[nome] = None
    entradas = [
        {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
        for p in (a, b)
    ]
    return {
        'ambiente': {
            'python': platform.python_version(),
            'sistema': platform.platform(),
            'bibliotecas': bibliotecas,
        },
        'entradas': entradas,
        'referencia': str(referencia.resolve()),
        'repeticoes': repeticoes,
        'escopo': 'núcleo e apresentação' if interface else 'somente núcleo',
        'periodo_comum': comum,
        'notas': [
            'Frio significa caches de dados do aplicativo vazios; não esvazia cache do sistema operacional.',
            'Quente em memória reutiliza dados preparados; quente Parquet limpa a memória e relê disco.',
            'Não inclui importações, abertura, upload, rede, renderização no navegador ou escrita inicial do Parquet.',
        ],
        'medidas': medidas,
        'medianas': medianas,
    }


def tabela_comparativa(relatorio: dict[str, Any]) -> list[dict[str, str]]:
    """Gera linhas em pt-BR com redução percentual, inclusive quando há regressão."""
    from formatacao import fmt_num, fmt_pct

    nomes = {
        'frio': 'Cache de dados frio',
        'memoria': 'Cache em memória quente',
        'parquet': 'Cache Parquet quente',
    }
    linhas = []
    for chave, nome in nomes.items():
        antes, depois = (
            relatorio['medianas']['antes'][chave],
            relatorio['medianas']['depois'][chave],
        )
        if depois is None:
            continue
        reducao = 1 - depois / antes if antes is not None and antes > 0 else None
        linhas.append(
            {
                'Cenário': nome,
                'Antes (s)': fmt_num(antes, 3) if antes is not None else '—',
                'Depois (s)': fmt_num(depois, 3),
                'Redução': fmt_pct(reducao, 1) if reducao is not None else '—',
            }
        )
    return linhas


def salvar_relatorio(relatorio: dict[str, Any], destino: Path) -> None:
    """Salva tempos brutos em JSON e a tabela em CSV/Markdown sem dependência extra."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = tabela_comparativa(relatorio)
    destino.with_suffix('.json').write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    with destino.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), delimiter=';')
        escritor.writeheader()
        escritor.writerows(linhas)
    markdown = '| Cenário | Antes (s) | Depois (s) | Redução |\n|---|---:|---:|---:|\n'
    markdown += '\n'.join('| ' + ' | '.join(linha.values()) + ' |' for linha in linhas)
    markdown += '\n\n' + '\n'.join('- ' + nota for nota in relatorio['notas']) + '\n'
    destino.with_suffix('.md').write_text(markdown, encoding='utf-8')
    print(markdown)


def main() -> None:
    """Executa medições ou o modo interno de worker em processo separado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arquivo_a', nargs='?')
    parser.add_argument('arquivo_b', nargs='?')
    parser.add_argument('--antes', default=str(RAIZ / 'tests/fixtures/v05_passo1'))
    parser.add_argument('--repeticoes', type=int, default=3)
    parser.add_argument('--historicos-completos', action='store_true')
    parser.add_argument('--somente-nucleo', action='store_true')
    parser.add_argument('--parquet', action='store_true')
    parser.add_argument('--saida', default='benchmark_syncup')
    parser.add_argument('--worker-json', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_json:
        print(json.dumps(asdict(_worker(json.loads(args.worker_json)))))
        return
    if not args.arquivo_a or not args.arquivo_b:
        parser.error('Informe dois arquivos de histórico.')
    try:
        relatorio = comparar_tempos(
            Path(args.arquivo_a),
            Path(args.arquivo_b),
            Path(args.antes),
            args.repeticoes,
            not args.historicos_completos,
            not args.somente_nucleo,
            args.parquet,
        )
    except (ValueError, subprocess.CalledProcessError) as erro:
        detalhe = (
            erro.stderr.strip().splitlines()[-1]
            if isinstance(erro, subprocess.CalledProcessError) and erro.stderr
            else str(erro)
        )
        parser.error(f'Não foi possível medir o desempenho: {detalhe}')
    salvar_relatorio(relatorio, Path(args.saida))


if __name__ == '__main__':
    main()
