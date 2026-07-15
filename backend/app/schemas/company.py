"""企业（Company）的 Pydantic 校验模型。

- CompanyCreate / CompanyUpdate：请求边界
- CompanyRead：响应输出
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyBase(BaseModel):
    """企业共有字段。"""

    name: str = Field(..., min_length=1, max_length=200, description="企业名称")
    code: str | None = Field(default=None, max_length=50, description="股票代码/统一编号")
    industry: str | None = Field(default=None, max_length=100, description="所属行业")

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("企业名称不能为空")
        return v.strip()


class CompanyCreate(CompanyBase):
    """创建企业的请求体。"""


class CompanyUpdate(BaseModel):
    """更新企业的请求体（部分更新）。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    industry: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("企业名称不能为空")
        return v.strip() if v is not None else None


class CompanyRead(CompanyBase):
    """企业响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
