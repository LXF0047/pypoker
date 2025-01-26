class Player:
    def __init__(self, id: str, name: str, money: float, loan: int, ready: bool):
        self._id: str = id
        self._name: str = name
        self._money: float = money
        self._loan: int = loan
        self._ready: bool = ready

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def money(self) -> float:
        return self._money

    @property
    def loan(self) -> int:
        return self._loan

    @property
    def ready(self) -> bool:
        return self._ready

    def dto(self):
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money,
            "loan": self.loan,
        }

    def take_money(self, money: float):
        if money > self._money:
            raise ValueError("Player does not have enough money")
        if money < 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money -= money

    def add_money(self, money: float):
        if money <= 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money += money

    def refund_money(self, times: int):
        # 还钱
        if times > self._loan:
            raise ValueError("Player does not have enough loan")
        self._money -= times * 1000
        self._loan -= times

    def add_loan(self):
        self.add_money(1000)
        self._loan += 1

    def __str__(self):
        return "player {}".format(self._id)
