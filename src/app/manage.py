# src/scripts/manage.py
from src.app.db import init_db
from src.app.seed import seed_roles_and_permissions

def main():
    init_db()
    seed_roles_and_permissions()
    print("DB initialized and seeded.")

if __name__ == "__main__":
    main()
