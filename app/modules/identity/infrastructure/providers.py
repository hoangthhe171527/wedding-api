"""Lắp ráp phụ thuộc của `identity`.

Đây là nơi DUY NHẤT trong module biết `access` tồn tại: các cổng
`PermissionResolver`, `RoleGranter`, `UserRoleReader` được cắm vào hàm dựng mà
`access` công bố trên barrel. Use case và domain không hề nhắc tới `access`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.access import (
    build_grant_role,
    build_resolve_permissions,
    build_user_role_reader,
)
from app.modules.identity.application.session_issuer import SessionIssuer
from app.modules.identity.application.use_cases import (
    ChangeOwnPassword,
    GetCurrentActor,
    ListUsers,
    LoginUser,
    LogoutUser,
    RefreshToken,
    RegisterCustomer,
    SetUserActive,
)
from app.modules.identity.infrastructure.persistence.repositories import (
    BeanieAuthSessionRepository,
    BeanieStudioRepository,
    BeanieUserRepository,
)


def build_session_issuer() -> SessionIssuer:
    """Bộ phát hành phiên dùng chung cho đăng nhập, đăng ký, refresh và `GET /auth/me`."""
    return SessionIssuer(BeanieAuthSessionRepository(), build_resolve_permissions())


def provide_login_user() -> LoginUser:
    return LoginUser(BeanieUserRepository(), BeanieStudioRepository(), build_session_issuer())


def provide_register_customer() -> RegisterCustomer:
    return RegisterCustomer(
        BeanieUserRepository(), BeanieStudioRepository(), build_grant_role(), build_session_issuer()
    )


def provide_refresh_token() -> RefreshToken:
    return RefreshToken(
        BeanieAuthSessionRepository(),
        BeanieUserRepository(),
        BeanieStudioRepository(),
        build_session_issuer(),
    )


def provide_logout_user() -> LogoutUser:
    return LogoutUser(BeanieAuthSessionRepository())


def provide_get_current_actor() -> GetCurrentActor:
    return GetCurrentActor(BeanieUserRepository(), BeanieStudioRepository(), build_session_issuer())


def provide_change_own_password() -> ChangeOwnPassword:
    return ChangeOwnPassword(BeanieUserRepository(), BeanieAuthSessionRepository())


def provide_list_users() -> ListUsers:
    return ListUsers(BeanieUserRepository(), BeanieStudioRepository(), build_user_role_reader())


def provide_set_user_active() -> SetUserActive:
    return SetUserActive(BeanieUserRepository(), BeanieAuthSessionRepository())


LoginUserDep = Annotated[LoginUser, Depends(provide_login_user)]
RegisterCustomerDep = Annotated[RegisterCustomer, Depends(provide_register_customer)]
RefreshTokenDep = Annotated[RefreshToken, Depends(provide_refresh_token)]
LogoutUserDep = Annotated[LogoutUser, Depends(provide_logout_user)]
GetCurrentActorDep = Annotated[GetCurrentActor, Depends(provide_get_current_actor)]
ChangeOwnPasswordDep = Annotated[ChangeOwnPassword, Depends(provide_change_own_password)]
ListUsersDep = Annotated[ListUsers, Depends(provide_list_users)]
SetUserActiveDep = Annotated[SetUserActive, Depends(provide_set_user_active)]

__all__ = [
    "ChangeOwnPasswordDep",
    "GetCurrentActorDep",
    "ListUsersDep",
    "LoginUserDep",
    "LogoutUserDep",
    "RefreshTokenDep",
    "RegisterCustomerDep",
    "SetUserActiveDep",
    "build_session_issuer",
]
