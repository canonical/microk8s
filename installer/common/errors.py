class BaseError(Exception):
    """Base class for all exceptions.

    :cvar fmt: A format string that daughter classes override

    """

    fmt = "Daughter classes should redefine this"

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.fmt.format([], **self.__dict__)

    def get_exit_code(self):
        """Exit code to use if this exception causes the program to exit."""
        return 2
