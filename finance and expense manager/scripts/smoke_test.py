import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def main() -> None:
    with client:
        login = client.post("/api/auth/login", json={"email": "demo@finance.ai", "password": "Demo@12345"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        dashboard = client.get("/api/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        tx = client.post(
            "/api/transactions",
            headers=headers,
            json={
                "kind": "expense",
                "amount": 42.5,
                "currency": "USD",
                "merchant": "Orbit Cafe",
                "description": "team coffee",
                "occurred_on": "2026-05-10",
            },
        )
        assert tx.status_code == 200, tx.text
        assistant = client.post("/api/assistant", headers=headers, json={"message": "How can I save more?"})
        assert assistant.status_code == 200, assistant.text
        print("Smoke test passed")


if __name__ == "__main__":
    main()
