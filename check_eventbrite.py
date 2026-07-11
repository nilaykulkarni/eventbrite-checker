"""
Checks availability for St Thomas' antenatal classes (Saturday class and
Weekday class) by scanning several months ahead automatically, using
Eventbrite's public "checkoutfairy" /dates endpoint (found via DevTools -
Network tab). This returns every scheduled date in a given month along with
its availability, so newly added dates are picked up automatically without
needing to edit this script.

Sends a WhatsApp message via CallMeBot listing any date(s) that currently
have an open slot, grouped by event.

No Eventbrite API token needed - this endpoint is public and unauthenticated.

Required environment variables (set as GitHub Actions secrets, or export
locally before running):
  CALLMEBOT_PHONE    - your WhatsApp number, international format, no + or spaces
                        e.g. 447123456789
  CALLMEBOT_APIKEY   - the API key CallMeBot sent you after you messaged it
"""

import os
import sys
from datetime import date
import requests

DATES_URL_TEMPLATE = (
    "https://checkoutfairy.ernt4vxu.ext.eventbrite.com/main/event/{event_id}"
    "/dates?tzIdentifier=Europe/London&month={month}&year={year}"
)

# Only care about slots up to and including the first week of September 2026.
CUTOFF_DATE = date(2026, 9, 10)

EVENTS = [
    {
        "name": "Saturday class",
        "event_id": "71647504615",
        "event_url": (
            "https://www.eventbrite.co.uk/e/st-thomas-saturdays-antenatal-"
            "classes-labour-breastfeeding-and-baby-tickets-71647504615"
        ),
    },
    {
        "name": "Weekday class",
        "event_id": "50729907519",
        "event_url": (
            "https://www.eventbrite.co.uk/e/st-thomas-weekdays-antenatal-"
            "classes-labour-breatsfeeding-and-baby-tickets-50729907519"
        ),
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


def months_to_check():
    """Returns (year, month) tuples from this month through CUTOFF_DATE's month."""
    today = date.today()
    y, m = today.year, today.month
    months = []
    while (y, m) <= (CUTOFF_DATE.year, CUTOFF_DATE.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def get_month_dates(event_id: str, year: int, month: int):
    """Returns the eventDates list for one event/month, or [] on any issue."""
    url = DATES_URL_TEMPLATE.format(event_id=event_id, month=month, year=year)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("eventDates", [])


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

        for year, month in months_to_check():
            try:
                event_dates = get_month_dates(event["event_id"], year, month)
            except requests.HTTPError as e:
                print(f"  {year}-{month:02d}: error calling dates endpoint: {e}", file=sys.stderr)
                continue
            except (ValueError, KeyError) as e:
                print(f"  {year}-{month:02d}: unexpected response shape: {e}", file=sys.stderr)
                continue

            for entry in event_dates:
                d = entry.get("date")
                try:
                    d_parsed = date.fromisoformat(d)
                except (TypeError, ValueError):
                    print(f"  Skipping unparseable date entry: {entry}", file=sys.stderr)
                    continue

                if d_parsed > CUTOFF_DATE:
                    continue  # beyond the range we care about

                sold_out = entry.get("soldOut", True)
                checkout_enabled = entry.get("checkoutEnabled", False)
                print(f"  {d}: soldOut={sold_out}, checkoutEnabled={checkout_enabled}")
                if not sold_out and checkout_enabled:
                    available_dates.append(d)

        if available_dates:
            dates_list = ", ".join(sorted(available_dates))
            message_lines.append(f"{event['name']}: {dates_list} - {event['event_url']}")
            print(f"  -> Available: {dates_list}")
        else:
            print("  -> No available dates in the scanned months.")

    if message_lines:
        message = "Antenatal class slot(s) available!\n" + "\n".join(message_lines)
        send_whatsapp(message)
        print("WhatsApp sent.")
    else:
        print("Nothing available across either event right now.")


if __name__ == "__main__":
    main()
