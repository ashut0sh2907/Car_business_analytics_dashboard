import os
from sqlalchemy import create_engine, Column, Integer, Float, Date, String
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///car_business.db"
)

# Detect database type and configure accordingly
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # SQLite multi-threading
    )
else:
    # PostgreSQL (Supabase) - no special connect_args needed
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class DailyRecord(Base):
    __tablename__ = "daily_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    ride_count = Column(Integer, default=0)
    earnings = Column(Integer, default=0)
    cng_expenses = Column(Integer, default=0)
    driver_pass_subscription = Column(Float, default=0)
    indrive_topup = Column(Float, default=0)
    odometer_start = Column(Float, nullable=True)
    odometer_end = Column(Float, nullable=True)
    daily_net = Column(Integer, default=0)

    @property
    def total_expenses(self):
        return (
            self.cng_expenses +
            (self.driver_pass_subscription or 0) +
            (self.indrive_topup or 0)
        )

    @property
    def distance_traveled(self):
        if self.odometer_start and self.odometer_end:
            return self.odometer_end - self.odometer_start
        return self.odometer_start or 0


class OtherExpense(Base):
    __tablename__ = "other_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    expenses = Column(Float, default=0)
    months = Column(String, nullable=True)
    car_emi = Column(Float, default=0)
    pg_rent = Column(Float, default=0)

    @property
    def total_other_expenses(self):
        """Calculate total expenses including EMI and rent"""
        return (
            (self.expenses or 0) +
            (self.car_emi or 0) +
            (self.pg_rent or 0)
        )


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
