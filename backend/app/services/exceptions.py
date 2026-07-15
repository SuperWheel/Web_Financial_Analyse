"""业务层自定义异常。

业务规则违反时抛出，由 api 层转换为合适的 HTTP 响应。
"""
from __future__ import annotations


class ServiceError(Exception):
    """业务层异常基类。携带 HTTP 状态码与 detail。"""

    status_code: int = 400

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(ServiceError):
    """资源不存在。"""

    status_code = 404


class ConflictError(ServiceError):
    """唯一约束冲突。"""

    status_code = 409
