from typing import Optional


class FAExportError(Exception):
    pass


class FAExportAPIError(FAExportError):
    err_type: Optional[str] = None

    def __init__(self, msg: str, url: Optional[str]) -> None:
        self.msg = msg
        self.url = url

    def __str__(self) -> str:
        msg = self.msg
        if self.err_type is not None:
            f"{self.err_type}: {self.msg}"
        msg += f" ({self.url})" if self.url is not None else ""
        return f"{type(self).__name__}({msg})"


class FAExportClientError(FAExportError):
    def __init__(self, msg: str) -> None:
        self.msg = msg

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.msg})"


class UnrecognisedError(FAExportAPIError):
    def __init__(self, err_type: str, msg: str, url: Optional[str]) -> None:
        self.err_type = err_type
        self.msg = msg
        self.url = url


class FormError(FAExportAPIError):
    err_type = "fa_form"


class InvalidOffset(FAExportAPIError):
    err_type = "fa_offset"


class InvalidSearchParameters(FAExportAPIError):
    err_type = "fa_search"


class IncorrectFAStyle(FAExportAPIError):
    err_type = "fa_style"


class FALoginError(FAExportAPIError):
    err_type = "fa_login"


class InvalidFACookies(FAExportAPIError):
    err_type = "fa_login_cookie"


class InaccessibleToGuests(FAExportAPIError):
    err_type = "fa_guest_access"


class BlockedByContentFilter(FAExportAPIError):
    err_type = "fa_content_filter"


class SubmissionNotFound(FAExportAPIError):
    err_type = "fa_not_found"


class UserNotFound(FAExportAPIError):
    err_type = "fa_no_user"


class FAUserDisabled(FAExportAPIError):
    err_type = "account_disabled"


class FASlowdown(FAExportAPIError):
    err_type = "fa_slowdown"


class FAExportUnknownError(FAExportAPIError):
    def __init__(self, err_type: str, msg: str, url: Optional[str]) -> None:
        self.err_type = err_type
        self.msg = msg
        self.url = url


class FACloudflareError(FAExportAPIError):
    err_type = "fa_cloudflare"


def from_error_data(error_data: dict) -> FAExportAPIError:
    error_type = error_data["error_type"]
    msg = error_data["error"]
    url = error_data.get("url")
    err_classes = [
        FormError, InvalidOffset, InvalidSearchParameters, IncorrectFAStyle, FALoginError, InvalidFACookies,
        InaccessibleToGuests, BlockedByContentFilter, SubmissionNotFound, UserNotFound, FAUserDisabled, FASlowdown,
        FACloudflareError,
    ]
    known_unknown_types = [
        "unknown", "unknown_http", "fa_unknown", "fa_system", "fa_no_title", "cache_error", "fa_status",
    ]
    klass = {
        klass.err_type: klass for klass in err_classes
    }.get(error_type)
    if klass is not None:
        return klass(msg, url)
    if error_type in known_unknown_types:
        return FAExportUnknownError(error_type, msg, url)
    return UnrecognisedError(error_type, msg, url)
