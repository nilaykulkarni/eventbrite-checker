"""
Checks availability for the St Thomas' Saturday Antenatal Class on 18 July 2026
using Eventbrite's public "checkoutfairy" sessions endpoint (found via DevTools -
Network tab), and sends a WhatsApp message via CallMeBot if a slot opens up.

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

SESSIONS_URL = (
    "https://checkoutfairy.ernt4vxu.ext.eventbrite.com/main/event/71647504615"
    "/date/2026-07-18/sessions?tzIdentifier=Europe/London"
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


def check_availability() -> bool:
    """Returns True if the 18 July session currently has an open slot."""
    resp = requests.get(SESSIONS_URL, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    sessions = resp.json()

    if not sessions:
        print("No session data returned for this date.")
        return False

    session = sessions[0]
    sold_out = session.get("soldOut", True)
    checkout_enabled = session.get("checkoutEnabled", False)
    is_published = session.get("isPublished", False)

    print(
        f"soldOut={sold_out}, checkoutEnabled={checkout_enabled}, "
        f"isPublished={is_published}"
    )

    # Treat it as available if it's published, not sold out, and checkout is open.
    return is_published and not sold_out and checkout_enabled
    #return True


def send_whatsapp(message: str) -> None:
    url = "https://api.callmebot.com/whatsapp.php"
    params = {"phone": CALLMEBOT_PHONE, "text": message, "apikey": CALLMEBOT_APIKEY}
    r = requests.get(url, params=params, timeout=20)
    print(f"CallMeBot response: {r.status_code} {r.text[:200]}")


def main():
    try:
        available = check_availability()
    except requests.HTTPError as e:
        print(f"Error calling sessions endpoint: {e}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, IndexError) as e:
        print(f"Unexpected response shape: {e}", file=sys.stderr)
        sys.exit(1)

    if available:
        message = (
            "A slot has opened for the St Thomas' Saturday Antenatal Class "
            f"on 18 July! Book now: {EVENT_URL}"
        )
        send_whatsapp(message)
        print("Slot available - WhatsApp sent.")
    else:
        print("Still sold out / not open.")


if __name__ == "__main__":
    main()
