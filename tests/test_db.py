from app.database.session import SessionLocal
from app.database.models.member import Member
from scripts.init_db import init_db


def test_create_member():
    init_db()

    with SessionLocal() as db:
        member = Member(
            tag="#ABC123",
            name="Raphael",
            role="Member",
            trophies=9000,
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        assert member.id is not None
