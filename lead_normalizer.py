import re
from typing import Any

from app.models.lead import Lead
from app.services.lead_formatter import format_lead_for_sales

NAME_KEYS = ["name", "nome", "full_name", "contact[name]", "contact[full_name]"]
FIRST_NAME_KEYS = ["first_name", "firstname", "contact[first_name]", "contact[firstname]"]
LAST_NAME_KEYS = ["last_name", "lastname", "contact[last_name]", "contact[lastname]"]
EMAIL_KEYS = ["email", "contact[email]", "contact.email"]
PHONE_KEYS = ["phone", "telefone", "celular", "contact[phone]", "contact.phone"]
COMPANY_KEYS = [
    "company",
    "empresa",
    "company_name",
    "organization",
    "account[name]",
    "contact[orgname]",
]
PAIN_KEYS = [
    "pain_points",
    "principais_dores",
    "dores",
    "dor",
    "necessidade",
    "fields[principais_dores]",
    "fields[dores]",
    "contact[fields][principais_dores]",
]
SOURCE_KEYS = ["source", "origem", "utm_source", "initiated_from", "form_name"]
LANDING_PAGE_KEYS = ["landing_page", "page_url", "url", "utm_landing_page"]
TAGS_KEYS = ["tags", "contact[tags]", "contact.tags"]


def normalize_activecampaign_payload(payload: dict[str, Any]) -> Lead:
    """Transforma o payload baguncado da origem em um Lead padronizado."""
    name = _extract_text(payload, NAME_KEYS)
    if not name:
        first_name = _extract_text(payload, FIRST_NAME_KEYS)
        last_name = _extract_text(payload, LAST_NAME_KEYS)
        name = " ".join(part for part in [first_name, last_name] if part)

    lead = Lead(
        name=_normalize_name(name),
        email=_normalize_email(_extract_text(payload, EMAIL_KEYS)),
        phone=_normalize_phone(_extract_text(payload, PHONE_KEYS)),
        company=_clean_text(_extract_text(payload, COMPANY_KEYS)) or "Nao informado",
        pain_points=_extract_list(payload, PAIN_KEYS),
        source=_clean_text(_extract_text(payload, SOURCE_KEYS)) or "Nao informado",
        landing_page=_clean_text(_extract_text(payload, LANDING_PAGE_KEYS)),
        tags=_extract_list(payload, TAGS_KEYS),
        raw_payload=payload,
    )
    lead.commercial_summary = format_lead_for_sales(lead)
    return lead


def _extract_text(payload: dict[str, Any], possible_keys: list[str]) -> str:
    value = _extract_value(payload, possible_keys)
    return _clean_text(value)


def _extract_list(payload: dict[str, Any], possible_keys: list[str]) -> list[str]:
    value = _extract_value(payload, possible_keys)
    return _to_clean_list(value)


def _extract_value(payload: dict[str, Any], possible_keys: list[str]) -> Any:
    for key in possible_keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]

        nested_value = _get_nested_value(payload, key)
        if nested_value not in (None, ""):
            return nested_value

    return ""


def _get_nested_value(payload: dict[str, Any], key: str) -> Any:
    # Aceita tanto "contact.email" quanto "contact[email]".
    path = key.replace("]", "").replace("[", ".").split(".")
    current: Any = payload

    for part in path:
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current[part]

    return current


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return ""

    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _to_clean_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []

    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[\n;|,]+", str(value))

    cleaned_items = [_clean_text(item) for item in raw_items]
    return [item for item in cleaned_items if item]


def _normalize_name(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return "Nao informado"
    return text.title()


def _normalize_email(value: str) -> str:
    return _clean_text(value).lower()


def _normalize_phone(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    digits = re.sub(r"\D", "", text)
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]

    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"

    return text

