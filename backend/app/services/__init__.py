"""业务逻辑层。

每个领域一个 service 模块。Service 通过注入的 Session 操作 ORM，
承担业务规则与编排，路由层不直接写业务逻辑。
"""
