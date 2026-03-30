from app.models import User


async def test_user_created(user: User):
    assert user.id is not None
    assert user.username.startswith("testuser_")
    assert user.email.startswith("test_")
    assert user.is_active is True
