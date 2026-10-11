import csv
import uuid
from datetime import date
import psycopg2
from psycopg2 import sql, errors
import getpass
import time
import uuid

DB_CONFIG = {
    "host": "localhost",
    "database": "campusroom",
    "user": getpass.getuser(),
    "port": 5432
}

CSV_FILE = '/Users/dhyan/Desktop/genesis /campusroom-backend/data/room_timetable_monday_friday.csv'
HOLD_MINUTES = 5
WEEKDAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}


def connect():
    return psycopg2.connect(**DB_CONFIG)


def setup_database():
    conn = connect()

    try:
        # Create tables
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS classroom_timetable (
                        day VARCHAR(10) NOT NULL,
                        room_name VARCHAR(10) NOT NULL,
                        PRIMARY KEY (day, room_name)
                    )
                """)

                # Add slot columns if missing
                for i in range(1, 12):
                    cur.execute(sql.SQL("""
                        ALTER TABLE classroom_timetable
                        ADD COLUMN IF NOT EXISTS {} SMALLINT
                        NOT NULL DEFAULT 1
                    """).format(sql.Identifier(f"slot_{i}")))

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS room_reservations (
                        booking_id UUID NOT NULL,
                        booking_date DATE NOT NULL,
                        room_name VARCHAR(10) NOT NULL,
                        slot_index SMALLINT NOT NULL
                            CHECK (slot_index BETWEEN 1 AND 11),
                        status VARCHAR(10) NOT NULL
                            CHECK (status IN ('held', 'confirmed')),
                        expires_at TIMESTAMPTZ,
                        PRIMARY KEY (
                            booking_date, room_name, slot_index
                        )
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS booking_queue (
                        ticket_id BIGSERIAL PRIMARY KEY,
                        booking_id UUID NOT NULL UNIQUE,
                        booking_date DATE NOT NULL,
                        room_name VARCHAR(10) NOT NULL,
                        slots SMALLINT[] NOT NULL,
                        status VARCHAR(12) NOT NULL DEFAULT 'waiting',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)

        # Import CSV after creating the tables
        with open(CSV_FILE, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            with conn:
                with conn.cursor() as cur:
                    for row in reader:
                        day = row["day"].strip().capitalize()

                        if day not in WEEKDAYS:
                            continue

                        slots = [
                            int(row[f"slot_{i}"])
                            for i in range(1, 12)
                        ]

                        if any(value not in (0, 1) for value in slots):
                            raise ValueError(
                                f"Invalid slot values for {row['room_name']}"
                            )

                        cur.execute("""
                            INSERT INTO classroom_timetable (
                                day, room_name,
                                slot_1, slot_2, slot_3, slot_4, slot_5,
                                slot_6, slot_7, slot_8, slot_9, slot_10,
                                slot_11
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (day, room_name) DO UPDATE SET
                                slot_1 = EXCLUDED.slot_1,
                                slot_2 = EXCLUDED.slot_2,
                                slot_3 = EXCLUDED.slot_3,
                                slot_4 = EXCLUDED.slot_4,
                                slot_5 = EXCLUDED.slot_5,
                                slot_6 = EXCLUDED.slot_6,
                                slot_7 = EXCLUDED.slot_7,
                                slot_8 = EXCLUDED.slot_8,
                                slot_9 = EXCLUDED.slot_9,
                                slot_10 = EXCLUDED.slot_10,
                                slot_11 = EXCLUDED.slot_11
                        """, (day, row["room_name"].strip(), *slots))

    finally:
        conn.close()

def validate_request(booking_date, slots):
    if booking_date < date.today():
        raise ValueError("Booking date cannot be in the past.")
    if booking_date.strftime("%A") not in WEEKDAYS:
        raise ValueError("Bookings are allowed Monday to Friday only.")

    slots = sorted(set(int(s) for s in slots))
    if not slots or any(s < 1 or s > 11 for s in slots):
        raise ValueError("Slot numbers must be between 1 and 11.")
    return slots


def find_available_rooms(booking_date, slots):
    slots = validate_request(booking_date, slots)
    day = booking_date.strftime("%A")

    conditions = sql.SQL(" AND ").join(
        sql.SQL("t.{} = 0").format(sql.Identifier(f"slot_{s}"))
        for s in slots
    )

    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM room_reservations
                    WHERE status = 'held' AND expires_at <= NOW()
                """)

                cur.execute(sql.SQL("""
                    SELECT t.room_name
                    FROM classroom_timetable t
                    WHERE t.day = %s AND {}
                      AND NOT EXISTS (
                          SELECT 1 FROM room_reservations r
                          WHERE r.booking_date = %s
                            AND r.room_name = t.room_name
                            AND r.slot_index = ANY(%s)
                      )
                    ORDER BY t.room_name
                """).format(conditions), (day, booking_date, slots))

                return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def create_hold(booking_date, room_name, slots):
    slots = validate_request(booking_date, slots)
    room_name = room_name.strip().upper()
    day = booking_date.strftime("%A")
    booking_id = uuid.uuid4()

    # Step 1: Join the FIFO queue.
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                # Serialize queue ticket assignment for this room/date.
                cur.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (room_name, str(booking_date))
                )

                cur.execute("""
                    INSERT INTO booking_queue
                        (booking_id, booking_date, room_name, slots)
                    VALUES (%s, %s, %s, %s)
                    RETURNING ticket_id
                """, (str(booking_id), booking_date, room_name, slots))

                ticket_id = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"Queue ticket: {ticket_id}. Waiting for your turn...")

    # Step 2: Wait until all earlier requests for this room/date finish.
    while True:
        conn = connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT status
                        FROM booking_queue
                        WHERE ticket_id = %s
                        FOR UPDATE
                    """, (ticket_id,))
                    row = cur.fetchone()

                    if not row or row[0] != "waiting":
                        raise ValueError("Queue request is no longer waiting.")

                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1
                            FROM booking_queue
                            WHERE booking_date = %s
                              AND room_name = %s
                              AND ticket_id < %s
                              AND status IN ('waiting', 'processing')
                        )
                    """, (booking_date, room_name, ticket_id))

                    has_earlier_request = cur.fetchone()[0]

                    if not has_earlier_request:
                        cur.execute("""
                            UPDATE booking_queue
                            SET status = 'processing'
                            WHERE ticket_id = %s
                        """, (ticket_id,))
                        break
        finally:
            conn.close()

        time.sleep(0.2)

    # Step 3: Attempt the actual hold. PostgreSQL's unique constraint
    # remains the final protection against double booking.
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM room_reservations
                    WHERE status = 'held' AND expires_at <= NOW()
                """)

                cur.execute("""
                    SELECT room_name
                    FROM classroom_timetable
                    WHERE day = %s AND room_name = %s
                    FOR UPDATE
                """, (day, room_name))

                if not cur.fetchone():
                    raise ValueError("Classroom not found for this weekday.")

                conditions = sql.SQL(" AND ").join(
                    sql.SQL("{} = 0").format(
                        sql.Identifier(f"slot_{slot}")
                    )
                    for slot in slots
                )

                cur.execute(sql.SQL("""
                    SELECT room_name
                    FROM classroom_timetable
                    WHERE day = %s AND room_name = %s AND {}
                """).format(conditions), (day, room_name))

                if not cur.fetchone():
                    raise ValueError("Classroom is occupied in a requested slot.")

                cur.execute("""
                    INSERT INTO room_reservations
                        (booking_id, booking_date, room_name,
                         slot_index, status, expires_at)
                    SELECT %s, %s, %s, slot, 'held',
                           NOW() + (%s * INTERVAL '1 minute')
                    FROM unnest(%s::smallint[]) AS slot
                """, (
                    str(booking_id), booking_date, room_name,
                    HOLD_MINUTES, slots
                ))

                cur.execute("""
                    UPDATE booking_queue
                    SET status = 'granted'
                    WHERE ticket_id = %s
                """, (ticket_id,))

        print(f"Your turn! Queue ticket: {ticket_id}")
        return booking_id

    except Exception:
        # Release the queue for the next user, even if this request fails.
        conn.rollback()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE booking_queue
                    SET status = 'failed'
                    WHERE ticket_id = %s
                """, (ticket_id,))
        raise
    finally:
        conn.close()


def confirm_booking(booking_id):
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE room_reservations
                    SET status = 'confirmed', expires_at = NULL
                    WHERE booking_id = %s
                      AND status = 'held'
                      AND expires_at > NOW()
                    RETURNING room_name
                """, (str(booking_id),))

                if not cur.fetchall():
                    raise ValueError(
                        "Hold expired or booking was already confirmed."
                    )

        return True
    finally:
        conn.close()


def main():
    setup_database()
    print("\nCampusRoom")
    print("1. Check available classrooms")
    print("2. Hold a classroom")
    print("3. Confirm a booking")

    choice = input("Choose action: ").strip()

    try:
        if choice in ("1", "2"):
            booking_date = date.fromisoformat(
                input("Date (YYYY-MM-DD): ").strip()
            )
            slots = input("Slot numbers (e.g. 3 or 3,5,7): ")
            slots = [int(s.strip()) for s in slots.split(",")]

            if choice == "1":
                rooms = find_available_rooms(booking_date, slots)
                print("\nAvailable rooms:", ", ".join(rooms) if rooms else "None")

            else:
                room = input("Classroom name (e.g. E202): ").strip().upper()
                booking_id = create_hold(booking_date, room, slots)
                print("\nTemporary hold created!")
                print("Booking ID:", booking_id)
                print(f"Confirm within {HOLD_MINUTES} minutes.")

        elif choice == "3":
            booking_id = input("Booking ID: ").strip()
            confirm_booking(booking_id)
            print("Booking confirmed!")

        else:
            print("Invalid choice.")

    except (ValueError, psycopg2.Error) as error:
        print("Error:", error)

if __name__ == "__main__":
    main()