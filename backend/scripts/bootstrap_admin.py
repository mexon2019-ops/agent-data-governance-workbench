"""One-time admin bootstrap.

Required environment:
  DATABASE_URL
  BOOTSTRAP_ADMIN_USERNAME
  BOOTSTRAP_ADMIN_PASSWORD (minimum 14 characters)
Run from backend/: PYTHONPATH=. python scripts/bootstrap_admin.py
"""
import os
from sqlalchemy import select
from app.main import Base, SessionLocal, engine, Role, Permission, RolePermission, User, password_hash

PERMISSIONS = [
    ("iam:user:read", "查看用户", "iam:user", "read"),
    ("iam:role:read", "查看角色", "iam:role", "read"),
]


def main():
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not username or len(username) > 80:
        raise SystemExit("必须设置有效的 BOOTSTRAP_ADMIN_USERNAME")
    if len(password) < 14:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD 至少 14 位")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            raise SystemExit("数据库已有用户，拒绝重复引导；请通过受控用户管理流程创建账号")
        role = db.scalar(select(Role).where(Role.code == "platform_admin"))
        if role is None:
            role = Role(code="platform_admin", name="平台管理员",
                        description="工作台平台级管理员", is_system=True)
            db.add(role)
            db.flush()
        for code, name, resource, action in PERMISSIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, name=name, resource=resource, action=action)
                db.add(permission)
                db.flush()
            if db.scalar(select(RolePermission.id).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id
            )) is None:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.add(User(username=username, password_hash=password_hash.hash(password),
                    display_name="平台管理员", role_id=role.id, is_active=True))
        db.commit()
        print(f"管理员账号 {username} 已创建。请立即清除引导环境变量，并安全保存凭据。")


if __name__ == "__main__":
    main()
