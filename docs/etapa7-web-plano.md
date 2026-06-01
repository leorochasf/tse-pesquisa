# Etapa 7 — Distribuição web (plano detalhado por sessões)

> Documento complementar ao `docs/plano.md`. Divide a Etapa 7 em sub-etapas
> autocontidas, cada uma executável em uma sessão separada e com critério
> **"Pronto quando"** verificável. São sequenciais.

## Contexto resumido
Transformar a ferramenta (motor `tse_core` + CLI já prontos nas Etapas 0–5) em um
**app web com link público**, que qualquer assessor da AJE abre no navegador sem
instalar nada. Hospedagem: **Streamlit Community Cloud** (grátis). Persistência dos
dados: **Supabase Storage** (guarda o `tse.sqlite`). Botão "Atualizar dados" dentro
da ferramenta, protegido por senha.

> Convenção de progresso: marcar cada sub-etapa com ✅ ao concluir.

---

## ✅ Etapa 7.0 — Refatorações no motor (preparação)
**Objetivo:** preparar o `tse_core` para ser consumido pelo app, sem quebrar o CLI.
- `tse_core/db.py`: respeitar `TSE_DB_PATH` (env var) para sobrescrever o caminho
  padrão do `.sqlite`.
- `tse_core/export.py` (novo): extrair `gerar_excel(candidatos) -> bytes` (escreve
  em `BytesIO`) a partir do `_exportar_excel` de `cli.py`; `cli.py` passa a reusar.
- `tse_core/consulta.py`: adicionar `listar_municipios(uf, ano=None)` e
  `listar_anos(uf)` (mesmo padrão de `_resolver_municipio`).
- **Verificação:**
  - `python cli.py listar --municipio "Inaciolandia" --cargo vereador --ano 2024 --excel teste.xlsx`
    ainda funciona e gera o Excel (agora via `gerar_excel`).
  - `python -c "from tse_core.consulta import listar_municipios, listar_anos; print(listar_anos('GO')); print(len(listar_municipios('GO')))"`
    → retorna anos importados e ~246 municípios.
- **Pronto quando:** CLI intacto + novos helpers retornando dados corretos.

---

## ✅ Etapa 7.1 — App Streamlit local: modo "Listar"
**Objetivo:** primeira tela funcional rodando localmente.
- `requirements.txt`: adicionar `streamlit`.
- `app.py`: cabeçalho + seletor de modo (Listar | Rastrear) + bloco **Listar**:
  selectbox Ano (`listar_anos`), selectbox Município (`listar_municipios`),
  selectbox Cargo (Prefeito/Vereador) → `st.dataframe` (eleitos destacados) +
  `st.download_button("Baixar Excel")` usando `gerar_excel`.
- **Verificação:** `streamlit run app.py` → Listar Inaciolândia/Vereador/2024
  mostra os 9 eleitos; o botão baixa um `.xlsx` correto.
- **Pronto quando:** modo Listar funciona no navegador local com dropdowns + Excel.

---

## ✅ Etapa 7.2 — App Streamlit local: modo "Rastrear"
**Objetivo:** completar a segunda funcionalidade na mesma tela.
- `app.py`: bloco **Rastrear**: selectbox Município + selectbox Cargo + text_input
  Nome → reusa `consulta.rastrear` + `mandato.inferir_mandatos` /
  `formatar_linha_do_tempo`. Exibir linha do tempo de mandatos/reeleição e avisar
  homônimos.
- **Verificação:** Rastrear "CLAUDIO HENRIQUE" / Inaciolândia / Prefeito →
  mostra reeleição 2020→2024 (mesma saída do CLI).
- **Pronto quando:** ambos os modos funcionam localmente.

---

## ✅ Etapa 7.3 — Persistência via Supabase Storage + botão "Atualizar"
**Objetivo:** dados persistentes e atualizáveis pela própria ferramenta.
- `requirements.txt`: adicionar `supabase`.
- Criar bucket `tse-data` no Supabase e subir o `tse.sqlite` atual (seed inicial).
- `app.py` — **sync de boot:** baixar `.sqlite` do Storage para `/tmp/tse.sqlite`,
  setar `TSE_DB_PATH`, cachear com `st.cache_resource`.
- `app.py` — **sidebar admin:** campo de senha (`st.secrets["ADMIN_PASSWORD"]`);
  se correta, mostra "Atualizar dados do TSE" + input de ano → `ingest.importar(ano)`
  no working copy → reenvia `.sqlite` ao Storage. Spinner + "última atualização".
- `.streamlit/secrets.toml` (local, gitignored): `SUPABASE_URL`, `SUPABASE_KEY`,
  `ADMIN_PASSWORD`.
- **Verificação:** com a senha, "Atualizar dados" para um ano de teste → confirmar
  upload ao Storage; reiniciar o app → dados continuam (vieram do Storage).
- **Pronto quando:** atualização persiste após reinício; sem senha, o botão não age.

---

## ✅ Etapa 7.4 — Deploy no Streamlit Community Cloud
**Objetivo:** link público no ar.
- `git init` + repo **público** no GitHub (só código; `.sqlite`, `cache/`,
  `.streamlit/secrets.toml` gitignored). Conferir `.gitignore`.
- Conectar o repo no Streamlit Community Cloud (app file `app.py`); preencher os
  Secrets (`SUPABASE_URL`, `SUPABASE_KEY`, `ADMIN_PASSWORD`).
- **Verificação:** abrir o link em aba anônima (sem login) → pesquisar funciona;
  seção "Atualizar" só age com a senha correta.
- **Pronto quando:** qualquer pessoa com o link usa a ferramenta pelo navegador.

---

## ✅ Etapa 7.5 — Documentação para assessores
**Objetivo:** onboarding sem fricção.
- `README.md`: registrar a Etapa 7, o link público e uma seção curta
  **"Como usar (assessores)"** em linguagem não-técnica (passo a passo com prints
  opcionais: escolher ano → município → cargo → Pesquisar → Baixar Excel).
- **Verificação:** um colega leigo consegue, só com o README + link, fazer uma
  consulta e exportar o Excel sem ajuda.
- **Pronto quando:** documentação publicada e validada com um usuário real.
