import os
import tempfile
import unittest
from pathlib import Path


class AaharApiWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="aahar-api-tests-")
        db_path = Path(cls.temp_dir.name) / "aahar-tests.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        os.environ["SECRET_KEY"] = "test-only-secret"
        os.environ["CORS_ORIGINS"] = "http://testserver"
        os.environ["AHAAR_TESTING"] = "1"

        from fastapi.testclient import TestClient
        from app.database import Base
        from app.main import app, engine

        cls.client = TestClient(app)
        cls.base = Base
        cls.engine = engine

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.base.metadata.drop_all(bind=self.engine)
        self.base.metadata.create_all(bind=self.engine)

    def register(self, name, role):
        email = f"{role}-{name.lower().replace(' ', '.')}@example.com"
        response = self.client.post("/api/auth/register", json={
            "full_name": name,
            "email": email,
            "password": "valid-test-password",
            "role": role,
        })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        return result, {"Authorization": f"Bearer {result['access_token']}"}

    def test_profile_update_and_role_cannot_be_escalated(self):
        _, headers = self.register("Profile User", "ngo")
        updated = self.client.patch("/api/auth/me", headers=headers, json={
            "full_name": "Updated Profile User",
            "phone": "5550100",
            "address": "Community Center",
            "latitude": 16.7,
            "longitude": 74.2,
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["address"], "Community Center")
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).json()["phone"], "5550100")

        blocked = self.client.post("/api/auth/register", json={
            "full_name": "Untrusted Admin",
            "email": "untrusted-admin@example.com",
            "password": "valid-test-password",
            "role": "admin",
        })
        self.assertEqual(blocked.status_code, 422)

    def test_donor_request_delivery_and_notification_lifecycle(self):
        _, donor_headers = self.register("Food Donor", "donor")
        self.client.patch("/api/auth/me", headers=donor_headers, json={
            "full_name": "Food Donor",
            "latitude": 16.705,
            "longitude": 74.243,
        })
        _, ngo_headers = self.register("Community NGO", "ngo")
        self.client.patch("/api/auth/me", headers=ngo_headers, json={
            "full_name": "Community NGO",
            "latitude": 16.714,
            "longitude": 74.252,
        })
        _, volunteer_headers = self.register("Delivery Volunteer", "volunteer")

        listing_response = self.client.post("/api/food/listings", headers=donor_headers, json={
            "name": "Fresh Meals",
            "type": "Cooked",
            "quantity": 5,
            "unit": "meals",
            "expiry_hours": 4,
            "address": "Main Street",
            "latitude": 16.705,
            "longitude": 74.243,
        })
        self.assertEqual(listing_response.status_code, 200, listing_response.text)
        listing = listing_response.json()
        self.assertEqual(listing["address"], "Main Street")
        self.assertEqual(listing["quantity"], 5)

        too_many = self.client.post("/api/requests", headers=ngo_headers, json={
            "listing_id": listing["id"],
            "requested_quantity": 6,
        })
        self.assertEqual(too_many.status_code, 400)

        request_response = self.client.post("/api/requests", headers=ngo_headers, json={
            "listing_id": listing["id"],
            "requested_quantity": 3,
        })
        self.assertEqual(request_response.status_code, 200, request_response.text)
        request = request_response.json()
        inbox = self.client.get("/api/requests/inbox", headers=donor_headers)
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(inbox.json()[0]["listing_name"], "Fresh Meals")

        accepted = self.client.patch(
            f"/api/requests/{request['id']}",
            headers=donor_headers,
            params={"status": "accepted"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        delivery_response = self.client.get("/api/deliveries", headers=volunteer_headers)
        self.assertEqual(delivery_response.status_code, 200, delivery_response.text)
        delivery = delivery_response.json()[0]
        self.assertEqual(delivery["listing_name"], "Fresh Meals")

        claimed = self.client.post(f"/api/deliveries/{delivery['id']}/claim", headers=volunteer_headers)
        self.assertEqual(claimed.status_code, 200, claimed.text)
        location = self.client.post(
            f"/api/deliveries/{delivery['id']}/location",
            headers=volunteer_headers,
            json={"latitude": 16.71, "longitude": 74.25},
        )
        self.assertEqual(location.status_code, 200, location.text)
        for status in ("picked_up", "on_the_way", "delivered"):
            result = self.client.patch(
                f"/api/deliveries/{delivery['id']}/status",
                headers=volunteer_headers,
                params={"status": status},
            )
            self.assertEqual(result.status_code, 200, result.text)

        completed = self.client.get("/api/requests/mine", headers=ngo_headers)
        self.assertEqual(completed.json()[0]["status"], "completed")
        remaining = self.client.get("/api/food/listings").json()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["quantity"], 2)

        donor_locations = self.client.get(
            f"/api/deliveries/{delivery['id']}/locations",
            headers=donor_headers,
        )
        self.assertEqual(donor_locations.status_code, 200)
        self.assertEqual(donor_locations.json()[0]["latitude"], 16.71)
        notifications = self.client.get("/api/notifications", headers=donor_headers)
        self.assertEqual(notifications.status_code, 200)
        self.assertTrue(any(item["title"] == "Food delivered" for item in notifications.json()))
        self.assertEqual(self.client.post("/api/notifications/read-all", headers=donor_headers).status_code, 200)
        self.assertTrue(all(item["is_read"] for item in self.client.get("/api/notifications", headers=donor_headers).json()))

    def test_authorization_and_listing_deletion(self):
        _, donor_headers = self.register("Listing Owner", "donor")
        _, other_donor_headers = self.register("Other Donor", "donor")
        listing_response = self.client.post("/api/food/listings", headers=donor_headers, json={
            "name": "Available Fruit",
            "quantity": 2,
            "expiry_hours": 3,
        })
        listing_id = listing_response.json()["id"]

        unauthorized = self.client.get("/api/admin/overview", headers=donor_headers)
        self.assertEqual(unauthorized.status_code, 403)
        forbidden_delete = self.client.delete(f"/api/food/listings/{listing_id}", headers=other_donor_headers)
        self.assertEqual(forbidden_delete.status_code, 403)
        deleted = self.client.delete(f"/api/food/listings/{listing_id}", headers=donor_headers)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/api/food/listings").json(), [])

        from app.database import SessionLocal
        from app.models.models import User
        from app.security import create_access_token, hash_password

        with SessionLocal() as db:
            admin = User(
                full_name="Trusted Admin",
                email="trusted-admin@example.com",
                password_hash=hash_password("valid-test-password"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
        admin_users = self.client.get("/api/admin/users", headers=admin_headers)
        self.assertEqual(admin_users.status_code, 200, admin_users.text)
        self.assertNotIn("password_hash", admin_users.text)


if __name__ == "__main__":
    unittest.main()
