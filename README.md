# Ferramenta TSE

Consulta de eleitos, suplentes e mandatos municipais de Goiás a partir dos dados abertos do TSE.

---

## Como usar (assessores)

Acesse o link abaixo — não precisa instalar nada:

**[https://tse-pesquisa-nx9ugomzvysocnqzty96g6.streamlit.app](https://tse-pesquisa-nx9ugomzvysocnqzty96g6.streamlit.app)**

### Pesquisar eleitos de um município

1. Selecione o **Ano** da eleição (ex: 2024)
2. Selecione o **Município** (ex: INACIOLÂNDIA)
3. Selecione o **Cargo** (Vereador ou Prefeito)
4. Clique em **Pesquisar**
5. Os eleitos aparecem destacados na tabela
6. Clique em **⬇️ Baixar Excel** para exportar

### Rastrear mandatos de uma pessoa

1. Clique em **Rastrear mandatos**
2. Selecione o **Município** e o **Cargo**
3. Digite o **Nome** (parcial ou completo, ex: CLAUDIO HENRIQUE)
4. Clique em **Rastrear**
5. A linha do tempo mostra cada eleição, partido, período do mandato e se houve reeleição

> Se aparecer um aviso de "múltiplos candidatos", use o nome completo para refinar.

---

## Atualizar os dados (admin)

Os dados cobrem as eleições de **2016, 2020 e 2024**. Para importar um ano novo:

1. Abra a **barra lateral** (seta `>` no canto superior esquerdo)
2. Digite a senha de admin
3. Selecione o ano e clique em **⬆️ Atualizar dados do TSE**
4. O download do TSE leva alguns minutos; ao finalizar, os dados ficam disponíveis para todos

---

## Estrutura do projeto (desenvolvedores)

```
FerramentaTSE/
├─ tse_core/           # Motor de consulta
│  ├─ db.py            # SQLite + suporte a TSE_DB_PATH
│  ├─ ingest.py        # Download e importação dos CSVs do TSE
│  ├─ consulta.py      # listar(), rastrear(), listar_municipios(), listar_anos()
│  ├─ mandato.py       # Inferência de mandatos e reeleição
│  ├─ export.py        # gerar_excel() → bytes
│  └─ dados/cargos.py  # Mapa código↔nome de cargo
├─ app.py              # App Streamlit (web)
├─ cli.py              # CLI: ingest / listar / rastrear
├─ scripts/
│  └─ seed_storage.py  # Upload inicial do sqlite para o Supabase Storage
├─ .streamlit/
│  └─ secrets.toml     # Credenciais locais (não versionado)
├─ requirements.txt
└─ docs/               # Planos de implementação
```

### Rodar localmente

```bash
pip install -r requirements.txt
python cli.py ingest --anos 2024
streamlit run app.py
```

### Etapas concluídas

| Etapa | Descrição |
|-------|-----------|
| 0–5 | Motor tse_core + CLI (ingest, listar, rastrear, mandatos) |
| 7.0 | Refatorações para web (TSE_DB_PATH, export.py, listar_municipios/anos) |
| 7.1 | App Streamlit — modo Listar |
| 7.2 | App Streamlit — modo Rastrear |
| 7.3 | Persistência via Supabase Storage + botão Atualizar |
| 7.4 | Deploy no Streamlit Community Cloud |
| 7.5 | Documentação |

### Fonte dos dados

TSE Dados Abertos — `consulta_cand`:
`https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_AAAA.zip`
