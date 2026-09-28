from app.routers.members import router as members_router
from app.routers.categories import router as categories_router
from app.routers.rules import router as rules_router
from app.routers.kudos import router as kudos_router
from app.routers.items import router as items_router
from app.routers.redemptions import router as redemptions_router
from app.routers.system import router as system_router

__all__ = [
    "members_router",
    "categories_router",
    "rules_router",
    "kudos_router",
    "items_router",
    "redemptions_router",
    "system_router",
]
