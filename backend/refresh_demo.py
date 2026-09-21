"""Re-apply the demo boards (a few cards per persona, two pending delegation offers) to the CURRENT
database. Idempotent — a card is added only if that person has none with the same title.

    cd backend && .venv/bin/python refresh_demo.py
"""

from app import create_app
from demo_cards import apply_demo_cards

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print({"cards_added": apply_demo_cards()})
