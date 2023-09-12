from django.db import transaction
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel, validator, Field, root_validator
from typing import Optional
import re
from starlette import status

from callback.models import (
    Player,
    Game
)

description = """
We use JWT for auth.
"""

app = FastAPI(
    title="Test Project API",
    description=description,
    version="0.0.1"
)


class User(BaseModel):
    username: str
    password: str


class LoginMessage(BaseModel):
    access_token: str


class UserMessage(BaseModel):
    user: str


class StatusMessage(BaseModel):
    status: str
    id: Optional[int] = None
    success: Optional[bool] = None


class ErrorMessage(BaseModel):
    status: str
    message: str


class CreatePlayerItem(BaseModel):
    name: str = Field(..., max_length=54)
    email: str = Field(..., max_length=54)

    @validator('name')
    def validate_name(cls, name):
        allowed_chars = set('0123456789abcdef')
        if not set(name).issubset(allowed_chars):
            raise ValueError('Invalid characters in name. Only digits 0-9 and letters a-f are allowed.')

        try:
            Player.objects.get(name=name)
        except Player.DoesNotExist:
            return name

        raise ValueError('Player item with this name already exists')

    @validator('email')
    def validate_email(cls, email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            raise ValueError('Email is not valid')

        try:
            Player.objects.get(email=email)
        except Player.DoesNotExist:
            return email
        raise ValueError('Player item with this email already exists')


class GameItem(BaseModel):
    name: str


class AddingPlayerInGame(BaseModel):
    game_id: int
    player_id: int

    @validator('player_id')
    def validate_player_id(cls, player_id):
        try:
            Player.objects.get(pk=player_id)
        except Player.DoesNotExist:
            raise ValueError('Player does not exists')
        return player_id

    @root_validator
    def validate_game_id(cls, values):
        player_id = values.get('player_id')
        game_id = values.get('game_id')

        try:
            game = Game.objects.prefetch_related('players').get(pk=game_id)
        except Game.DoesNotExist:
            raise ValueError('Game does not exists')
        if game.players.count() > 4:
            raise ValueError('Game has not more than 5 players')
        if player_id in game.players.values_list('pk', flat=True):
            raise ValueError('Player already in this game')

        return values


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"


# callback to get your configuration
@AuthJWT.load_config
def get_config():
    return Settings()


# exception handler for auth-jwt
# in production, you can tweak performance using orjson response
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


# provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token to use authorization
# later in endpoint protected
@app.post('/login', tags=['Auth'], responses={200: {"model": LoginMessage}})
def login(user: User, Authorize: AuthJWT = Depends()):
    """
    Use username=test and password=test for now. 
    This endpoint will response you with access_token 
    to use in header like: "Authorization: Bearer $TOKEN" to get protected endpoints
    """
    if user.username != "test" or user.password != "test":
        raise HTTPException(status_code=401, detail="Bad username or password")

    # subject identifier for who this token is for example id or username from database
    access_token = Authorize.create_access_token(subject=user.username)
    return JSONResponse(status_code=200, content={"access_token": access_token})


# protect endpoint with function jwt_required(), which requires
# a valid access token in the request headers to access.
@app.get('/user', tags=['Auth'], responses={200: {"model": UserMessage}})
def user(Authorize: AuthJWT = Depends()):
    """
    Endpoint response with user that fits "Authorization: Bearer $TOKEN"
    """
    Authorize.jwt_required()

    current_user = Authorize.get_jwt_subject()
    return JSONResponse(status_code=200, content={"user": current_user})


@app.get('/protected_example', tags=['Auth'], responses={200: {"model": UserMessage}})
def protected_example(Authorize: AuthJWT = Depends()):
    """
    Just for test of Auth. 

    Auth usage example:
    $ curl http://ip:8000/user

    {"detail":"Missing Authorization Header"}

    $ curl -H "Content-Type: application/json" -X POST \
    -d '{"username":"test","password":"test"}' http://localhost:8000/login

    {"access_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAzNjkyMjYxLCJuYmYiOjE2MDM2OTIyNjEsImp0aSI6IjZiMjZkZTkwLThhMDYtNDEzMy04MzZiLWI5ODJkZmI3ZjNmZSIsImV4cCI6MTYwMzY5MzE2MSwidHlwZSI6ImFjY2VzcyIsImZyZXNoIjpmYWxzZX0.ro5JMHEVuGOq2YsENkZigSpqMf5cmmgPP8odZfxrzJA"}

    $ export TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAzNjkyMjYxLCJuYmYiOjE2MDM2OTIyNjEsImp0aSI6IjZiMjZkZTkwLThhMDYtNDEzMy04MzZiLWI5ODJkZmI3ZjNmZSIsImV4cCI6MTYwMzY5MzE2MSwidHlwZSI6ImFjY2VzcyIsImZyZXNoIjpmYWxzZX0.ro5JMHEVuGOq2YsENkZigSpqMf5cmmgPP8odZfxrzJA

    $ curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/user

    {"user":"test"}

    $ curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/protected_example

    {"user":"test", "test": true}
    """
    Authorize.jwt_required()

    current_user = Authorize.get_jwt_subject()
    return JSONResponse(status_code=200, content={"user": current_user})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = exc.errors()
    modified_details = []
    for error in details:
        modified_details.append(
            {
                "status": "error",
                "text": error["msg"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": modified_details}),
    )


"""
Примечание для проверяющего: я знаю, что возможно лучше было бы с состоянием гонки бороться внутри функции через 
with transaction.atomic():
Но у меня валидация на уже существующего пользователя вынесена в схему pydantic. И мне хотелось оставить её там
"""
@transaction.atomic
@app.post('/new_player', tags=['Main'], responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}})
def create_new_player(player: CreatePlayerItem, Authorize: AuthJWT = Depends()):
    """
    Creates new player.
    """
    Authorize.jwt_required()
    new_player = Player(name=player.name, email=player.email)
    new_player.save()

    # if django >= 4.2
    # await Player.objects.acreate(name=player.name, email=player.email)

    return JSONResponse(content={"status": "success", "id": new_player.id, "success": True})


@transaction.atomic
@app.post('/new_game', tags=['Main'], responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}})
def create_new_game(game: GameItem, Authorize: AuthJWT = Depends()):
    """
    Creates new game.
    """
    Authorize.jwt_required()

    new_game = Game()
    new_game.name = game.name
    new_game.save()

    return JSONResponse(content={"status": "success", "id": new_game.id, "success": True})


@transaction.atomic
@app.post('/add_player_to_game', tags=['Main'], responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}})
def add_player_to_game(request_data: AddingPlayerInGame, Authorize: AuthJWT = Depends()):
    """
    Adds existing player to existing game.
    """
    Authorize.jwt_required()
    game = Game.objects.get(pk=request_data.game_id)
    game.players.add(request_data.player_id)

    return JSONResponse(content={"status": "success", "id": request_data.game_id, "success": True})
