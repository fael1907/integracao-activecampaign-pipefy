# Integração ActiveCampaign → Pipefy (leads do site direto no CRM)

API em **Python (FastAPI)** que recebe os leads do formulário do site via webhook da **ActiveCampaign**, limpa e padroniza os dados e cria automaticamente um card no **Pipefy**, o CRM do time comercial, com um resumo pronto para o primeiro contato.

> Projeto que desenvolvi com o squad de Python da **Ayra Consultoria** (empresa júnior de gestão da UFRJ), participando de todas as etapas. Esta é a versão pública: tokens, IDs e endereços reais foram removidos.

## Problema

Quem preenchia o formulário do site caía na ActiveCampaign, mas o time comercial trabalhava no Pipefy. Os leads eram copiados à mão de um sistema para o outro, com atraso e com dados bagunçados: nomes em caixa alta, telefones em formatos diferentes, campos vazios.

## Solução

```
Formulário do site → ActiveCampaign → webhook → FastAPI (limpeza e padronização) → API GraphQL do Pipefy → card criado no CRM
```

1. **Recebe o webhook** em `POST /webhooks/activecampaign`, aceitando JSON ou form-urlencoded (o formato que a ActiveCampaign usa), protegido por um segredo na URL.
2. **Normaliza o lead:** procura cada informação em vários nomes de campo possíveis (`email`, `contact[email]`, `contact.email`...), padroniza nome e e-mail, formata o telefone como `(21) 99999-9999` e transforma listas de dores em itens.
3. **Monta um resumo comercial** legível, com nome, contato, empresa, principais dores, origem e landing page.
4. **Cria o card no Pipefy** pela mutation `createCard` da API GraphQL, mapeando cada informação para o campo certo do pipe.

## Impacto

- Leads do site chegam ao CRM na hora, sem ninguém copiar dados.
- O time comercial recebe o lead já organizado, com um resumo pronto para a abordagem.

## Destaques técnicos

- **Modo `DRY_RUN`:** trata o lead e mostra exatamente o card que seria criado, sem tocar no Pipefy. Assim dá para testar com segurança.
- **Configuração por variáveis de ambiente:** token, pipe e IDs de campos ficam no `.env`, nunca no código. A API recusa rodar em modo real se faltar alguma configuração e diz o que está faltando.
- **Erros tratados por tipo:** segredo inválido (401), payload vazio (400), lead sem e-mail (422), falha no Pipefy (502), cada um com mensagem clara.
- **Duas versões do mesmo fluxo:**
  - `main.py`: versão didática em um arquivo só, usada para apresentar o fluxo ao time;
  - `app/`: versão organizada em camadas (`api`, `core`, `models`, `services`), pronta para crescer.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env          # deixe DRY_RUN=true no primeiro teste
uvicorn main:app --reload     # ou: uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000/docs` para testar o webhook pela documentação interativa. O passo a passo para configurar o Pipefy está em `PIPEFY_CONFIG_PASSO_A_PASSO.md`.

## Como usei IA

Construí com apoio do **Claude Code**: a IA ajudou a entender a API GraphQL do Pipefy e o formato dos webhooks da ActiveCampaign, e a escrever o código em camadas. Testei com leads reais em modo `DRY_RUN` antes de ligar a criação de cards de verdade.

---
Rafael Avila · Economia UFRJ
