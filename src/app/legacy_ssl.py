import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class LegacySSLAdapter(HTTPAdapter):
    """
    Адаптер, который включает поддержку устаревшего TLS renegotiation.
    Это необходимо, потому что сервер Белоруснефти использует старый TLS-стек.
    """
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)
