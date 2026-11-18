from typing import Any

import requests

from app.core.config import Settings
from app.models.lead import Lead

CREATE_CARD_MUTATION = """
mutation CreateCard($input: CreateCardInput!) {
  createCard(input: $input) {
    card {
      id
      title
    }
  }
}
"""


class PipefyError(RuntimeError):
    """Erro especifico para chamadas ao Pipefy."""


class PipefyClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_card_from_lead(self, lead: Lead) -> dict[str, Any]:
        card_input = self._build_card_input(lead)

        if self.settings.dry_run:
            return {
                "dry_run": True,
                "message": "DRY_RUN=true: card nao foi enviado ao Pipefy.",
                "card_input": card_input,
            }

        self.settings.ensure_pipefy_ready()

        response = requests.post(
            self.settings.pipefy_api_url,
            headers={
                "Authorization": f"Bearer {self.settings.pipefy_token}",
                "Content-Type": "application/json",
            },
            json={
                "query": CREATE_CARD_MUTATION,
                "variables": {"input": card_input},
            },
            timeout=self.settings.request_timeout_seconds,
        )

        data = _parse_pipefy_response(response)
        return data["data"]["createCard"]["card"]

    def _build_card_input(self, lead: Lead) -> dict[str, Any]:
        card_input: dict[str, Any] = {
            "pipe_id": self.settings.pipefy_pipe_id,
            "title": _build_card_title(lead),
            "fields_attributes": self._build_field_attributes(lead),
        }

        if self.settings.pipefy_phase_id:
            card_input["phase_id"] = self.settings.pipefy_phase_id

        return card_input

    def _build_field_attributes(self, lead: Lead) -> list[dict[str, str]]:
        values_by_key = {
            "nome": lead.name,
            "email": lead.email,
            "telefone": lead.phone,
            "empresa": lead.company,
            "dores": "\n".join(f"- {pain}" for pain in lead.pain_points),
            "origem": lead.source,
            "resumo_comercial": lead.commercial_summary,
            "landing_page": lead.landing_page,
            "tags": ", ".join(lead.tags),
        }

        fields = []
        for key, pipefy_field_id in self.settings.pipefy_field_map.items():
            field_value = values_by_key.get(key, "")
            if field_value:
                fields.append(
                    {
                        "field_id": pipefy_field_id,
                        "field_value": field_value,
                    }
                )

        return fields


def _build_card_title(lead: Lead) -> str:
    company = lead.company if lead.company and lead.company != "Nao informado" else "Sem empresa"
    return f"{lead.name} - {company}"


def _parse_pipefy_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise PipefyError(
            f"Pipefy retornou resposta nao-JSON. Status: {response.status_code}."
        ) from exc

    if response.status_code >= 400:
        raise PipefyError(f"Erro HTTP do Pipefy: {response.status_code}. Resposta: {data}")

    if data.get("errors"):
        raise PipefyError(f"Erro GraphQL do Pipefy: {data['errors']}")

    if not data.get("data", {}).get("createCard", {}).get("card"):
        raise PipefyError(f"Resposta inesperada do Pipefy: {data}")

    return data

