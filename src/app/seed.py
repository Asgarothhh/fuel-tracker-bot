# src/app/seed.py
from src.app.db import get_db_session, init_db
from src.app.models import Role, Permission

def seed_roles_and_permissions():
    init_db()
    with get_db_session() as db:
        # базовые пермишены
        perms = [
            ("admin:manage", "Полный доступ администратора"),
            ("user:confirm", "Подтверждать заправки"),
            ("user:upload_receipt", "Загружать чеки"),
        ]
        for name, desc in perms:
            p = db.query(Permission).filter_by(name=name).first()
            if not p:
                p = Permission(name=name, description=desc)
                db.add(p)
        db.flush()

        # роли
        admin_role = db.query(Role).filter_by(role_name="admin").first()
        if not admin_role:
            admin_role = Role(role_name="admin", description="Администратор системы")
            db.add(admin_role)
        user_role = db.query(Role).filter_by(role_name="user").first()
        if not user_role:
            user_role = Role(role_name="user", description="Обычный пользователь")
            db.add(user_role)
        db.flush()

        # привязать пермишены
        perm_admin = db.query(Permission).filter_by(name="admin:manage").one()
        perm_confirm = db.query(Permission).filter_by(name="user:confirm").one()
        perm_upload = db.query(Permission).filter_by(name="user:upload_receipt").one()

        if perm_admin not in admin_role.permissions:
            admin_role.permissions.append(perm_admin)
        if perm_confirm not in user_role.permissions:
            user_role.permissions.append(perm_confirm)
        if perm_upload not in user_role.permissions:
            user_role.permissions.append(perm_upload)

        db.commit()

if __name__ == "__main__":
    seed_roles_and_permissions()
    print("Seed completed: roles and permissions created.")
