# Ferramenta TSE — consulta de eleitos e inferência de mandatos

## Context

O usuário (assessor jurídico MPGO/AJE) precisa hoje consultar manualmente o site
`divulgacandcontas.tse.jus.br` (uma SPA Angular) clicando por vários menus
(pleito → região → estado → município → cargo → pesquisar) só para descobrir se
um candidato foi **eleito / suplente / não eleito** — dado de que ele precisa
para inferir **início e fim de mandato** de prefeitos e vereadores, e se houve
reeleição. Repetir isso eleição a eleição é lento e repetitivo.

**Objetivo:** automatizar essa consulta. Entregar **dois produtos sobre um mesmo
motor**:
1. **Skill `/tse`** integrada ao AssessorIA (uso conversacional do próprio usuário, só municipais GO).
2. **MVP Python independente (CLI)** que depois vira ferramenta para os outros
   assessores — começa só municipais GO, mas **arquitetado para escalar a qualquer UF/cargo**.

Ambos os modos de consulta: **(a) listar** por município+cargo+ano (igual ao site)
e **(b) rastrear uma pessoa** pelo nome ao longo das eleições → mandatos automáticos.

## Decisão técnica central — fonte de dados

Descartamos automação de navegador (frágil). Duas fontes de dados possíveis:

| Fonte | Avaliação |
|-------|-----------|
| **API REST do site** (`/divulga/rest/v1/...`, não-oficial) | Existe e é usada pela SPA, mas é não-documentada, sem CORS (só serve server-side) e nos meus testes o endpoint `/candidatura/listar/...` voltou `candidatos: []` mesmo com parâmetros plausíveis — risco de instabilidade. |
| **TSE Dados Abertos — `consulta_cand`** (CSV oficial) ✅ **escolhida** | Oficial, completa, estável, sem limite de requisições, offline. Um ZIP por ano de eleição (`https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_AAAA.zip`) contém CSV por UF. Já traz **tudo**: `DS_SIT_TOT_TURNO` (ELEITO / ELEITO POR QP / ELEITO POR MÉDIA / SUPLENTE / NÃO ELEITO / 2º TURNO), `CD_MUNICIPIO`+`NM_UE`, `CD_CARGO`+`DS_CARGO`, `NM_CANDIDATO`, `NM_URNA_CANDIDATO`, `SG_PARTIDO`, `ANO_ELEICAO`. |

**Backbone:** baixar os CSVs `consulta_cand` (filtrando GO), importar para **SQLite
local** e consultar por SQL. Isso resolve os dois modos como queries triviais,
torna o rastreamento entre eleições um `WHERE nome LIKE ... GROUP BY ano`, e escala
para qualquer UF/cargo apenas importando mais linhas. A API REST fica como
*enhancement* futuro documentado (consulta "ao vivo"), não no caminho crítico.

> Para o caso de uso (mandatos históricos), o dado "final" do CSV é o ideal —
> a API "ao vivo" só importaria durante a apuração de uma eleição em curso.

## Arquitetura — motor compartilhado + 2 frontends

```
FerramentaTSE/
├─ tse_core/                 # MOTOR reusável (skill e CLI dependem dele)
│  ├─ ingest.py             # baixa consulta_cand_AAAA.zip, extrai CSV da UF, popula SQLite
│  ├─ db.py                 # conexão SQLite + schema + índices
│  ├─ consulta.py           # listar() e rastrear() — regras de negócio puras
│  ├─ mandato.py            # inferência início/fim de mandato + reeleição
│  └─ dados/
│     ├─ cargos.py          # mapa código↔nome (11=Prefeito, 13=Vereador, ...)
│     └─ tse.sqlite         # base gerada (gitignore; recriável via ingest)
├─ cli.py                    # MVP externo: argparse + exportação Excel/CSV
├─ requirements.txt          # requests, openpyxl (ou pandas), nada exótico
└─ README.md                 # como rodar o ingest e as consultas
```

A **skill `/tse`** (SKILL.md no diretório de skills do AssessorIA) é uma camada fina:
interpreta o pedido em linguagem natural, resolve município/cargo/ano (defaults GO),
chama as funções de `tse_core`, e devolve resposta em markdown — opcionalmente
salvando em `contexto/` no padrão do projeto.

### Schema SQLite (tabela única `candidatura`)
Colunas mínimas: `ano`, `uf`, `cd_municipio`, `nm_municipio`, `cd_cargo`,
`ds_cargo`, `nr_cpf` (quando disponível), `nm_candidato`, `nm_urna`, `sg_partido`,
`situacao_turno` (de `DS_SIT_TOT_TURNO`). Índices em (`ano`,`cd_municipio`,`cd_cargo`)
e em `nm_candidato` para o rastreamento por nome.

## Componentes

### 1. `tse_core/ingest.py`
- Baixa o ZIP do ano pedido, extrai apenas `consulta_cand_AAAA_GO.csv` (encoding
  `latin-1`, separador `;`), filtra colunas relevantes e faz `INSERT` no SQLite.
- Idempotente: limpa o ano antes de reimportar. Aceita lista de anos.
- Para escalar: parâmetro `uf` (default `GO`) — só trocar o CSV extraído.

### 2. `tse_core/consulta.py`
- `listar(ano, municipio, cargo) -> list[dict]`: resolve nome→código de município
  (busca case/acento-insensível em `nm_municipio`) e nome→código de cargo, e
  retorna candidatos com situação. Espelha a tela do site.
- `rastrear(nome, municipio, cargo, anos=None) -> dict`: para cada ano disponível,
  encontra a pessoa (match por `nm_candidato`/`nm_urna`, normalizado) e registra a
  situação. Lida com homônimos retornando candidatos distintos para o usuário
  desambiguar.

### 3. `tse_core/mandato.py`
- Regra: mandato municipal = 4 anos, posse em 1º/jan do ano seguinte à eleição.
  `ELEITO` (e variantes "POR QP/POR MÉDIA") em `X` → **mandato `X+1` a `X+4`**.
  Ex.: eleito 2020 → 2021–2024; eleito 2024 → 2025–2028.
- A partir do resultado de `rastrear`, monta a linha do tempo: períodos de mandato,
  marca **reeleição** (eleito em eleições consecutivas) e identifica em qual eleição
  o mandato terminou (última vitória sem vitória seguinte). Suplentes são sinalizados
  separadamente (não geram mandato inferido).

### 4. `cli.py` (MVP externo)
- `python cli.py listar --municipio "Inaciolândia" --cargo vereador --ano 2024 [--excel saida.xlsx]`
- `python cli.py rastrear --nome "Fulano" --municipio "Inaciolândia" --cargo vereador`
- `python cli.py ingest --anos 2016 2020 2024`
- Exportação Excel/CSV reproduz o "exportar" do site. Saída de tabela legível no terminal.

### 5. Skill `/tse`
- SKILL.md descrevendo gatilhos (consulta TSE, eleito, mandato, reeleição) e
  instruções para chamar `tse_core` via Bash, com defaults GO + municipais, e
  formatar a resposta. Reusa o mesmo motor — zero duplicação de lógica.

## Escalabilidade futura (sem reescrever)
- **Outras UFs:** parâmetro `uf` no ingest; CSV por estado já existe no mesmo ZIP.
- **Cargos estaduais/federais (eleições gerais):** mesma tabela; `cd_cargo` 1–8
  (Presidente, Governador, Senador, Dep. Federal/Estadual...). Mandatos: 4 anos
  (deputados/governador) ou 8 (senador) — `mandato.py` recebe a regra por cargo.
- **API ao vivo (opcional):** adicionar um `tse_core/api.py` que implementa a mesma
  interface de `consulta.py` contra `/divulga/rest/v1`, selecionável por flag.

## Verificação (end-to-end)
1. `python cli.py ingest --anos 2024` → confirma que `tse.sqlite` é criado e tem
   linhas de GO (`SELECT COUNT(*) ... WHERE uf='GO'`).
2. `python cli.py listar --municipio "Inaciolândia" --cargo vereador --ano 2024`
   → comparar a lista (nomes, partidos, eleitos/suplentes) com o resultado manual
   no site para o mesmo município — **deve bater 1:1**. Conferir o `--excel`.
3. `python cli.py rastrear --nome "<prefeito conhecido>" --municipio "<cidade>" --cargo prefeito`
   após `ingest --anos 2016 2020 2024` → conferir períodos de mandato e flag de
   reeleição contra o histórico real.
4. Skill: `/tse <pergunta em linguagem natural>` → resposta coerente com o CLI.

## Premissas / pontos a confirmar na execução
- Nomes exatos das colunas serão validados contra o "Leia-me" do dataset no primeiro
  `ingest` (o leiaute `consulta_cand` é estável, mas variações por ano existem).
- Local de instalação da skill `/tse` no AssessorIA (diretório de skills) a confirmar.
- Tamanho do download: ZIP é nacional (~dezenas de MB); extraímos só o CSV da UF.
- Homônimos no rastreamento: MVP devolve candidatos distintos para desambiguação
  manual (sem tentar adivinhar identidade).

---

# Plano de implementação por etapas (sessões independentes)

Cada etapa é autocontida, executável em uma sessão separada, e termina num estado
**verificável** (critério "Pronto quando"). As etapas são sequenciais: cada uma
assume que a anterior está concluída.

> Convenção de progresso: marcar cada etapa com ✅ ao concluir, no topo da própria
> etapa, para a sessão seguinte saber onde retomar.

## Etapa 0 ✅ — Scaffolding e base de dados
**Objetivo:** estrutura do projeto + schema SQLite, sem dados ainda.

## Etapa 1 — Ingest do CSV oficial do TSE
**Objetivo:** popular o SQLite com os candidatos de GO de um ano.
- `tse_core/ingest.py`: baixa `consulta_cand_AAAA.zip` (cache local), extrai
  `consulta_cand_AAAA_GO.csv` (`latin-1`, `;`), mapeia colunas relevantes e faz
  `INSERT` em lote. Idempotente (limpa o ano antes). Parâmetro `uf='GO'` (default).
- Primeiro passo da sessão: validar nomes de colunas contra o "Leia-me" do dataset
  e ajustar o mapeamento se o ano variar.
- **Verificação:** `python cli.py ingest --anos 2024` →
  `SELECT COUNT(*) FROM candidatura WHERE uf='GO' AND ano=2024` retorna > 0;
  conferir alguns valores de `situacao_turno` (ELEITO/SUPLENTE/...).
- **Pronto quando:** base de 2024/GO carregada e inspecionável.

## Etapa 2 — Consulta "listar" (núcleo)
**Objetivo:** modo lista igual ao site, como função pura.
- `tse_core/consulta.py`: `listar(ano, municipio, cargo)` com resolução
  nome→código de município (match sem acento/caixa em `nm_municipio`) e de cargo.
  Retorna candidatos (nome, urna, partido, situação) ordenados.
- **Verificação:** `listar(2024, "Inaciolândia", "vereador")` comparado **1:1** com
  a busca manual no site (mesmos nomes, partidos, eleitos/suplentes).
- **Pronto quando:** resultado bate com o site para ≥1 município de teste.

## Etapa 3 — CLI "listar" + exportação Excel/CSV
**Objetivo:** primeiro entregável usável do MVP externo.
- `cli.py` (argparse): subcomando `listar --municipio --cargo --ano [--excel arq.xlsx]`
  + comando `ingest`. Tabela legível no terminal; exportação com `openpyxl`.
- **Verificação:** rodar `listar` para Inaciolândia/Vereador/2024 no terminal e gerar
  `.xlsx` — abrir e conferir conteúdo equivalente ao "exportar" do site.
- **Pronto quando:** assessor externo consegue rodar e exportar sem tocar em código.

## Etapa 4 — Rastrear pessoa + inferência de mandato
**Objetivo:** o caso de uso final (início/fim de mandato, reeleição).
- Ampliar ingest: `python cli.py ingest --anos 2016 2020 2024`.
- `consulta.rastrear(nome, municipio, cargo, anos=None)`: encontra a pessoa por ano
  (normalização de nome; homônimos retornados para desambiguação).
- `tse_core/mandato.py`: regra municipal (4 anos, posse em X+1); monta timeline,
  marca reeleição e fim de mandato; sinaliza suplentes (sem inferir mandato).
- `cli.py`: subcomando `rastrear --nome --municipio --cargo`.
- **Verificação:** rastrear um prefeito conhecido em 2016/2020/2024 → períodos e
  flag de reeleição conferem com o histórico real.
- **Pronto quando:** timeline de mandatos correta para ≥1 pessoa de teste.

## Etapa 5 ✅ — Skill `/tse` no AssessorIA
**Objetivo:** camada conversacional sobre o mesmo motor (só GO/municipais).
- Confirmar diretório de skills do AssessorIA; criar `SKILL.md` com gatilhos
  (consulta TSE, eleito, mandato, reeleição), defaults GO+municipais, e instruções
  para chamar `tse_core` via Bash e formatar resposta em markdown (opção de salvar
  em `contexto/`).
- **Verificação:** `/tse <pergunta natural>` (ex.: "fulano de Inaciolândia foi
  reeleito vereador?") devolve resposta coerente com o CLI.
- **Pronto quando:** skill responde corretamente reusando o motor (zero lógica duplicada).

## Etapa 6 — (Futuro, fora do MVP) Escalabilidade
Documentada, não implementada agora: parâmetro `uf` no ingest p/ outras UFs;
cargos de eleições gerais (1–8) com regras de mandato por cargo em `mandato.py`;
`tse_core/api.py` opcional para consulta "ao vivo" via REST com a mesma interface.

---

# Etapa 7 — Distribuição web para assessores leigos

## Context
Etapas 0–5 entregaram o motor (`tse_core`) + CLI + skill, mas hoje usar a
ferramenta exige Python instalado e linha de comando — inviável para os outros
assessores da AJE. Objetivo desta etapa: **um link web que qualquer assessor abre
no navegador, sem instalar nada**, escolhe município/cargo/ano em menus, vê os
eleitos e baixa Excel — economizando o trabalho manual no site do TSE.

**Decisões (confirmadas com o usuário):**
- App **web com link público** (dados são públicos do TSE; sem login).
- Hospedagem: **Streamlit Community Cloud** (grátis, reaproveita todo o `tse_core`).
- **Botão "Atualizar dados" dentro da ferramenta**, protegido por senha (só admin).

## Arquitetura
- **Frontend + compute:** `app.py` (Streamlit) reusa `tse_core` (consulta/mandato/ingest).
- **Persistência:** Streamlit Cloud tem disco efêmero → o arquivo `tse.sqlite` vive
  no **Supabase Storage** (bucket `tse-data`). É a fonte única dos dados.
  - No boot, o app baixa o `.sqlite` do Storage para `/tmp` e aponta o `tse_core` p/ lá.
  - O botão "Atualizar" roda o ingest no working copy e **reenvia** o `.sqlite` ao Storage.
- **Repo = só código** (o `.sqlite` continua gitignored; dados ficam no Supabase).
  Atualizações são raras (eleição municipal a cada 2 anos), então sincronização por
  arquivo é suficiente — sem necessidade de migrar para Postgres.

## Refatorações no motor (pequenas, reusáveis pelo CLI também)
1. **`tse_core/db.py`** — respeitar `TSE_DB_PATH` (env var) para sobrescrever o
   caminho padrão do `.sqlite`. Permite o app apontar para o working copy em `/tmp`.
2. **`tse_core/export.py` (novo)** — extrair `gerar_excel(candidatos) -> bytes`
   (escreve em `BytesIO`) a partir do `_exportar_excel` hoje em `cli.py`; o `cli.py`
   passa a reusar essa função. Permite o `st.download_button` no app.
3. **`tse_core/consulta.py`** — adicionar `listar_municipios(uf, ano=None)` e
   `listar_anos(uf)` (mesmo padrão de conexão de `_resolver_municipio`). Alimentam
   os **menus suspensos** do app — leigo escolhe da lista, eliminando o problema de
   grafia/"município ambíguo".

## `app.py` (Streamlit)
- Cabeçalho curto + instrução de uso.
- Seletor de modo: **Listar candidatos** | **Rastrear pessoa**.
  - *Listar:* selectbox Ano + selectbox Município (lista GO) + selectbox Cargo
    (Prefeito/Vereador) → tabela (`st.dataframe`, eleitos destacados) +
    `st.download_button("Baixar Excel")` usando `gerar_excel`.
  - *Rastrear:* Município + Cargo + Nome → linha do tempo de mandatos/reeleição
    reusando `consulta.rastrear` + `mandato.inferir_mandatos`/`formatar_linha_do_tempo`.
    Avisar homônimos.
- **Sidebar admin:** campo de senha (compara com `st.secrets["ADMIN_PASSWORD"]`);
  se correta, exibe "Atualizar dados do TSE" + input de ano → chama
  `ingest.importar(ano)` → reenvia `.sqlite` ao Supabase Storage. Mostra spinner
  e "última atualização".
- **Sync de boot:** baixar `.sqlite` do Storage (se existir) → `/tmp/tse.sqlite`;
  setar `TSE_DB_PATH`. Cachear com `st.cache_resource`.

## Dependências e segredos
- `requirements.txt`: adicionar `streamlit` e `supabase` (cliente p/ Storage).
- `.streamlit/secrets.toml` (local, gitignored) e **Secrets do Streamlit Cloud**:
  `SUPABASE_URL`, `SUPABASE_KEY` (service role, p/ upload), `ADMIN_PASSWORD`.

## Deploy (passo a passo)
1. Criar bucket `tse-data` no Supabase e **subir o `tse.sqlite` atual** (seed inicial).
2. `git init` + repo **público** no GitHub (só código; `.sqlite`, `cache/`,
   `.streamlit/secrets.toml` gitignored).
3. Conectar o repo no **Streamlit Community Cloud**, app file `app.py`,
   preencher os Secrets → publica e gera o **link público**.
4. Compartilhar o link com os assessores. (Nota: apps grátis "dormem" após
   inatividade; o primeiro acesso acorda em ~30s.)

## Verificação (end-to-end)
1. **Local:** `streamlit run app.py` → modo Listar para Inaciolândia/Vereador/2024
   mostra os 9 eleitos e o botão baixa um `.xlsx` correto.
2. **Rastrear local:** "CLAUDIO HENRIQUE" / Inaciolândia / Prefeito → mostra
   reeleição 2020→2024 (mesma saída do CLI).
3. **Persistência:** com senha, clicar "Atualizar dados" para um ano de teste →
   confirmar que o `.sqlite` foi reenviado ao Supabase Storage e que, após
   reiniciar o app, os dados continuam lá.
4. **Público:** abrir o link do Streamlit Cloud em uma aba anônima (sem login) →
   pesquisar funciona; a seção "Atualizar" só aparece/age com a senha correta.

## Entrega final
Registrar a Etapa 7 e o link público no `README.md` e adicionar uma seção curta
"Como usar (assessores)" em linguagem não-técnica.
