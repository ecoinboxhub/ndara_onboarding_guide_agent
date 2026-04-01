# Customer AI ↔ Backend Bookings API Integration

Customer AI integrates with the backend Bookings & Working Hours API for appointment scheduling.

## Flow

1. **Customer requests appointment** → AI extracts date, time, service, customer name, and contact.
2. **Check availability** → AI fetches working hours and existing appointments for the date; computes if the requested slot is free.
3. **If slot is booked** → AI suggests alternative times from available slots.
4. **If slot is free** → AI creates the appointment via the backend.
5. **Confirmation** → AI returns a success message and appointment reference.

## Backend Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/bookings/working-hours/` | Business hours for each day |
| `GET /api/bookings/appointments/?start_date=...&end_date=...` | Existing appointments for date |
| `POST /api/bookings/appointments/` | Create new appointment |

## Configuration

| Env Variable | Description |
|--------------|-------------|
| `APPOINTMENT_BOOKING_URL` | Backend base URL  |
| `BOOKINGS_API_TOKEN` | Bearer token for auth (required if backend enforces it) |
| `BOOKINGS_BUSINESS_ID_MAP` | JSON map: `{"beauty_wellness_001": 5}` when business_id is string |

## Business ID Mapping

- Backend expects `business` as an integer.
- Customer AI uses `business_id` as string (e.g. `beauty_wellness_001`).
- If `business_id` is numeric (e.g. `"5"`), it is used directly.
- Otherwise, set `BOOKINGS_BUSINESS_ID_MAP` to map string IDs to backend integers.
