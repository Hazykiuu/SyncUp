"""Registra o resultado numérico da cópia congelada do Passo 1, em processo isolado."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def worker(a: Path, b: Path, destino: Path) -> None:
    """Serializa métricas e perfis do Passo 1, sem usar o código atual."""
    sys.path.insert(0, str(RAIZ / 'tests/fixtures/v05_passo1'))
    from app import comparar

    resultados = {}
    for comum in (True, False):
        r = comparar(a, b, 'Perfil A', 'Perfil B', comum)
        perfis = []
        for p in (r.perfil_a, r.perfil_b):
            perfis.append(
                {
                    'plays': p.plays,
                    'horas': p.horas,
                    'quantidade_artistas': p.quantidade_artistas,
                    'arquetipos': {
                        campo: {'nome': d['nome'], 'proporcao': d['proporcao']}
                        for campo, d in asdict(p.arquetipos).items()
                    },
                }
            )
        resultados['comum' if comum else 'completo'] = {
            'metricas': asdict(r.metricas),
            'perfis': perfis,
        }
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    """Gera entradas pequenas ou de 300 mil eventos antes de chamar o processo isolado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', nargs=3)
    parser.add_argument('--escala-grande', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker(*(Path(v) for v in args.worker))
        return
    sys.path.insert(0, str(RAIZ))
    from tools.gerar_dados_falsos import Configuracao, gerar_zip

    tamanho, artistas, bloco = (300_000, 3_000, 25_000) if args.escala_grande else (1_200, 60, 250)
    nome = 'comparacao_passo1_300k.json' if args.escala_grande else 'comparacao_passo1.json'
    with tempfile.TemporaryDirectory() as pasta:
        a = gerar_zip(Path(pasta) / 'perfil_a.zip', Configuracao(tamanho, artistas, 41, bloco))
        b = gerar_zip(Path(pasta) / 'perfil_b.zip', Configuracao(tamanho, artistas, 97, bloco))
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                '--worker',
                str(a),
                str(b),
                str(RAIZ / 'tests/golden' / nome),
            ],
            check=True,
        )


if __name__ == '__main__':
    main()
