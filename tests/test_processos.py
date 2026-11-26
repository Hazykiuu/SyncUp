"""R3-08: encerrar o app à força não pode deixar os processos de leitura órfãos."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

FILHO = (
    'import os, time; from dados import habilitar_leitura_paralela, _executor;'
    'habilitar_leitura_paralela(); pool = _executor(2); pool.submit(abs, -1).result();'
    'time.sleep(3); print(os.getpid(), *pool._processes, flush=True); time.sleep(120)'
)


def _vivo(pid: str) -> bool:
    saida = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True)
    return pid.encode() in saida.stdout


@pytest.mark.skipif(sys.platform != 'win32', reason='o encerramento à força testado é o do Windows')
def test_pool_morre_junto_com_o_app_encerrado_a_forca() -> None:
    raiz = Path(__file__).resolve().parents[1]
    app = subprocess.Popen(
        [sys.executable, '-c', FILHO], cwd=raiz, stdout=subprocess.PIPE, text=True
    )
    pid, *pool = app.stdout.readline().split()
    try:
        assert pool and all(map(_vivo, pool))
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, check=True)
        fim = time.monotonic() + 10
        while any(map(_vivo, pool)) and time.monotonic() < fim:
            time.sleep(0.5)
        assert not [p for p in pool if _vivo(p)]
    finally:
        for p in (pid, *pool):
            subprocess.run(['taskkill', '/F', '/PID', p], capture_output=True)
        app.wait(timeout=10)
