from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telbot_llm.models import Campaign, Donation, NGO, User  # Assuming these models exist
from telbot_llm.config import DATABASE_URL

def seed_demo_data():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create demo NGOs
    ngos = [
        NGO(name="Flood Relief NGO", wallet_address="0x1234567890abcdef1234567890abcdef12345678"),
        NGO(name="Earthquake Relief NGO", wallet_address="0xabcdef1234567890abcdef1234567890abcdef12"),
    ]

    # Create demo campaigns
    campaigns = [
        Campaign(title="Flood Relief Campaign", description="Help us provide aid to flood victims.", ngo=ngos[0]),
        Campaign(title="Earthquake Relief Campaign", description="Support earthquake recovery efforts.", ngo=ngos[1]),
    ]

    # Create demo users
    users = [
        User(telegram_id="123456789", username="demo_user1"),
        User(telegram_id="987654321", username="demo_user2"),
    ]

    # Create demo donations
    donations = [
        Donation(amount=0.1, currency="AVAX", user=users[0], campaign=campaigns[0]),
        Donation(amount=50, currency="USDT", user=users[1], campaign=campaigns[1]),
    ]

    # Add all to session and commit
    session.add_all(ngos + campaigns + users + donations)
    session.commit()
    session.close()

if __name__ == "__main__":
    seed_demo_data()