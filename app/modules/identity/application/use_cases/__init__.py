"""Use case của `identity` — mỗi file một việc, mỗi class một `execute`."""

from app.modules.identity.application.use_cases.change_own_password import ChangeOwnPassword
from app.modules.identity.application.use_cases.delete_own_account import DeleteOwnAccount
from app.modules.identity.application.use_cases.get_current_actor import GetCurrentActor
from app.modules.identity.application.use_cases.list_users import ListUsers
from app.modules.identity.application.use_cases.login_user import LoginUser
from app.modules.identity.application.use_cases.logout_user import LogoutUser
from app.modules.identity.application.use_cases.refresh_token import RefreshToken
from app.modules.identity.application.use_cases.register_customer import RegisterCustomer
from app.modules.identity.application.use_cases.set_user_active import SetUserActive

__all__ = [
    "ChangeOwnPassword",
    "DeleteOwnAccount",
    "GetCurrentActor",
    "ListUsers",
    "LoginUser",
    "LogoutUser",
    "RefreshToken",
    "RegisterCustomer",
    "SetUserActive",
]
