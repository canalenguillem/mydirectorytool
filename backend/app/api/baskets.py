from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import (
    add_place_to_basket,
    create_basket,
    delete_basket,
    get_basket,
    list_baskets,
    remove_place_from_basket,
)

router = APIRouter()


class CreateBasketRequest(BaseModel):
    name: str


class AddPlaceRequest(BaseModel):
    place_id: str


@router.get("")
def get_baskets():
    return list_baskets()


@router.post("")
def post_basket(data: CreateBasketRequest):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre de la cesta no puede estar vacío")
    return create_basket(name)


@router.get("/{basket_id}")
def get_basket_detail(basket_id: int):
    basket = get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Cesta no encontrada")
    return basket


@router.post("/{basket_id}/places")
def add_place(basket_id: int, data: AddPlaceRequest):
    if not get_basket(basket_id):
        raise HTTPException(status_code=404, detail="Cesta no encontrada")
    add_place_to_basket(basket_id, data.place_id)
    return get_basket(basket_id)


@router.delete("/{basket_id}/places/{place_id}")
def remove_place(basket_id: int, place_id: str):
    if not get_basket(basket_id):
        raise HTTPException(status_code=404, detail="Cesta no encontrada")
    remove_place_from_basket(basket_id, place_id)
    return get_basket(basket_id)


@router.delete("/{basket_id}", status_code=204)
def delete_basket_endpoint(basket_id: int):
    if not get_basket(basket_id):
        raise HTTPException(status_code=404, detail="Cesta no encontrada")
    delete_basket(basket_id)
