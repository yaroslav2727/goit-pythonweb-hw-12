from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar
from fastapi import HTTPException, status

from src.repository.users import UserRepository
from schemas import UserCreate


class UserService:
    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(f"Failed to get Gravatar: {e}")

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def get_user_by_username(self, username: str):
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        try:
            return await self.repository.update_avatar_url(email, url)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
