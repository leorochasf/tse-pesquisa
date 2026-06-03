/**
 * Ferramenta TSE — cliente web.
 * Toda comunicação com o backend via fetch() para /api/index.
 */

const API = '/api/index';

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
  const map = { eleito: 'badge-eleito', suplente: 'badge-suplente', naoel: 'badge-naoel', reeleicao: 'badge-reeleicao' };
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

    // aba Listar
    const selAno = document.getElementById('ano-listar');
    populateSelect(selAno, [...anos].reverse());

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
  const rows = candidatos.map(c => `
    <tr>
      <td>${c.nome}</td>
      <td>${c.urna || ''}</td>
      <td>${c.partido || ''}</td>
      <td>${situacaoBadge(c.situacao)}</td>
    </tr>`).join('');
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

function renderTimeline(mandatos) {
  if (!mandatos.length) return '<div class="tse-callout tse-callout-info">Nenhum mandato registrado.</div>';
  const items = mandatos.map(m => {
    const reeleicaoHtml = m.reeleicao ? `&nbsp;${badge('Reeleição', 'reeleicao')}` : '';
    const partidoHtml = m.partido ? `<span class="tse-tl-partido">${m.partido}</span>` : '';
    return `
      <div class="tse-tl-item">
        <div class="tse-tl-card">
          <div class="tse-tl-ano">Eleição ${m.ano_eleicao}${reeleicaoHtml}</div>
          <div class="tse-tl-row">${partidoHtml}<span class="tse-tl-periodo">${m.inicio}&ndash;${m.fim}</span></div>
        </div>
      </div>`;
  }).join('');
  return `<div class="tse-timeline">${items}</div>`;
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

    // Homônimos
    if (data.homonimos && data.homonimos.length > 1) {
      const nomes = data.homonimos.map(n => `&bull; ${n}`).join('<br>');
      out.appendChild(callout(
        `<strong>Múltiplos candidatos encontrados</strong> — use o nome completo para refinar:<br><br>${nomes}`,
        'warn'
      ));
    }

    if (!data.mandatos.length && !data.suplencias.length && !data.sem_eleicao.length) {
      out.appendChild(callout(`Nenhum registro encontrado para <strong>${nome}</strong> em ${municipio} / ${cargo}.`, 'info'));
      return;
    }

    // Timeline
    out.innerHTML += `<h3 class="tse-subhead">Linha do tempo de mandatos</h3>`;
    out.innerHTML += renderTimeline(data.mandatos);

    // Suplências
    if (data.suplencias.length) {
      const rows = data.suplencias.map(s => `<tr><td>${s.ano}</td><td>${s.partido || ''}</td></tr>`).join('');
      out.innerHTML += `
        <details>
          <summary>Suplências (${data.suplencias.length})</summary>
          <div class="tse-table-wrap">
            <table>
              <thead><tr><th>Ano</th><th>Partido</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </details>`;
    }

    // Não eleito
    if (data.sem_eleicao.length) {
      const rows = data.sem_eleicao.map(s => `<tr><td>${s.ano}</td><td>${s.situacao}</td><td>${s.partido || ''}</td></tr>`).join('');
      out.innerHTML += `
        <details>
          <summary>Não eleito (${data.sem_eleicao.length})</summary>
          <div class="tse-table-wrap">
            <table>
              <thead><tr><th>Ano</th><th>Situação</th><th>Partido</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </details>`;
    }
  } catch (err) {
    out.innerHTML = '';
    out.appendChild(callout(err.message, 'erro'));
  }
});
