import os
from itertools import count
from locust import HttpUser, task, constant
from app.core.security import create_access_token

EVENT_ID = int(os.getenv("EVENT_ID", "1"))
USER_COUNT = int(os.getenv("LOADTEST_USER_COUNT", "10000"))
user_indexes = count()

class EventApplicant(HttpUser):
    wait_time = constant(0)

    def on_start(self):
        index = next(user_indexes) % USER_COUNT
        username = f"loadtest_user_{index}"
        self.client.headers.update({
            "Authorization": f"Bearer {create_access_token(subject=username)}"
        })

    @task
    def apply_once(self):
        with self.client.post(
            f"/api/events/{EVENT_ID}/apply",
            name="/api/events/[event_id]/apply",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 409:
                response.success()
            else:
                response.failure(
                    f"Unexpected status {response.status_code}: {response.text[:200]}"
                )
        self.stop(True)
