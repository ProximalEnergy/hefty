class Field:
    def __init__(self, value):
        self._var: str | None = None
        self._scope: str | None = None
        self.value = value

    def set_var(self, var: str):
        self._var = var

    @property
    def var(self) -> str:
        if self._var is None:
            raise ValueError("Field var not assigned")
        return self._var

    def __set_name__(self, owner, name):
        self._scope = owner.__name__
        self.set_var(name)

    @property
    def full_name(self) -> str:
        if self._scope is None or self._var is None:
            raise ValueError("Field full name not assigned")
        return f"{self._scope}.{self._var}"

    @property
    def scope(self) -> str:
        if self._scope is None:
            raise ValueError("Scope not assigned")
        return self._scope
