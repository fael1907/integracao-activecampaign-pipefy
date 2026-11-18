from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Carrega variaveis de ambiente e o arquivo .env local."""

    app_name: str = "ActiveCampaign -> Pipefy MVP"
    app_env: str = "development"
    dry_run: bool = True
    webhook_secret: str = ""
    request_timeout_seconds: int = 20

    pipefy_api_url: str = "https://api.pipefy.com/graphql"
    pipefy_token: str = ""
    pipefy_pipe_id: str = ""
    pipefy_phase_id: str = ""

    pipefy_field_id_nome: str = ""
    pipefy_field_id_email: str = ""
    pipefy_field_id_telefone: str = ""
    pipefy_field_id_empresa: str = ""
    pipefy_field_id_dores: str = ""
    pipefy_field_id_origem: str = ""
    pipefy_field_id_resumo_comercial: str = ""
    pipefy_field_id_landing_page: str = ""
    pipefy_field_id_tags: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def pipefy_field_map(self) -> dict[str, str]:
        """Relaciona campos internos do lead aos IDs dos campos no Pipefy."""
        field_map = {
            "nome": self.pipefy_field_id_nome,
            "email": self.pipefy_field_id_email,
            "telefone": self.pipefy_field_id_telefone,
            "empresa": self.pipefy_field_id_empresa,
            "dores": self.pipefy_field_id_dores,
            "origem": self.pipefy_field_id_origem,
            "resumo_comercial": self.pipefy_field_id_resumo_comercial,
            "landing_page": self.pipefy_field_id_landing_page,
            "tags": self.pipefy_field_id_tags,
        }
        return {key: value for key, value in field_map.items() if value}

    def ensure_pipefy_ready(self) -> None:
        """Falha cedo quando a integracao real com Pipefy nao esta configurada."""
        missing = []
        if not self.pipefy_token:
            missing.append("PIPEFY_TOKEN")
        if not self.pipefy_pipe_id:
            missing.append("PIPEFY_PIPE_ID")
        if not self.pipefy_field_map:
            missing.append("PIPEFY_FIELD_ID_*")

        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(
                f"Configuracao incompleta para Pipefy: {missing_list}. "
                "Preencha o .env ou use DRY_RUN=true para testes locais."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()

