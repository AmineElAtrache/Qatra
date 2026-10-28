"""Load demo farmer + advisor + MA-001 when DB is up. Backend seat."""

from app.core.database import Base, SessionLocal, engine
from app.core.geo import default_ma001_geojson, geojson_to_text
from app.core.security import hash_password
from app.domain.models import Farmer, Plot


def _ensure_user(
    db,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str,
) -> Farmer:
    user = db.query(Farmer).filter(Farmer.email == email).first()
    if user:
        if user.role != role:
            user.role = role
            db.commit()
            db.refresh(user)
        return user
    user = Farmer(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        notify_opt_in=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        farmer = _ensure_user(
            db,
            email="farmer@example.com",
            password="demo-demo",
            full_name="Demo Farmer",
            role="farmer",
        )
        advisor = _ensure_user(
            db,
            email="advisor@example.com",
            password="demo-demo",
            full_name="Demo Advisor",
            role="advisor",
        )

        geom_text = geojson_to_text(default_ma001_geojson())
        plot = db.query(Plot).filter(Plot.public_id == "MA-001").first()
        if not plot:
            plot = Plot(
                public_id="MA-001",
                owner_id=farmer.id,
                crop="citrus",
                stage="fruit_growth",
                irrigation_method="drip",
                area_ha=1.2,
                geom=geom_text,
            )
            db.add(plot)
            db.commit()
        else:
            changed = False
            if plot.owner_id != farmer.id:
                plot.owner_id = farmer.id
                changed = True
            if not plot.geom:
                plot.geom = geom_text
                changed = True
            if changed:
                db.commit()

        print("Roles ready:")
        print(f"  farmer  {farmer.email} / demo-demo  (role={farmer.role})")
        print(f"  advisor {advisor.email} / demo-demo  (role={advisor.role})")
        print("Plot: MA-001 (GeoJSON stored)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
