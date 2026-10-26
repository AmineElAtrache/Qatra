"""Load demo farmer + MA-001 when DB is up. Backend seat."""

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.domain.models import Farmer, Plot


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.email == "demo@qatra.local").first()
        if not farmer:
            farmer = Farmer(
                email="demo@qatra.local",
                password_hash=hash_password("demo-demo"),
                full_name="Demo Farmer",
                role="farmer",
                notify_opt_in=True,
            )
            db.add(farmer)
            db.commit()
            db.refresh(farmer)

        plot = db.query(Plot).filter(Plot.public_id == "MA-001").first()
        if not plot:
            plot = Plot(
                public_id="MA-001",
                owner_id=farmer.id,
                crop="citrus",
                stage="fruit_growth",
                irrigation_method="drip",
                area_ha=1.2,
                geom="SRID=4326;POLYGON((-7.5898 33.5731, -7.5888 33.5731, -7.5888 33.5740, -7.5898 33.5740, -7.5898 33.5731))",
            )
            db.add(plot)
            db.commit()
        print("Seeded demo@qatra.local / demo-demo and plot MA-001")
    finally:
        db.close()


if __name__ == "__main__":
    main()
