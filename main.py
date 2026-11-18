"""
main.py

Versao didatica do MVP ActiveCampaign -> FastAPI -> Pipefy.

Este arquivo deixa o fluxo principal em um unico lugar para facilitar a
apresentacao:

1. Recebe um lead via webhook.
2. Organiza os dados recebidos.
3. Monta um resumo legivel para o time comercial.
4. Cria um card no Pipefy via GraphQL.

Para testar sem criar card real, deixe DRY_RUN=true no .env.

Rodar localmente: uvicorn main:app --reload
Documentacao interativa: http://127.0.0.1:8000/docs
"""


import json
import os
import re
from typing import Any
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, status

load_dotenv()

app = FastAPI(
    title="MVP ActiveCampaign para Pipefy",
    description="API simples para receber leads e criar cards no Pipefy.",
    version="0.1.0",
)


# Configuracoes vindas do arquivo .env.
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

PIPEFY_API_URL = os.getenv("PIPEFY_API_URL", "https://api.pipefy.com/graphql")
PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN", "")
PIPEFY_PIPE_ID = os.getenv("PIPEFY_PIPE_ID", "")

PIPEFY_FIELD_ID_NOME = os.getenv("PIPEFY_FIELD_ID_NOME", "nome_do_lead")
PIPEFY_FIELD_ID_EMAIL = os.getenv("PIPEFY_FIELD_ID_EMAIL", "email")
PIPEFY_FIELD_ID_TELEFONE = os.getenv("PIPEFY_FIELD_ID_TELEFONE", "telefone")
PIPEFY_FIELD_ID_EMPRESA = os.getenv("PIPEFY_FIELD_ID_EMPRESA", "empresa")
PIPEFY_FIELD_ID_RESUMO = os.getenv("PIPEFY_FIELD_ID_RESUMO_COMERCIAL", "resumo_comercial")



@app.get("/health")
def health_check() -> dict[str, Any]:
    """
    Endpoint simples para confirmar que a API esta funcionando.
    """
    return {
        "status": "ok",
        "message": "API no ar",
        "dry_run": DRY_RUN,
    }


async def read_payload(request: Request) -> dict[str, Any]:
    """
    Le o corpo da requisicao aceitando JSON ou form-urlencoded.

    A ActiveCampaign envia os dados como form-urlencoded com chaves no formato
    'contact[email]', 'contact[fields][30]', etc. Esta funcao converte esse
    formato para um dict aninhado igual ao JSON equivalente.
    """
    body = await request.body()
    if not body:
        return {}

    content_type = request.headers.get("content-type", "").lower()
    text_body = body.decode("utf-8")

    if "json" in content_type or text_body.lstrip().startswith("{"):
        return json.loads(text_body)

    flat = {
        k: v[0] if len(v) == 1 else v
        for k, v in parse_qs(text_body, keep_blank_values=True, encoding="utf-8").items()
    }
    return _parse_bracket_keys(flat)


def _parse_bracket_keys(flat: dict[str, Any]) -> dict[str, Any]:
    """Converte {'contact[email]': 'x'} em {'contact': {'email': 'x'}}."""
    result: dict[str, Any] = {}
    for key, value in flat.items():
        parts = [p for p in re.split(r"\[|\]", key) if p]
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return result


@app.post("/webhooks/activecampaign")
async def receber_lead_activecampaign(
    request: Request,
    secret: str | None = Query(default=None),
) -> dict[str, Any]:
    """
    Endpoint chamado pela ActiveCampaign quando um novo lead entra.

    Exemplo de URL para configurar no webhook:
    /webhooks/activecampaign?secret=SEU_SEGREDO
    """
    if secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret do webhook invalido.",
        )

    payload = await read_payload(request)

    print("\n===== PAYLOAD RECEBIDO DO ACTIVECAMPAIGN =====")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("==============================================\n")

    lead_tratado = tratar_dados_do_lead(payload)

    print("\n===== LEAD TRATADO =====")
    print(json.dumps(lead_tratado, indent=2, ensure_ascii=False))
    print(f"DRY_RUN = {DRY_RUN}")
    print("========================\n")

    resumo_comercial = formatar_resumo_comercial(lead_tratado)
    resultado_pipefy = criar_card_no_pipefy(lead_tratado, resumo_comercial)

    print("\n===== RESULTADO PIPEFY =====")
    print(json.dumps(resultado_pipefy, indent=2, ensure_ascii=False))
    print("============================\n")

    return {
        "status": "ok",
        "message": "Lead recebido e processado com sucesso.",
        "lead_tratado": lead_tratado,
        "resumo_comercial": resumo_comercial,
        "pipefy": resultado_pipefy,
    }


def tratar_dados_do_lead(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Organiza os dados recebidos da ActiveCampaign.

    A ideia e pegar um JSON possivelmente baguncado e transformar em um
    formato previsivel para o Pipefy e para o time comercial.
    """
    contato = payload.get("contact", {})
    # Campos customizados do ActiveCampaign ficam em contact.fields com IDs numericos.
    # IDs mapeados a partir do payload real recebido:
    #   4  = Nome da Empresa
    #   7  = Canal de origem (WhatsApp, Google etc.)
    #   8  = Telefone (backup)
    #   9  = Principal dor / necessidade
    #   30 = Telefone (WhatsApp principal)
    #   31 = Setor
    campos_ac = contato.get("fields", {})

    primeiro_nome = buscar_valor(payload, contato, ["first_name", "firstname", "nome"])
    ultimo_nome = buscar_valor(payload, contato, ["last_name", "lastname", "sobrenome"])
    nome_completo = buscar_valor(payload, contato, ["name", "full_name", "nome_completo"])

    if not nome_completo:
        nome_completo = f"{primeiro_nome} {ultimo_nome}".strip()

    lead = {
        "nome": normalizar_nome(nome_completo),
        "email": normalizar_email(buscar_valor(payload, contato, ["email"])),
        "telefone": normalizar_telefone(
            buscar_valor(payload, contato, ["phone", "telefone", "celular"])
            or limpar_texto(campos_ac.get("30", ""))
            or limpar_texto(campos_ac.get("8", ""))
        ),
        "empresa": limpar_texto(
            payload.get("company")
            or payload.get("empresa")
            or contato.get("orgname")
            or limpar_texto(campos_ac.get("4", ""))
            or "Nao informado"
        ),
        "tamanho_empresa": limpar_texto(campos_ac.get("tamanho_da_empresa", "") or ""),
        "setor": limpar_texto(campos_ac.get("setor", "") or limpar_texto(campos_ac.get("31", ""))),
        "principais_dores": normalizar_lista(
            payload.get("principais_dores")
            or payload.get("dores")
            or payload.get("pain_points")
            or campos_ac.get("9")
        ),
        "origem": limpar_texto(
            payload.get("utm_source")
            or payload.get("source")
            or payload.get("origem")
            or limpar_texto(campos_ac.get("7", ""))
            or "Nao informado"
        ),
        "landing_page": limpar_texto(
            payload.get("landing_page")
            or payload.get("page_url")
            or payload.get("url")
            or ""
        ),
    }

    if not lead["email"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead sem email. Confira o payload recebido da ActiveCampaign.",
        )

    return lead


def buscar_valor(
    payload: dict[str, Any],
    contato: dict[str, Any],
    chaves: list[str],
) -> str:
    """
    Procura uma informacao primeiro no objeto contact e depois na raiz do JSON.
    """
    for chave in chaves:
        if contato.get(chave):
            return limpar_texto(contato[chave])
        if payload.get(chave):
            return limpar_texto(payload[chave])
    return ""


def limpar_texto(valor: Any) -> str:
    """
    Remove espacos desnecessarios e transforma valores vazios em string vazia.
    """
    if valor is None:
        return ""
    texto = str(valor).strip()
    return re.sub(r"\s+", " ", texto)


def normalizar_nome(nome: str) -> str:
    """
    Padroniza o nome para ficar mais apresentavel.
    """
    nome_limpo = limpar_texto(nome)
    if not nome_limpo:
        return "Nao informado"
    return nome_limpo.title()


def normalizar_email(email: str) -> str:
    """
    Padroniza email em minusculas.
    """
    return limpar_texto(email).lower()


def normalizar_telefone(telefone: str) -> str:
    """
    Tenta transformar telefone brasileiro em um formato mais legivel.
    """
    texto = limpar_texto(telefone)
    digitos = re.sub(r"\D", "", texto)

    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"

    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"

    return texto


def normalizar_lista(valor: Any) -> list[str]:
    """
    Transforma dores/tags em lista, mesmo quando chegam como texto.
    """
    if not valor:
        return []

    if isinstance(valor, list):
        itens = valor
    else:
        itens = re.split(r"[,;|\n]+", str(valor))

    return [limpar_texto(item) for item in itens if limpar_texto(item)]


def formatar_resumo_comercial(lead: dict[str, Any]) -> str:
    """
    Monta um texto simples para o comercial bater o olho e entender o lead.
    """
    dores = lead["principais_dores"] or ["Nao informado"]
    dores_formatadas = "\n".join(f"- {dor}" for dor in dores)

    linhas = [
        f"Nome: {lead['nome']}",
        f"Email: [{lead['email']}](mailto:{lead['email']})",
        f"Telefone: {lead['telefone'] or 'Nao informado'}",
        f"Empresa: {lead['empresa']}",
    ]
    if lead.get("tamanho_empresa"):
        linhas.append(f"Tamanho da empresa: {lead['tamanho_empresa']}")
    if lead.get("setor"):
        linhas.append(f"Setor: {lead['setor']}")
    linhas += [
        "Principais dores:",
        dores_formatadas,
        f"Origem: {lead['origem']}",
        f"Landing page: {lead['landing_page'] or 'Nao informado'}",
    ]
    return "\n".join(linhas)


def criar_card_no_pipefy(
    lead: dict[str, Any],
    resumo_comercial: str,
) -> dict[str, Any]:
    """
    Cria o card no Pipefy.

    Em DRY_RUN=true, a funcao so mostra o que seria enviado. Isso e perfeito
    para testar antes de usar token real.
    """
    card_input = {
        "pipe_id": PIPEFY_PIPE_ID,
        "title": f"{lead['nome']} - {lead['empresa']}",
        "fields_attributes": [
            {"field_id": PIPEFY_FIELD_ID_NOME, "field_value": lead["nome"]},
            {"field_id": PIPEFY_FIELD_ID_EMAIL, "field_value": lead["email"]},
            {"field_id": PIPEFY_FIELD_ID_TELEFONE, "field_value": lead["telefone"]},
            {"field_id": PIPEFY_FIELD_ID_EMPRESA, "field_value": lead["empresa"]},
            {"field_id": PIPEFY_FIELD_ID_RESUMO, "field_value": resumo_comercial},
        ],
    }

    if DRY_RUN:
        return {
            "dry_run": True,
            "message": "Teste local: nenhum card real foi criado.",
            "payload_que_seria_enviado": card_input,
        }

    if not PIPEFY_TOKEN or not PIPEFY_PIPE_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configure PIPEFY_TOKEN e PIPEFY_PIPE_ID no .env.",
        )

    mutation = """
    mutation CreateCard($input: CreateCardInput!) {
      createCard(input: $input) {
        card {
          id
          title
        }
      }
    }
    """

    response = requests.post(
        PIPEFY_API_URL,
        headers={
            "Authorization": f"Bearer {PIPEFY_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "query": mutation,
            "variables": {"input": card_input},
        },
        timeout=20,
    )

    data = response.json()

    print("\n===== RESPOSTA BRUTA DO PIPEFY =====")
    print(f"HTTP status: {response.status_code}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("=====================================\n")

    if response.status_code >= 400 or data.get("errors"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Erro ao criar card no Pipefy.",
                "pipefy_response": data,
            },
        )

    return data["data"]["createCard"]["card"]
