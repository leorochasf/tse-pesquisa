# Ferramenta TSE

Consulta de eleitos, suplentes e mandatos municipais de Goiás a partir dos dados abertos do TSE.

---

## Como usar (assessores)

Acesse o link abaixo — não precisa instalar nada:

**[https://ferramenta-tse.vercel.app](https://ferramenta-tse.vercel.app)** *(atualizar após o deploy)*

### Pesquisar eleitos de um município

1. Selecione o **Ano** da eleição (ex: 2024)
2. Selecione o **Município** (ex: INACIOLÂNDIA)
3. Selecione o **Cargo** (Vereador ou Prefeito)
4. Clique em **Pesquisar**
5. Os eleitos aparecem na tabela
6. Clique em **Baixar Excel** para exportar

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

```bash
# 1. Importa os dados do TSE para o sqlite local
python cli.py ingest --anos 2028

# 2. Sobe o sqlite atualizado para o Supabase Storage
python scripts/seed_storage.py
```

Após o upload, o Vercel usa o arquivo atualizado automaticamente (sem redeploy).

---

## Estrutura do projeto (desenvolvedores)

```
FerramentaTSE/
├─ api/
│  └─ index.py         # Função serverless Vercel (despacha por ?action=)
├─ tse_core/           # Motor de consulta (Python puro, SQLite)
│  ├─ db.py
│  ├─ ingest.py
│  ├─ consulta.py
│  ├─ mandato.py
│  ├─ export.py
│  └─ dados/cargos.py
├─ index.html          # SPA (estático)
├─ styles.css          # Design institucional
├─ app.js              # Cliente JS (fetch → /api)
├─ vercel.json         # Config Vercel
├─ cli.py              # CLI: ingest / listar / rastrear
├─ dev_server.py       # Servidor local para desenvolvimento
├─ scripts/
│  └─ seed_storage.py  # Upload do sqlite para o Supabase Storage
└─ requirements.txt
```

### Rodar localmente

```bash
pip install -r requirements.txt
python dev_server.py        # http://localhost:3000
```

### Deploy no Vercel

1. Conectar o repositório como novo projeto (framework: *Other*)
2. Definir env vars no painel Vercel:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (service_role key)
3. Deploy automático a cada push na branch `main`

### Fonte dos dados

TSE Dados Abertos — `consulta_cand`:
`https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_AAAA.zip`
