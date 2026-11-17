# Benchmark do app no navegador (v1.14)

Medições de laboratório. Não são dados de campo, e o SyncUp não coleta dados de uso, então não há como afirmar Core Web Vitals (a avaliação oficial usa o percentil 75 de usuários reais). Servem só para comparar antes e depois no mesmo ambiente.

## Ambiente

- AMD Ryzen 5 8600G (12 threads), 31,6 GiB, Windows 11 (10.0.26300).
- Motor: Node v24.19.0.
- Navegador: Chromium 156 (painel do app desktop do Claude). Na primeira medição o painel estava oculto (página em segundo plano), então os tempos do navegador são aproximados.
- O painel emula larguras, mas não a CPU de um celular.
- Site servido localmente: `python -m http.server` em `site/`, com as demos geradas por `python tools/empacotar_web.py`.

## Cenários

Gerados com `python tools/gerar_dados_falsos.py <saída> --linhas N --seed S`. Ficam fora do repositório e são reproduzíveis pela semente.

| Cenário | Linhas | Semente | ZIP |
|---|---:|---:|---:|
| P | 20 000 | 42 | 0,6 MB |
| M | 100 000 | 42 | 3,0 MB |
| G | 300 000 | 42 | 8,9 MB |
| G2 | 300 000 | 7 | 8,9 MB |
| GG | 1 000 000 | 42 | 29,8 MB |

O GG fica abaixo do teto de 50 MB por pessoa (`envio.js`). O teto é em bytes: o teste de 49,9 MB válido e de 50 MB + 1 recusado está na seção de limites.

## Referência: v1.13.0 (antes de qualquer mudança)

### Motor (Node, mediana de 3)

Script descartável que chama `lerHistorico`, `calcularWrapped` e `compararDupla` com `performance.now()`, como `tests/js/rodar_*.mjs`.

| Cenário | Leitura (ms) | Wrapped (ms) | Heap depois (MB) |
|---|---:|---:|---:|
| P | 95 | 52 | 22 |
| M | 517 | 153 | 55 |
| G | 1 718 | 378 | 88 |
| GG | 4 416 | 1 206 | 244 |

Dupla G + G2 (identificar, ler e comparar): **5 493 ms**.

### Carregamento inicial (local, cache vazio, antes de qualquer clique)

| Medida | Valor |
|---|---|
| TTFB (local, só referência) | 3 ms |
| FCP = LCP (elemento `H1`) | 652 ms (painel oculto, aproximado) |
| CLS | 0,0000 |
| Long tasks na carga | nenhuma registrada |
| JS carregado (decodificado, sem o Preact) | 260 001 B em 22 módulos, todos de imediato (nenhum `import()`) |
| Preact (unpkg) | tamanho invisível: o unpkg não manda `Timing-Allow-Origin` (`transferSize` = 0) |
| CSS | 108 297 B em 4 arquivos, **todos bloqueiam a renderização** |
| Fonte Figtree | 62 712 B, com preload e `font-display: swap`; sem CLS medido |
| Heap do main thread depois da carga | 2,4 MB |

### Processamento (navegador, do clique até os stories aparecerem)

| Caso | Tempo | Long tasks no main thread |
|---|---:|---|
| Dupla, demo (Ana + Bruno) | 628 ms | 1 × 53 ms |
| Dupla G + G2 | 3 285 ms | nenhuma |
| Wrapped G | 1 138 ms | nenhuma |
| Wrapped GG | 3 263 ms | nenhuma |
| Batalha P + M + G + G2 | 4 030 ms | nenhuma |

Todo o cálculo roda em Workers; o main thread fica livre durante o processamento. A memória dos Workers não aparece em `performance.memory` e não foi medida.

### Memória em execuções repetidas

Dupla demo 5 vezes seguidas, `usedJSHeapSize` 10 s depois de cada uma: 9,1 → 7,6 → 7,6 → 7,6 MB. A 5ª medição não foi registrada porque o script de medição esgotou o tempo. A tendência é estável, sem sinal de retenção.

### Comportamentos confirmados (Etapa 0)

- **H2:** com o modo escondido, a animação da barra some; ao voltar, o mesmo story recomeça o segmento do zero (`currentTime` 5003 ms → 261 ms, ainda em 3/7). O relógio em JS deve manter isso.
- **P8:** com o foco em "Próximo story", o Espaço **pausou** em vez de avançar.
- **P12 (360 px):** sem rolagem horizontal, mas os 12 nomes de `.su-arch-detail` ficam com **0 px** de largura. `.sb-titulo` fica com 8,64 px.
