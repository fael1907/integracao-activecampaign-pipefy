import json
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import get_settings
from app.services.lead_normalizer import normalize_activecampaign_payload
from app.services.pipefy_client import PipefyClient, PipefyError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/activecampaign")
async def receive_activecampaign_webhook(
    request: Request,
    secret: str | None = Query(default=None),
) -> dict:
    """
    Recebe o webhook da ActiveCampaign, normaliza o lead e cria o card no Pipefy.

    O parametro `secret` e um MVP simples de seguranca:
    configure a URL do webhook como /webhooks/activecampaign?secret=seu-segredo.
    """
    settings = get_settings()
    if settings.webhook_secret and secret != settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook secret invalido.",
        )

    payload = await read_payload(request)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload vazio. Envie JSON ou form-urlencoded.",
        )

    lead = normalize_activecampaign_payload(payload)
    if not lead.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead sem email. Confira o mapeamento dos campos recebidos.",
        )

    try:
        pipefy_result = PipefyClient(settings).create_card_from_lead(lead)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except PipefyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "message": "Lead recebido, tratado e enviado para o Pipefy.",
        "dry_run": settings.dry_run,
        "lead": lead.model_dump(),
        "pipefy": pipefy_result,
    }


async def read_payload(request: Request) -> dict:
    """
    Le o corpo da requisicao.

    A ActiveCampaign pode enviar dados como POST parameters. Como o MVP tambem
    quer aceitar JSON, esta funcao cobre os dois formatos mais comuns.
    """
    body = await request.body()
    if not body:
        return {}

    content_type = request.headers.get("content-type", "").lower()
    text_body = body.decode("utf-8")

    if "json" in content_type or text_body.lstrip().startswith("{"):
        try:
            return json.loads(text_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON invalido.",
            ) from exc

    parsed = parse_qs(text_body, keep_blank_values=True)
    return {
        key: values[0] if len(values) == 1 else values
        for key, values in parsed.items()
    }

