import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.clients import router
from database.session import get_session


def _mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_session] = _mock_session

    @application.middleware("http")
    async def mock_auth(request, call_next):
        request.state.org_id = "org_test_123"
        request.state.user_id = "user_test_456"
        request.state.user_role = "org:admin"
        response = await call_next(request)
        return response

    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


MOCK_ORG_ID = "org_test_123"


def _make_client_record(name="Test Client", client_id=1):
    from models.client import Client

    rec = Client(name=name, agency_id=MOCK_ORG_ID)
    rec.id = client_id
    rec.org_id = MOCK_ORG_ID
    return rec


class TestClientEndpoints:
    def test_list_clients_empty(self, client):
        with patch("routers.clients._client_service") as svc:
            svc.list_all = AsyncMock(return_value=[])
            response = client.get(f"/organizations/{MOCK_ORG_ID}/clients")
            assert response.status_code == 200
            assert response.json() == []

    def test_create_client(self, client):
        created = _make_client_record("Acme Corp")
        with patch("routers.clients._client_service") as svc:
            svc.create = AsyncMock(return_value=created)
            response = client.post(
                f"/organizations/{MOCK_ORG_ID}/clients",
                json={"name": "Acme Corp"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Acme Corp"

    def test_create_client_missing_name(self, client):
        response = client.post(
            f"/organizations/{MOCK_ORG_ID}/clients",
            json={"name": ""},
        )
        assert response.status_code == 400

    def test_create_client_with_settings(self, client):
        created = _make_client_record("Acme Corp", client_id=2)
        with patch("routers.clients._client_service") as svc:
            svc.create = AsyncMock(return_value=created)
            response = client.post(
                f"/organizations/{MOCK_ORG_ID}/clients",
                json={
                    "name": "Acme Corp",
                    "settings": {
                        "timezone": "UTC",
                        "branding": {"primaryColor": "#10B981"},
                    },
                },
            )
            assert response.status_code == 201
            assert response.json()["name"] == "Acme Corp"

    def test_get_client(self, client):
        found = _make_client_record("Found Corp")
        with patch("routers.clients._client_service") as svc:
            svc.get_by_id = AsyncMock(return_value=found)
            response = client.get(f"/organizations/{MOCK_ORG_ID}/clients/1")
            assert response.status_code == 200
            assert response.json()["name"] == "Found Corp"

    def test_get_client_not_found(self, client):
        with patch("routers.clients._client_service") as svc:
            svc.get_by_id = AsyncMock(return_value=None)
            response = client.get(f"/organizations/{MOCK_ORG_ID}/clients/999")
            assert response.status_code == 404

    def test_update_client(self, client):
        existing = _make_client_record("Old Name")
        updated = _make_client_record("New Name")
        with patch("routers.clients._client_service") as svc:
            svc.get_by_id = AsyncMock(return_value=existing)
            svc.update = AsyncMock(return_value=updated)
            response = client.patch(
                f"/organizations/{MOCK_ORG_ID}/clients/1",
                json={"name": "New Name"},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "New Name"

    def test_delete_client(self, client):
        existing = _make_client_record("To Delete")
        with patch("routers.clients._client_service") as svc:
            svc.get_by_id = AsyncMock(return_value=existing)
            svc.hard_delete = AsyncMock(return_value=True)
            response = client.delete(f"/organizations/{MOCK_ORG_ID}/clients/1")
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_delete_client_not_found(self, client):
        with patch("routers.clients._client_service") as svc:
            svc.get_by_id = AsyncMock(return_value=None)
            response = client.delete(f"/organizations/{MOCK_ORG_ID}/clients/999")
            assert response.status_code == 404

    def test_cross_org_forbidden(self, client):
        response = client.get("/organizations/org_other_999/clients")
        assert response.status_code == 403
