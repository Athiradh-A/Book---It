import concurrent.futures
import threading
from datetime import date, timedelta

from main import create_hold
from main import setup_database, create_hold

USERS = 10
ROOM = "E105"
SLOTS = [5]

# Find the next Monday-Friday date
booking_date = date.today()
while booking_date.weekday() >= 5:
    booking_date += timedelta(days=1)

# Make all users start together
barrier = threading.Barrier(USERS)


def simulate_user(user_id):
    try:
        barrier.wait()

        booking_id = create_hold(
            booking_date,
            ROOM,
            SLOTS
        )

        return f"User {user_id}: SUCCESS — hold ID {booking_id}"

    except Exception as error:
        return f"User {user_id}: FAILED — {error}"


if __name__ == "__main__":
    setup_database()
    print(f"Testing {USERS} users")
    print(f"Room: {ROOM}")
    print(f"Date: {booking_date}")
    print(f"Slot(s): {SLOTS}\n")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=USERS
    ) as executor:
        results = list(
            executor.map(
                simulate_user,
                range(1, USERS + 1)
            )
        )

    for result in results:
        print(result)

    successes = sum("SUCCESS" in result for result in results)
    print(f"\nSuccessful holds: {successes}/{USERS}")