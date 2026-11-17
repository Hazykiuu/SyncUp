// Contrato de site/app/js/worker.js com um Worker falso (o Node não tem o Worker da web).
import assert from 'node:assert/strict';
import { test } from 'node:test';

const criados = [];
class WorkerFalso {
  constructor(url) { this.url = url; this.enviadas = []; this.encerrado = 0; criados.push(this); }
  postMessage(msg, transferiveis) { this.enviadas.push({ msg, transferiveis }); }
  terminate() { this.encerrado++; }
  responder(data) { this.onmessage?.({ data }); }
}
globalThis.Worker = WorkerFalso;
const { abrirWorker, rodarNoWorker, SEM_RESPOSTA } = await import('../../site/app/js/worker.js');
const ultimo = () => criados.at(-1);
const abortado = (e) => e.name === 'AbortError';

test('uma requisição: resolve com o data inteiro e passa os transferíveis', async () => {
  const w = abrirWorker('x.js');
  const buf = new ArrayBuffer(4);
  const p = w.pedir({ a: 1 }, [buf]);
  assert.deepEqual(ultimo().enviadas[0], { msg: { a: 1 }, transferiveis: [buf] });
  ultimo().responder({ ok: true, dados: 42 });
  assert.deepEqual(await p, { ok: true, dados: 42 });
});

test('duas fases com progresso no meio (protocolo da Batalha)', async () => {
  const etapas = [];
  const w = abrirWorker('b.js', { aoProgresso: (e) => etapas.push(e) });
  const f = ultimo();
  const p1 = w.pedir({ fase: 1 });
  f.responder({ etapa: 'lendo 1 de 3' });
  f.responder({ ok: true, faixas: [1] });
  assert.deepEqual((await p1).faixas, [1]);
  const p2 = w.pedir({ fase: 2 });
  f.responder({ etapa: 'rodadas' });
  f.responder({ ok: true, dados: 'fim' });
  assert.equal((await p2).dados, 'fim');
  assert.deepEqual(etapas, ['lendo 1 de 3', 'rodadas']);
  assert.equal(f.encerrado, 0);
  w.cancelar();
  assert.equal(f.encerrado, 1);
});

test('ok: false rejeita com a mensagem do Worker', async () => {
  const w = abrirWorker('x.js');
  const p = w.pedir({});
  ultimo().responder({ ok: false, erro: 'ZIP inválido' });
  await assert.rejects(p, /ZIP inválido/);
});

test('error e messageerror encerram o Worker e rejeitam', async () => {
  const w = abrirWorker('x.js', { semResposta: 'parou' });
  const p = w.pedir({});
  ultimo().onerror({ preventDefault() {} });
  await assert.rejects(p, /parou/);
  assert.equal(ultimo().encerrado, 1);

  const w2 = abrirWorker('x.js');
  const p2 = w2.pedir({});
  ultimo().onmessageerror();
  await assert.rejects(p2, /não deu para receber/);
  assert.equal(ultimo().encerrado, 1);
  w2.cancelar(); // depois de encerrado por erro: nada
  assert.equal(ultimo().encerrado, 1);
});

test('cancelar: rejeita a pendente com AbortError, é idempotente e barra pedidos novos', async () => {
  const w = abrirWorker('x.js');
  const p = w.pedir({});
  w.cancelar(); w.cancelar();
  await assert.rejects(p, abortado);
  assert.equal(ultimo().encerrado, 1);
  await assert.rejects(w.pedir({}), abortado);
  ultimo().responder({ ok: true }); // resposta atrasada depois de cancelar: ignorada
});

test('cancelar sem nada pendente só encerra', () => {
  const w = abrirWorker('x.js');
  w.cancelar();
  assert.equal(ultimo().encerrado, 1);
});

test('pedir com outro pendente é erro de programação', () => {
  const w = abrirWorker('x.js');
  w.pedir({}).catch(() => {});
  assert.throws(() => w.pedir({}), /em andamento/);
  w.cancelar();
});

test('rodarNoWorker: devolve .dados e encerra o Worker uma vez, com sucesso ou erro', async () => {
  const p = rodarNoWorker('d.js', { a: 1 }, []);
  ultimo().responder({ ok: true, dados: 'r' });
  assert.equal(await p, 'r');
  assert.equal(ultimo().encerrado, 1);

  const p2 = rodarNoWorker('d.js', {}, []);
  ultimo().onerror({});
  await assert.rejects(p2, (e) => e.message === SEM_RESPOSTA);
  assert.equal(ultimo().encerrado, 1);
});
