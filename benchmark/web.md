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
| Preact (unpkg) | tamanho invisível (`transferSize` = 0); hipótese: o unpkg não manda `Timing-Allow-Origin` (não conferido nos cabeçalhos) |
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

## Depois: v1.14 (mesmo ambiente, mesmos cenários)

### Motor (Node, mediana de 3)

O código do motor não mudou na v1.14 (só constantes passaram a vir de `calculo.js`). As diferenças abaixo são a variação entre execuções da mesma máquina: com uma diferença de até cerca de 30%, nenhuma mudança de desempenho menor que isso pode ser afirmada.

| Cenário | Leitura (ms) | Wrapped (ms) | Heap depois (MB) |
|---|---:|---:|---:|
| P | 80 | 58 | 19 |
| M | 377 | 100 | 57 |
| G | 1 243 | 321 | 160 |
| GG | 3 997 | 897 | 243 |

Dupla G + G2: **4 557 ms**.

### Carregamento inicial

- Os recursos terminam de chegar em cerca de 45 ms localmente: 23 módulos JS, um a mais que antes (`js/worker.js`, 2 KB).
- Sem long tasks na carga e CLS 0.
- **FCP e LCP não são confiáveis neste painel.** Deu 652 ms antes e 3 352 ms agora, com todos os recursos prontos aos 45 ms nas duas vezes. A hipótese é que a primeira pintura dependa de o painel estar visível (não confirmado). Para esses dois números, use o Lighthouse do Chrome no site publicado (medição manual, ainda não feita).

### Processamento (navegador)

| Caso | Antes | Depois | Long tasks no main thread (depois) |
|---|---:|---:|---|
| Dupla, demo | 628 ms | 606 ms | nenhuma |
| Dupla G + G2 | 3 285 ms | 3 901 ms | nenhuma |
| Wrapped G | 1 138 ms | 1 292 ms | nenhuma |
| Wrapped GG | 3 263 ms | 3 516 ms | nenhuma |
| Batalha P + M + G + G2 | 4 030 ms | 4 319 ms | nenhuma |

As diferenças ficam dentro da variação: o processamento roda nos mesmos Workers, com o mesmo código.

### Memória em execuções repetidas

Dupla demo 5 vezes, heap 10 s depois de cada uma: 16,7 → 9,2 → 8,8 → 10,8 → 9,1 MB. A primeira medida inclui o que sobrou das execuções grandes anteriores. A tendência é estável e não há crescimento contínuo, então não foi preciso comparar heap snapshots.

### Limites de arquivo

- **49,71 MB, válido:** o histórico G mais uma entrada `.bin` de enchimento. Foi aceito e processado (1,3 s), e a entrada que não é JSON foi ignorada.
- **50 MB + 1 byte:** recusado na hora com "Passou de 50 MB para esta pessoa".
- **ZIP malicioso:** coberto em `tests/js/historico.test.mjs`. Recusa o ZIP truncado, o cabeçalho que mente o tamanho, a entrada acima de 64 MB e, agora, a soma declarada acima de 1 GiB.

### Outras verificações (v1.14)

- **H1, desktop:** Dupla G + G2 e Wrapped GG ao mesmo tempo, com três trocas de modo no meio. As duas terminaram (3,5 s e 3,7 s), sem erro e sem long task. Os eventos medidos ficaram em até 48 ms (só eventos de ponteiro; os cliques sintéticos não entram no Event Timing). O risco de memória no celular **não foi testado**.
- **375 px:** Dupla, Wrapped e Batalha sem rolagem horizontal.
- **Pôsteres:** os três desenham (PNG de 1,3 a 1,5 MB) depois da consolidação.
- **Corrida:** o arraste real move o slider e pausa a corrida, e nada se move depois de soltar.

### Não medido

- Batalha 4×M e 6×G.
- INP real de cliques durante o processamento.
- LCP e CLS no site publicado.
- Memória dos Workers.
- Celular real.

### Conclusão da etapa de desempenho

Nenhuma otimização entrou na v1.14:

- nenhuma long task do app passou de 100 ms (a maior, antes, foi de 53 ms);
- o main thread fica livre durante o processamento;
- a memória não cresce entre execuções.

Os candidatos do plano (`import()` das telas, leitura do `File` dentro do Worker na Dupla) não têm problema medido que justifique a mudança.

