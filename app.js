/**
 * Ferramenta TSE — cliente web.
 * Toda comunicação com o backend via fetch() para /api/index.
 */

const API = '/api/index';

const _TSE_BASE = 'https://divulgacandcontas.tse.jus.br/divulga/';
const _TSE_CD = { 2024: '2045202024', 2020: '2030402020', 2016: '2', 2012: '1699' };

function tseCandidatoUrl(ano, sq, cdMun) {
  const cd = _TSE_CD[ano];
  return (cd && sq && cdMun)
    ? `${_TSE_BASE}#/candidato/CENTRO-OESTE/GO/${cd}/${sq}/${ano}/${cdMun}` : '';
}

// ── Utilitários ───────────────────────────────────────────────────────────────

async function apiFetch(params) {
  const qs = new URLSearchParams(params).toString();
  const resp = await fetch(`${API}?${qs}`);
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.erro || `Erro ${resp.status}`);
  return data;
}

function callout(text, kind = 'info') {
  const div = document.createElement('div');
  div.className = `tse-callout tse-callout-${kind}`;
  div.innerHTML = text;
  return div;
}

function spinner() {
  const span = document.createElement('span');
  span.className = 'tse-spinner';
  return span;
}

function badge(text, kind = 'suplente') {
  const map = { eleito: 'badge-eleito', suplente: 'badge-suplente', naoel: 'badge-naoel', reeleicao: 'badge-reeleicao', atual: 'badge-atual' };
  return `<span class="badge ${map[kind] || 'badge-suplente'}">${text}</span>`;
}

function populateSelect(sel, options, placeholder) {
  sel.innerHTML = '';
  if (placeholder) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = placeholder;
    opt.disabled = true;
    opt.selected = true;
    sel.appendChild(opt);
  }
  options.forEach(v => {
    const opt = document.createElement('option');
    opt.value = String(v);
    opt.textContent = String(v);
    sel.appendChild(opt);
  });
}

// ── Abas ──────────────────────────────────────────────────────────────────────

document.querySelectorAll('.tse-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tse-tab').forEach(b => b.setAttribute('aria-selected', 'false'));
    document.querySelectorAll('.tse-section').forEach(s => s.classList.remove('active'));
    btn.setAttribute('aria-selected', 'true');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

// ── Inicialização: carrega anos e municípios ──────────────────────────────────

async function init() {
  try {
    const [{ anos }, { municipios }] = await Promise.all([
      apiFetch({ action: 'anos' }),
      apiFetch({ action: 'municipios' }),
    ]);

    // aba Listar — anos em ordem crescente (2012→2024), 2024 pré-selecionado
    const selAno = document.getElementById('ano-listar');
    populateSelect(selAno, anos);
    selAno.value = String(anos[anos.length - 1]);

    // municípios filtrados por ano (atualiza ao mudar ano)
    const selMun = document.getElementById('municipio-listar');
    async function atualizarMunicipios() {
      const ano = selAno.value;
      try {
        const { municipios: muns } = await apiFetch({ action: 'municipios', ano });
        populateSelect(selMun, muns);
      } catch {
        populateSelect(selMun, municipios);
      }
    }
    selAno.addEventListener('change', atualizarMunicipios);
    await atualizarMunicipios();

    // aba Rastrear
    populateSelect(document.getElementById('municipio-rastrear'), municipios);

    // Rodapé com anos cobertos
    if (anos.length) {
      document.getElementById('rodape').innerHTML =
        `Eleições cobertas: ${anos.join(', ')} &nbsp;&middot;&nbsp; Fonte: TSE Dados Abertos &mdash; consulta_cand`;
    }
  } catch (e) {
    document.body.prepend(callout(`Falha ao carregar dados: ${e.message}`, 'erro'));
  }
}

init();

// ── Aba: Listar ───────────────────────────────────────────────────────────────

function situacaoBadge(situacao) {
  const s = (situacao || '').toUpperCase();
  if (s.startsWith('ELEITO')) return badge(situacao, 'eleito');
  if (s === 'SUPLENTE') return badge(situacao, 'suplente');
  return badge(situacao, 'naoel');
}

function renderTabela(candidatos, title) {
  if (!candidatos.length) return '';
  const rows = candidatos.map(c => {
    const url = tseCandidatoUrl(c.ano, c.sq_candidato, c.cd_municipio);
    const nomeCell = url
      ? `<a class="tse-cand-link" href="${url}" target="_blank" rel="noopener">${c.nome}</a>`
      : c.nome;
    return `
    <tr>
      <td>${nomeCell}</td>
      <td>${c.urna || ''}</td>
      <td>${c.partido || ''}</td>
      <td>${situacaoBadge(c.situacao)}</td>
    </tr>`;
  }).join('');
  return `
    <h3 class="tse-subhead">${title}</h3>
    <div class="tse-table-wrap">
      <table>
        <thead><tr><th>Nome</th><th>Nome Urna</th><th>Partido</th><th>Situação</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

document.getElementById('form-listar').addEventListener('submit', async e => {
  e.preventDefault();
  const ano = document.getElementById('ano-listar').value;
  const municipio = document.getElementById('municipio-listar').value;
  const cargo = document.getElementById('cargo-listar').value;
  const out = document.getElementById('resultado-listar');

  out.innerHTML = '';
  const sp = spinner();
  out.appendChild(sp);
  out.appendChild(document.createTextNode(' Pesquisando…'));

  try {
    const { eleitos, nao_eleitos } = await apiFetch({ action: 'listar', ano, municipio, cargo });
    out.innerHTML = '';

    // Cards de métrica
    const total = eleitos.length + nao_eleitos.length;
    out.innerHTML += `
      <div class="tse-metrics">
        <div class="tse-metric">
          <div class="tse-metric-value eleito">${eleitos.length}</div>
          <div class="tse-metric-label">Eleito(s)</div>
        </div>
        <div class="tse-metric">
          <div class="tse-metric-value">${nao_eleitos.length}</div>
          <div class="tse-metric-label">Não eleito(s) / Suplente(s)</div>
        </div>
        <div class="tse-metric">
          <div class="tse-metric-value">${total}</div>
          <div class="tse-metric-label">Total de candidatos</div>
        </div>
      </div>`;

    // Botão Excel
    const excelUrl = `${API}?action=excel&ano=${encodeURIComponent(ano)}&municipio=${encodeURIComponent(municipio)}&cargo=${encodeURIComponent(cargo)}`;
    out.innerHTML += `
      <div class="tse-toolbar">
        <a class="btn-outline" href="${excelUrl}" download>⬇ Baixar Excel</a>
      </div>`;

    // Eleitos
    if (eleitos.length) out.innerHTML += renderTabela(eleitos, 'Eleitos');

    // Demais
    if (nao_eleitos.length) {
      out.innerHTML += `
        <details>
          <summary>Demais candidatos (${nao_eleitos.length})</summary>
          ${renderTabela(nao_eleitos, '')}
        </details>`;
    }
  } catch (err) {
    out.innerHTML = '';
    out.appendChild(callout(err.message, 'erro'));
  }
});

// ── Aba: Rastrear ─────────────────────────────────────────────────────────────

function renderTimeline(data) {
  const anoAtual = new Date().getFullYear();

  // Unifica eleitos, suplentes e não eleitos numa só linha do tempo (decrescente).
  const eventos = [];
  data.mandatos.forEach(m => eventos.push({
    tipo: 'eleito', ano: m.ano_eleicao, partido: m.partido,
    sq: m.sq_candidato, cdMun: m.cd_municipio,
    inicio: m.inicio, fim: m.fim, reeleicao: m.reeleicao,
    atual: anoAtual >= m.inicio && anoAtual <= m.fim,
  }));
  data.suplencias.forEach(s => eventos.push({
    tipo: 'suplente', ano: s.ano, partido: s.partido,
    sq: s.sq_candidato, cdMun: s.cd_municipio, situacao: 'Suplente',
  }));
  data.sem_eleicao.forEach(s => eventos.push({
    tipo: 'naoel', ano: s.ano, partido: s.partido,
    sq: s.sq_candidato, cdMun: s.cd_municipio, situacao: s.situacao || 'Não eleito',
  }));

  if (!eventos.length) return '<div class="tse-callout tse-callout-info">Nenhum registro encontrado.</div>';
  eventos.sort((a, b) => b.ano - a.ano);

  const items = eventos.map(ev => {
    const partidoHtml = ev.partido ? `<span class="tse-tl-partido">${ev.partido}</span>` : '';
    const tseHref = tseCandidatoUrl(ev.ano, ev.sq, ev.cdMun);
    const tseLink = tseHref ? `
      <div class="tse-tl-confirm">
        <a href="${tseHref}" target="_blank" rel="noopener">🔗 Ver ficha no TSE</a>
      </div>` : '';

    if (ev.tipo === 'eleito') {
      const reeleicaoHtml = ev.reeleicao ? `&nbsp;${badge('Reeleição', 'reeleicao')}` : '';
      const atualHtml = ev.atual ? `&nbsp;${badge('Mandato atual', 'atual')}` : '';
      return `
        <div class="tse-tl-item">
          <div class="tse-tl-card${ev.atual ? ' tse-tl-card-atual' : ''}">
            <div class="tse-tl-ano">Eleição ${ev.ano}${reeleicaoHtml}${atualHtml}</div>
            <div class="tse-tl-row">${partidoHtml}<span class="tse-tl-periodo">${ev.inicio}&ndash;${ev.fim}</span></div>
            ${tseLink}
          </div>
        </div>`;
    }

    // Suplente ou não eleito — card secundário, sem período de mandato
    // Para candidaturas com restrição (indeferido/cassado/etc.), placeholder
    // para os motivos, carregados depois via API (ver carregarMotivos).
    const ehRestricao = ev.tipo === 'naoel' && !/^(n[ãa]o eleito|sem )/i.test(ev.situacao || '');
    const motivosPh = (ehRestricao && ev.sq && ev.cdMun)
      ? `<div class="tse-tl-motivos" data-ano="${ev.ano}" data-mun="${ev.cdMun}" data-sq="${ev.sq}"></div>` : '';
    return `
      <div class="tse-tl-item tse-tl-item-${ev.tipo}">
        <div class="tse-tl-card tse-tl-card-sec">
          <div class="tse-tl-ano tse-tl-ano-sec">Eleição ${ev.ano}&nbsp;${badge(ev.situacao, ev.tipo)}</div>
          ${partidoHtml ? `<div class="tse-tl-row">${partidoHtml}</div>` : ''}
          ${motivosPh}
          ${tseLink}
        </div>
      </div>`;
  }).join('');
  return `<div class="tse-timeline">${items}</div>`;
}

// Busca os motivos das candidaturas com restrição e injeta nos cards.
async function carregarMotivos() {
  const els = [...document.querySelectorAll('.tse-tl-motivos[data-sq]')];
  await Promise.all(els.map(async el => {
    try {
      const f = await apiFetch({ action: 'ficha', ano: el.dataset.ano, municipio: el.dataset.mun, sq: el.dataset.sq });
      if (f.motivos && f.motivos.length) {
        el.innerHTML = `<div class="tse-motivos">${f.motivos.map(m => `<span class="tse-motivo">${m}</span>`).join('')}</div>`;
      }
    } catch { /* silencioso — o badge da situação já está no card */ }
  }));
}

// ── Patrimônio / evolução patrimonial ──────────────────────────────────────────

function formatCpf(cpf) {
  const s = String(cpf).replace(/\D/g, '').padStart(11, '0');
  return `${s.slice(0, 3)}.${s.slice(3, 6)}.${s.slice(6, 9)}-${s.slice(9)}`;
}

function formatBRL(v) {
  if (v == null) return '—';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v);
}

function fotoUrl(ano, sq, cdMun) {
  const cd = _TSE_CD[ano];
  return (cd && sq && cdMun) ? `${_TSE_BASE}rest/arquivo/img/${cd}/${sq}/${cdMun}` : '';
}

function temRestricao(f) {
  return (f.motivos && f.motivos.length) || (f.situacao_registro && f.situacao_registro !== 'Deferido');
}

function renderFicha(fichas) {
  const fs = [...fichas].sort((a, b) => a.ano - b.ano);

  // Resumo de restrições (indeferida / cassada / etc.) com os motivos
  const restricoes = fs.filter(temRestricao);
  let alertaHtml = '';
  if (restricoes.length) {
    const itens = restricoes.map(f => {
      const mot = (f.motivos && f.motivos.length) ? `: ${f.motivos.join('; ')}` : '';
      return `&bull; <strong>${f.ano}</strong> — ${f.situacao_registro || 'Com restrição'}${mot}`;
    }).join('<br>');
    alertaHtml = `<div class="tse-callout tse-callout-warn"><strong>⚠ Candidatura(s) com restrição</strong><br>${itens}</div>`;
  }

  let prev = null;
  const linhas = fs.map(f => {
    let deltaHtml = '';
    if (prev != null && prev > 0 && f.total_bens != null) {
      const pct = Math.round((f.total_bens - prev) / prev * 100);
      const salto = pct >= 100;
      deltaHtml = `<span class="tse-delta${salto ? ' tse-delta-salto' : ''}">${pct >= 0 ? '+' : ''}${pct}%${salto ? ' ⚠' : ''}</span>`;
    }
    if (f.total_bens != null) prev = f.total_bens;

    const valorTxt = f.total_bens != null
      ? formatBRL(f.total_bens)
      : (f.divulga_bens === false ? 'Não divulgado' : 'Não declarou bens');

    let sitHtml = '';
    if (temRestricao(f)) {
      const sit = `${f.situacao_registro || 'Com restrição'}${f.situacao_candidato ? ` — ${f.situacao_candidato}` : ''}`;
      const mot = (f.motivos && f.motivos.length)
        ? `<div class="tse-motivos">${f.motivos.map(m => `<span class="tse-motivo">${m}</span>`).join('')}</div>` : '';
      sitHtml = `<div class="tse-ficha-sit">${sit}${mot}</div>`;
    }

    const bensList = f.bens.length ? `
      <details class="tse-bens">
        <summary>${f.bens.length} bem(ns) declarado(s)</summary>
        <ul>${f.bens.map(b => `<li>${b.descricao || b.tipo || '—'} &mdash; <strong>${formatBRL(b.valor)}</strong></li>`).join('')}</ul>
      </details>` : '';

    return `
      <div class="tse-pat-linha${temRestricao(f) ? ' tse-pat-linha-restr' : ''}">
        <div class="tse-pat-cab">
          <span class="tse-pat-ano">${f.ano}</span>
          <span class="tse-pat-valor">${valorTxt}</span>
          ${deltaHtml}
        </div>
        ${sitHtml}
        ${bensList}
      </div>`;
  }).join('');

  return `
    <h4 class="tse-pat-title">Ficha do candidato (situação e bens)</h4>
    ${alertaHtml}
    <div class="tse-pat">${linhas}</div>
    <p class="tse-pat-fonte">Fonte: ficha do candidato no DivulgaCandContas (TSE). Situação e bens conforme cada eleição.</p>`;
}

async function carregarPatrimonio(data, btn) {
  const panel = document.getElementById('patrimonio-out');
  btn.disabled = true;
  panel.innerHTML = '';
  panel.appendChild(spinner());
  panel.appendChild(document.createTextNode(' Consultando ficha no TSE (situação e bens)…'));

  // Candidaturas da pessoa (ano + município + sq), sem duplicatas e com sq válido
  const cands = [];
  data.mandatos.forEach(m => cands.push({ ano: m.ano_eleicao, mun: m.cd_municipio, sq: m.sq_candidato }));
  data.suplencias.forEach(s => cands.push({ ano: s.ano, mun: s.cd_municipio, sq: s.sq_candidato }));
  data.sem_eleicao.forEach(s => cands.push({ ano: s.ano, mun: s.cd_municipio, sq: s.sq_candidato }));
  const seen = new Set();
  const unicos = cands.filter(c => c.sq && c.mun && !seen.has(`${c.ano}-${c.sq}`) && seen.add(`${c.ano}-${c.sq}`));

  try {
    const fichas = await Promise.all(
      unicos.map(c => apiFetch({ action: 'ficha', ano: c.ano, municipio: c.mun, sq: c.sq }))
    );
    panel.innerHTML = renderFicha(fichas);
  } catch (err) {
    panel.innerHTML = '';
    panel.appendChild(callout('Não foi possível consultar os bens no TSE agora. Tente novamente em instantes.', 'erro'));
    btn.disabled = false;
  }
}

document.getElementById('form-rastrear').addEventListener('submit', async e => {
  e.preventDefault();
  const municipio = document.getElementById('municipio-rastrear').value;
  const cargo = document.getElementById('cargo-rastrear').value;
  const nome = document.getElementById('nome-rastrear').value.trim();
  const out = document.getElementById('resultado-rastrear');

  if (!nome) {
    out.innerHTML = '';
    out.appendChild(callout('Informe ao menos parte do nome.', 'warn'));
    return;
  }

  out.innerHTML = '';
  const sp = spinner();
  out.appendChild(sp);
  out.appendChild(document.createTextNode(' Rastreando…'));

  try {
    const data = await apiFetch({ action: 'rastrear', nome, municipio, cargo });
    out.innerHTML = '';

    // Homônimos — reforçado por CPFs distintos
    const multiNomes = data.homonimos && data.homonimos.length > 1;
    if (multiNomes || data.cpfs_distintos > 1) {
      let msg = `<strong>Múltiplos candidatos encontrados</strong> — use o nome completo para refinar.`;
      if (data.cpfs_distintos > 1) msg += `<br><small>Detectados ${data.cpfs_distintos} CPFs distintos nos resultados.</small>`;
      if (multiNomes) msg += `<br><br>${data.homonimos.map(n => `&bull; ${n}`).join('<br>')}`;
      out.appendChild(callout(msg, 'warn'));
    }

    if (!data.mandatos.length && !data.suplencias.length && !data.sem_eleicao.length) {
      out.appendChild(callout(`Nenhum registro encontrado para <strong>${nome}</strong> em ${municipio} / ${cargo}.`, 'info'));
      return;
    }

    // Cabeçalho: foto (candidatura mais recente) + CPF
    const todas = [
      ...data.mandatos.map(m => ({ ano: m.ano_eleicao, mun: m.cd_municipio, sq: m.sq_candidato })),
      ...data.suplencias.map(s => ({ ano: s.ano, mun: s.cd_municipio, sq: s.sq_candidato })),
      ...data.sem_eleicao.map(s => ({ ano: s.ano, mun: s.cd_municipio, sq: s.sq_candidato })),
    ].filter(c => c.sq && c.mun).sort((a, b) => b.ano - a.ano);
    const foto = todas.length ? fotoUrl(todas[0].ano, todas[0].sq, todas[0].mun) : '';
    if (foto || data.cpf) {
      out.innerHTML += `
        <div class="tse-ficha-head">
          ${foto ? `<img class="tse-foto" src="${foto}" alt="Foto do candidato" onerror="this.style.display='none'">` : ''}
          ${data.cpf ? `<span class="tse-cpf">CPF: <strong>${formatCpf(data.cpf)}</strong></span>` : ''}
        </div>`;
    }

    // Timeline unificada (eleito / suplente / não eleito)
    out.innerHTML += `<h3 class="tse-subhead">Linha do tempo de candidaturas</h3>`;
    out.innerHTML += renderTimeline(data);

    // Ficha (situação + bens) — sob demanda
    out.innerHTML += `
      <div class="tse-patrimonio-wrap">
        <button type="button" class="btn-outline" id="btn-patrimonio">📋 Ver ficha (situação + bens)</button>
        <div id="patrimonio-out"></div>
      </div>`;
    const btnPat = document.getElementById('btn-patrimonio');
    if (btnPat) btnPat.addEventListener('click', () => carregarPatrimonio(data, btnPat));

    // Motivos das candidaturas com restrição, direto nos cards da timeline
    carregarMotivos();
  } catch (err) {
    out.innerHTML = '';
    out.appendChild(callout(err.message, 'erro'));
  }
});
