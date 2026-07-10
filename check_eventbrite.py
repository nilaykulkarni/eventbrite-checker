"""
Checks availability for St Thomas' antenatal classes (both the Saturday
class and the Weekday class) across several specific dates each, using
Eventbrite's public "checkoutfairy" sessions endpoint (found via DevTools -
Network tab). Sends a WhatsApp message via CallMeBot listing any date(s)
that currently have an open slot, per event.

No Eventbrite API token needed - this endpoint is public and unauthenticated.

Required environment variables (set as GitHub Actions secrets, or export
locally before running):
  CALLMEBOT_PHONE    - your WhatsApp number, international format, no + or spaces
                        e.g. 447123456789
  CALLMEBOT_APIKEY   - the API key CallMeBot sent you after you messaged it
"""

import os
import sys
import requests

SESSIONS_URL_TEMPLATE = (
    "https://checkoutfairy.ernt4vxu.ext.eventbrite.com/main/event/{event_id}"
    "/date/{date}/sessions?tzIdentifier=Europe/London"
)

# Each event has its own Eventbrite event ID, a human-readable name for the
# WhatsApp message, its own booking URL, and the list of dates to check
# (format: YYYY-MM-DD).
EVENTS = [
    {
        "name": "Saturday class",
        "event_id": "71647504615",
        "event_url": (
            "https://www.eventbrite.co.uk/e/st-thomas-saturdays-antenatal-"
            "classes-labour-breastfeeding-and-baby-tickets-71647504615"
        ),
        "dates": [
            "2026-07-18",
            "2026-08-15",
            "2026-08-22",
            "2026-09-05",
        ],
    },
    {
        "name": "Weekday class",
        "event_id": "50729907519",
        "event_url": (
            "https://www.eventbrite.co.uk/e/st-thomas-weekdays-antenatal-"
            "classes-labour-breatsfeeding-and-baby-tickets-50729907519"
        ),
        "dates": [
            "2026-07-21",
            "2026-07-23",
            "2026-07-28",
            "2026-08-04",
            "2026-08-06",
            "2026-08-11",
            "2026-08-20",
            "2026-08-25",
            "2026-09-08",
            "2026-09-10",
        ],
    },
]

CALLMEBOT_PHONE = os.environ["CALLMEBOT_PHONE"]
CALLMEBOT_APIKEY = os.environ["CALLMEBOT_APIKEY"]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.eventbrite.co.uk/",
    "Origin": "https://www.eventbrite.co.uk",
}


def check_date_availability(event_id: str, date: str) -> bool:
    """Returns True if the session on this date currently has an open slot."""
    url = SESSIONS_URL_TEMPLATE.format(event_id=event_id, date=date)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    sessions = resp.json()

    if not sessions:
        print(f"  {date}: no session data returned.")
        return False

    session = sessions[0]
    sold_out = session.get("soldOut", True)
    checkout_enabled = session.get("checkoutEnabled", False)
    is_published = session.get("isPublished", False)

    print(
        f"  {date}: soldOut={sold_out}, checkoutEnabled={checkout_enabled}, "
        f"isPublished={is_published}"
    )

    return is_published and not sold_out and checkout_enabled


def send_whatsapp(message: str) -> None:
    url = "https://api.callmebot.com/whatsapp.php"
    params = {"phone": CALLMEBOT_PHONE, "text": message, "apikey": CALLMEBOT_APIKEY}
    r = requests.get(url, params=params, timeout=20)
    print(f"CallMeBot response: {r.status_code} {r.text[:200]}")


def main():
    message_lines = []

    for event in EVENTS:
        print(f"Checking {event['name']} ({event['event_id']}):")
        available_dates = []

        for date in event["dates"]:
            try:
                if check_date_availability(event["event_id"], date):
                    available_dates.append(date)
            except requests.HTTPError as e:
                print(f"  {date}: error calling sessions endpoint: {e}", file=sys.stderr)
            except (ValueError, KeyError, IndexError) as e:
                print(f"  {date}: unexpected response shape: {e}", file=sys.stderr)

        if available_dates:
            dates_list = ", ".join(available_dates)
            message_lines.append(
                f"{event['name']}: {dates_list} - {event['event_url']}"
            )
            print(f"  -> Available: {dates_list}")
        else:
            print("  -> No available dates right now.")

    if message_lines:
        message = "Antenatal class slot(s) available!\n" + "\n".join(message_lines)
        send_whatsapp(message)
        print("WhatsApp sent.")
    else:
        print("Nothing available across either event right now.")


if __name__ == "__main__":
    main()
