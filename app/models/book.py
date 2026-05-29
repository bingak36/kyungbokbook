from odmantic import Model


class BookModel(Model):
    keyword: str
    publisher: str
    price: int
    image: str
    is_favorite: bool = False

    model_config = {"collection": "books"}
