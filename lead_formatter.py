from app.models.lead import Lead


def format_lead_for_sales(lead: Lead) -> str:
    """
    Gera um resumo legivel para o time comercial.

    Esse texto pode ir para um campo de texto longo do Pipefy.
    """
    pain_points = _format_pain_points(lead.pain_points)
    email = f"[{lead.email}](mailto:{lead.email})" if lead.email else "Nao informado"

    lines = [
        f"👤 Nome: {lead.name or 'Nao informado'}",
        f"📧 Email: {email}",
        f"📱 Telefone: {lead.phone or 'Nao informado'}",
        f"🏢 Empresa: {lead.company or 'Nao informado'}",
        "🚨 Principais dores:",
        pain_points,
    ]

    if lead.source:
        lines.append(f"Origem: {lead.source}")
    if lead.landing_page:
        lines.append(f"Landing page: {lead.landing_page}")
    if lead.tags:
        lines.append(f"Tags: {', '.join(lead.tags)}")

    return "\n".join(lines)


def _format_pain_points(pain_points: list[str]) -> str:
    if not pain_points:
        return "- Nao informado"
    return "\n".join(f"- {pain}" for pain in pain_points)

