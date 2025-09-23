from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.database import get_db
from models.models import AuthUser
from auth.utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ✅ Hardcoded users list
USERS_TO_CREATE = [
    ("Murtaza", "murtaza1272"),
    ("Khizer", "khizer123"),
    
    # Add/edit as needed
]


# 🔄 Sync users (run at startup)
async def sync_users(db: AsyncSession):
    # 1️⃣ Fetch all existing users from DB
    result = await db.execute(select(AuthUser))
    existing_users = result.scalars().all()  # list of AuthUser objects

    # 2️⃣ Hardcoded usernames set
    hardcoded_usernames = [u[0] for u in USERS_TO_CREATE]

    # 3️⃣ Delete users who are not in hardcoded list
    for user in existing_users:
        if user.username not in hardcoded_usernames:
            await db.delete(user)

    # 4️⃣ Add new users or update existing users
    for username, plain_pw in USERS_TO_CREATE:
        # Check if username already exists
        user = next((u for u in existing_users if u.username == username), None)

        if user:
            # ✅ Update password only if changed
            user.password = hash_password(plain_pw)
            db.add(user)
        else:
            # ✅ Create new user
            new_user = AuthUser(username=username, password=hash_password(plain_pw))
            db.add(new_user)

    await db.commit()



# 🔑 Login route
@router.post("/login")
async def login(username: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30
    }
