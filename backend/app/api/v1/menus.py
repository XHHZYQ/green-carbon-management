"""菜单路由接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.response import success
from app.services import auth_service

router = APIRouter(prefix="/menus", tags=["菜单"])


@router.get("/routes", summary="获取当前用户菜单树")
async def get_routes(user: CurrentUser, session: SessionDep):
    tree = await auth_service.build_menu_tree(session, user)
    return success(tree)
