from schemas import User, UserCreate
from crud import get_user_by_id, update_user
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}", response_model=User)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user



@router.put("/{user_id}", response_model=User)
async def update_user_endpoint(user_id: int, updated_user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await update_user(db, user_id, updated_user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
