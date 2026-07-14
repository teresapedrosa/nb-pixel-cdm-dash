# Guia de atenção manual — nb-cdm

Este guia é pra quando alguma coisa parece errada no dashboard ou no
agendamento, e você não quer (ou não precisa) mexer no código. Não
pressupõe leitura de Python.

**Dashboard:** https://teresapedrosa.github.io/nb-pixel-cdm-dash/

---

## Como o dashboard se atualiza

Toda sexta-feira, às 08:00, um workflow no N8N roda automaticamente e:
1. Busca o que mudou no Plane desde a última vez
2. Recalcula as métricas
3. Gera o dashboard de novo
4. Publica no GitHub Pages

Você não precisa fazer nada nesse processo — ele é automático. Este guia é
só pra quando algo nesse fluxo falha.

---

## "O dashboard não atualizou nessa sexta"

1. **Confirma que o workflow do N8N está ativo** (toggle ligado na tela do
   workflow). Se tiver sido desativado sem querer, é só ligar de novo.
2. **Abre `logs\ultimo_sync.log`** na pasta do projeto — esse arquivo é
   reescrito toda vez que o sync roda (manual ou automático) e mostra
   exatamente onde parou. Procura por linhas com "ERRO".
3. Se o log mostrar **"venv não encontrado"** — ver seção abaixo.
4. Se o log mostrar erro nos passos de **sync/métricas** — provavelmente a
   API do Plane recusou a conexão (credencial expirada, ou o Plane estava
   fora do ar). Ver seção "A conexão com o Plane parou de funcionar".
5. Se o log mostrar erro no **git push** — o repositório pode estar com
   conflito, ou a autenticação do git expirou. Nesse caso, é melhor pedir
   ajuda em vez de tentar resolver sozinha (`git push` com conflito pode
   sobrescrever coisas sem querer).

## "venv não encontrado"

O ambiente Python (`venv/`) sumiu — pode acontecer por limpeza acidental
ou uma sincronização estranha do OneDrive. Solução: recriar do zero, na
pasta do projeto, no terminal:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Depois disso, roda `scripts\sync_and_publish.bat` manualmente uma vez pra
confirmar que voltou a funcionar.

## A conexão com o Plane parou de funcionar

Normalmente é uma de duas coisas:

- **A API key expirou ou foi revogada.** Pega uma nova key no Plane
  (Settings → API Tokens) e substitui o valor de `PLANE_API_KEY` no
  arquivo `.env` (esse arquivo não abre sozinho no Explorer — abrir com o
  Bloco de Notas). Não precisa mexer em mais nada.
- **O Plane estava temporariamente fora do ar.** Nesse caso não precisa
  fazer nada — o próximo sync (manual ou da sexta seguinte) resolve
  sozinho. Issues que falharam ficam marcadas internamente pra serem
  tentadas de novo automaticamente, não ficam "esquecidas".

## "Alguns números parecem errados ou um ticket sumiu"

O sistema guarda um cache do que já foi buscado, pra não rebuscar tudo
toda vez (mais rápido e evita bloqueio da API por excesso de chamadas).
Se desconfiar que algo ficou desatualizado, force um rebuild completo:

```
venv\Scripts\activate
python -m src.data_layer --full
python -m src.metrics
python -m src.render
git add docs\index.html
git commit -m "rebuild completo"
git push
```

Isso ignora o cache e rebusca tudo do zero — demora mais, mas garante que
está tudo atualizado.

## "Quero atualizar o dashboard agora, sem esperar sexta"

Duas formas:

- **Pelo N8N:** abre o workflow e clica em "Execute Workflow" (roda uma
  vez, sem mexer no agendamento automático).
- **Pelo terminal:** roda `scripts\sync_and_publish.bat` na pasta do
  projeto.

## "O link do dashboard não abre"

- Confirma que o último `git push` funcionou (ver `logs\ultimo_sync.log`
  ou rodar `git log -1` no terminal, dentro da pasta do projeto).
- No GitHub, em **Settings → Pages** do repositório, confirma que a fonte
  ainda está configurada como branch `main`, pasta `/docs`.
- GitHub Pages pode levar alguns minutos pra atualizar depois de um push —
  se acabou de publicar, espera um pouco antes de desconfiar de erro.

## Quando pedir ajuda em vez de tentar resolver sozinha

- Erro de `git push` com menção a "conflict" ou "rejected"
- Qualquer coisa envolvendo apagar ou sobrescrever o histórico do git
  (`--force`, `reset --hard`, etc.)
- Se depois de seguir os passos acima o problema persistir
