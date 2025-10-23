
import re

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    pass


class MixInNameTable:
	"""Class that take the class name and lower this to create the table name

	Returns:
		str: name in lowercase
	"""

	@declared_attr.directive
	def __tablename__(cls) -> str:
		name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()  # type: ignore
		return name
