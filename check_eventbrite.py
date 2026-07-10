"""
Checks availability for the St Thomas' Saturday Antenatal Class across
several specific dates, using Eventbrite's public "checkoutfairy" sessions
endpoint (found via DevTools - Network tab). Sends a WhatsApp message via
CallMeBot listing any date(s) that currently have an open slot.

No Eventbrite API token needed - this endpoint is public and unauthenticated.

Required environment variables (set as GitHub Actions secrets, or export
locally before running):
  CALLMEBOT_PHONE    - your WhatsApp number, international format, no + or spaces
                        e.g. 447123456789
  CALLMEBOT_APIKEY   - the API key CallMeBot sent you after you messaged it

Optional:
  EVENT_URL          - link to include in the WhatsApp message (defaults below)
"""

import os
import sys
import requests

EVENT_ID = "71647504615"

# Add or remove dates here (format: YYYY-MM-DD).
DATES_TO_CHECK = [
    "2026-07-18",
    "2026-08-15",
    "2026-08-22",
    "2026-09-05",
]

SESSIONS_URL_TEMPLATE = (
    "https://checkoutfairy.ernt4vxu.ext.eventbrite.com/main/event/{event_id}"
    "/date/{date}/sessions?tzIdentifier=Europe/London"
)

CALLMEBOT_PHONE = os.environ["CALLMEBOT_PHONE"]
CALLMEBOT_APIKEY = os.environ["CALLMEBOT_APIKEY"]
EVENT_URL = os.environ.get(
    "EVENT_URL",
    "https://www.eventbrite.co.uk/e/st-thomas-saturdays-antenatal-classes-labour-breastfeeding-and-baby-tickets-71647504615",
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.eventbrite.co.uk/",
    "Origin": "https://www.eventbrite.co.uk",
}


def check_date_availability(date: str) -> bool:
    """Returns True if the session on this date currently has an open slot."""
    url = SESSIONS_URL_TEMPLATE.format(event_id=EVENT_ID, date=date)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    sessions = resp.json()

    if not sessions:
        print(f"{date}: no session data returned.")
        return False

    session = sessions[0]
    sold_out = session.get("soldOut", True)
    checkout_enabled = session.get("checkoutEnabled", False)
    is_published = session.get("isPublished", False)

    print(
        f"{date}: soldOut={sold_out}, checkoutEnabled={checkout_enabled}, "
        f"isPublished={is_published}"
    )

    return is_published and not sold_out and checkout_enabled


def send_whatsapp(message: str) -> None:
    url = "https://api.callmebot.com/whatsapp.php"
    params = {"phone": CALLMEBOT_PHONE, "text": message, "apikey": CALLMEBOT_APIKEY}
    r = requests.get(url, params=params, timeout=20)
    print(f"CallMeBot response: {r.status_code} {r.text[:200]}")


def main():
    available_dates = []

    for date in DATES_TO_CHECK:
        try:
            if check_date_availability(date):
                available_dates.append(date)
        except requests.HTTPError as e:
            print(f"{date}: error calling sessions endpoint: {e}", file=sys.stderr)
        except (ValueError, KeyError, IndexError) as e:
            print(f"{date}: unexpected response shape: {e}", file=sys.stderr)

    if available_dates:
        dates_list = ", ".join(available_dates)
        message = (
            "A slot has opened for the St Thomas' Saturday Antenatal Class "
            f"on: {dates_list}. Book now: {EVENT_URL}"
        )
        send_whatsapp(message)
        print(f"Available dates found ({dates_list}) - WhatsApp sent.")
    else:
        print("No available dates right now.")


if __name__ == "__main__":
    main()
