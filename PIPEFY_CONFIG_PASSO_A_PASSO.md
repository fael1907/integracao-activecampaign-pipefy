# Configurando o Pipefy no MVP

Este guia e para sair do modo simulado (`DRY_RUN=true`) e preparar a criacao real de cards no Pipefy.

Importante: nao cole token em grupo, print, chat ou README. Token fica somente no arquivo `.env` da maquina ou nas variaveis de ambiente do Render.

## 1. O que precisa existir no Pipefy

Crie ou escolha um pipe para receber os leads. Para o MVP, uma estrutura simples ja resolve:

```text
Novo lead
Em contato
Qualificado
Proposta
Ganho
Perdido
```

No formulario inicial do pipe, crie campos parecidos com estes:

| Campo no Pipefy | Tipo sugerido | Obrigatorio? |
| --- | --- | --- |
| Nome do lead | Texto curto | Sim |
| Email | Email ou texto curto | Sim |
| Telefone | Telefone ou texto curto | Nao |
| Empresa | Texto curto | Nao |
| Principais dores | Texto longo | Nao |
| Resumo comercial | Texto longo | Nao |

Opcionalmente, depois voces podem adicionar:

| Campo | Para que serve |
| --- | --- |
| Origem | Google, Meta, LinkedIn, organico etc. |
| Landing page | URL da pagina que captou o lead |
| Status de integracao | Ajuda a auditar erros |
| ID ActiveCampaign | Ajuda a evitar duplicidade |

## 2. Onde pegar o Pipe ID

Abra o pipe no navegador.

A URL costuma ficar parecida com:

```text
https://app.pipefy.com/pipes/123456789
```

O numero depois de `/pipes/` e o `PIPEFY_PIPE_ID`.

No `.env`, preencha:

```env
PIPEFY_PIPE_ID=123456789
```

## 3. Onde colocar o token

No arquivo `.env`, preencha:

```env
PIPEFY_TOKEN=cole_o_token_aqui
```

Deixe assim enquanto estiverem testando sem criar card real:

```env
DRY_RUN=true
```

So mudem para falso quando os campos estiverem mapeados:

```env
DRY_RUN=false
```

## 4. Como descobrir os IDs dos campos

Depois de preencher `PIPEFY_TOKEN` e `PIPEFY_PIPE_ID`, rode no terminal do VS Code:

```powershell
.\.venv\Scripts\python.exe scripts\list_pipefy_fields.py
```

O script vai mostrar algo parecido com:

```text
CAMPOS DO FORMULARIO INICIAL
--------------------------------
- Nome do lead | id: nome_do_lead | tipo: short_text | obrigatorio
- Email | id: email | tipo: email | obrigatorio
- Telefone | id: telefone | tipo: phone | opcional
```

Copie os IDs para o `.env`:

```env
PIPEFY_FIELD_ID_NOME=nome_do_lead
PIPEFY_FIELD_ID_EMAIL=email
PIPEFY_FIELD_ID_TELEFONE=telefone
PIPEFY_FIELD_ID_EMPRESA=empresa
PIPEFY_FIELD_ID_DORES=principais_dores
PIPEFY_FIELD_ID_RESUMO_COMERCIAL=resumo_comercial
```

## 5. Como testar sem criar card real

Confirme no `.env`:

```env
DRY_RUN=true
```

Rode a API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Abra:

```text
http://127.0.0.1:8000/docs
```

Teste `POST /webhooks/activecampaign`.

Se a resposta mostrar `payload_que_seria_enviado`, o mapeamento esta quase pronto.

## 6. Como testar criando card real

Pare a API com `Ctrl + C`.

No `.env`, troque:

```env
DRY_RUN=false
```

Suba a API de novo:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Teste novamente no `/docs`.

Se tudo estiver certo, a resposta do Pipefy deve trazer `id` e `title` do card criado.

## 7. Erros comuns nessa etapa

`401` ou erro de autorizacao: token errado, expirado ou sem permissao no pipe.

`Pipe nao encontrado`: `PIPEFY_PIPE_ID` errado ou token sem acesso ao pipe.

`Erro GraphQL`: geralmente ID de campo errado, campo obrigatorio sem valor, ou campo de tipo diferente do valor enviado.

Card criado sem informacoes: os IDs dos campos no `.env` nao batem com os campos reais do pipe.

Duplicidade de cards: normal no MVP. Para producao, precisa criar controle de idempotencia.

## 8. O que vem depois

Depois que criar um card real manualmente pelo `/docs`, o proximo passo e expor a API para a ActiveCampaign usando ngrok ou Render.

Ordem recomendada:

1. Pipefy estruturado.
2. Token e pipe ID no `.env`.
3. Script de campos rodando.
4. IDs de campos no `.env`.
5. Teste com `DRY_RUN=true`.
6. Teste real com `DRY_RUN=false`.
7. Deploy no Render.
8. Webhook real na ActiveCampaign.

