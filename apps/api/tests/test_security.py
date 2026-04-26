import hashlib
import hmac
import time
from urllib.parse import urlencode

from app.core.security import verify_telegram_webapp_init_data


def test_verify_telegram_webapp_init_data() -> None:
    token = "123456:test"
    data = {
        "auth_date": str(int(time.time())),
        "query_id": "abc",
        "user": '{"id":10001,"first_name":"Dev"}',
    }
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    parsed = verify_telegram_webapp_init_data(urlencode(data), token)

    assert parsed["query_id"] == "abc"
    assert "10001" in parsed["user"]
