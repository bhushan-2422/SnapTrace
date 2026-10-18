# JWT(Json web Token):  proves that user has successfully logged in
#                       this token is send by the server to the frontend 



#  bcrypt: is a password-hashing algorithm
#           used when the user creates an account


from fastapi import FastAPI
from pydantic import BaseModel # is the python lib used to validate and stucture data 
                                # it checks whether the data sent by a user has the correct format
from database import SessionLocal
from models import User
from fastapi import HTTPException
import bcrypt


app = FastAPI()

# @app.get("/")
# def home():
#     return {
#         "message " : "Cloud-based photo retriveal API isd running"
#     }

# @app.get("/health")
# def health():
#     return{
#         "status":"healthy"
#     }

# @app.get("/about") # the /about is the url where it should be go is same goes to health 
# def about():
#     return{
#         "project" : "Cloud-based Photo Retriveal",
#         "technology" : "FastAPI"
#     }

# class UserRequest(BaseModel):  # defines what data API expects
#     name: str
#     email: str


# @app.post("/users")     # Post: how FastAPI recevies data from the user
# def create_user(user: UserRequest):
#     db = SessionLocal()

#     new_user = User(
#         name=user.name,
#         email=user.email
#     )

#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     db.close()


#     return {
#         "message": "User created successfully",
#         "id": new_user.id,
#         "name": new_user.name,
#         "email": new_user.email
#     }


# @app.get("/users")
# def get_users():
#     db = SessionLocal()

#     users = db.query(User).all()

#     db.close()

#     return users


# # to get the user id by comparing the User id in the database

# @app.get("/users/{user_id}")
# def get_user(user_id: int):

#     db = SessionLocal()

#     user = db.query(User).filter(User.id == user_id).first()

#     db.close()

#     if user is None:
#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     return {
#         "id": user.id,
#         "name": user.name,
#         "email": user.email
#     }

#     #FastAPI will communicate with PostgreSQl through python database lib called SQLAlchemy
#     #   SQLAlchemy --> maps that python model to the database table........This concept is called ORM(Object Relational Mapping)

#     # Now importing the database session and user model


# #  Database operations 
# #  1. Update : PUT

# @app.put("/users/{user_id}")
# def update_user(user_id: int, user_data: UserRequest):

#     db = SessionLocal()

#     user = db.query(User).filter(User.id == user_id).first()

#     if user is None:
#         db.close()
#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     user.name = user_data.name
#     user.email = user_data.email

#     db.commit()
#     db.refresh(user)

#     db.close()

#     return {
#         "message": "User updated successfully",
#         "id": user.id,
#         "name": user.name,
#         "email": user.email
#     }


# # 2. Delete a user

# @app.delete("/users/{user_id}")
# def delete_user(user_id: int):

#     db = SessionLocal()

#     user = db.query(User).filter(User.id == user_id).first()

#     if user is None:
#         db.close()
#         raise HTTPException(
#             status_code=404,
#             detail="User not found"
#         )

#     db.delete(user)
#     db.commit()

#     db.close()

#     return {
#         "message":"User deleted successfully"
#     }


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


@app.post("/signup")
def signup(user_data: SignupRequest):

    db = SessionLocal()

    hashed_password = bcrypt.hashpw(
        user_data.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    new_user = User( 
    name = user_data.name,
    email = user_data.email,
    password_hash = hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    db.close()

    return{
        "message": "User registered succesfully",
        "id": new_user.id,
        "name": new_user.name,
        "email" : new_user.email
    }