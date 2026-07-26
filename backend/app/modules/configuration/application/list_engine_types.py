"""ListEngineTypesUseCase — TRADEOS_API_SPECIFICATION.md §6.6, GET
/configuration/engine-types."""

from app.modules.configuration.domain.engine_type import EngineType
from app.modules.configuration.infrastructure.repository import EngineTypeRepository


class ListEngineTypesUseCase:
    def __init__(self, repository: EngineTypeRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[EngineType]:
        return await self._repository.list_all()
