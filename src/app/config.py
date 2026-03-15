from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TOKEN_SALT = os.getenv("TOKEN_SALT")
CODE_LENGTH = int(os.getenv("CODE_LENGTH", "6"))
CODE_TTL_HOURS = int(os.getenv("CODE_TTL_HOURS", "24"))
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

# --- Белоруснефть API ---
BEL_PASSWORD = os.getenv("BEL_PASSWORD")
BEL_EMITENT_ID = os.getenv("BEL_EMITENT_ID")
BEL_CONTRACT_ID = os.getenv("BEL_CONTRACT_ID")

