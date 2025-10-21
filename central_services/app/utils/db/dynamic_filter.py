from datetime import datetime
from json import loads
from typing import Any

from sqlalchemy.sql import operators
from sqlalchemy.sql.operators import Operators

operator_map = {
	"=": operators.eq,
	"!=": operators.ne,
	">": operators.gt,
	">=": operators.ge,
	"<": operators.lt,
	"<=": operators.le,
	"like": operators.like_op,
	"in": operators.in_op,
	"btw": operators.between_op,
}


def get_filters(filters: str, model_db: Any) -> tuple[Any] | tuple[Operators]:
	"""
	Convert a string of filters to a tuple with the real Operations.
	The operations available are:

		- =
		- !=
		- >
		- >=
		- <=
		- like
		- in
		- btw
	Args:
		filters (str): A string with `n` filters used in any operation in the db.
		model_db (Any): Model where the filter should be applied
	Returns:
		tuple[Any] | tuple[Operators] :A tuple with the applied filters.

	Examples:

	.. code-block:: python
		filter = "[["id", "=", 1]]"
		get_filters(filters=filter, model_db: Employee)"""
	filter_ = ()
	if filters != "":
		filter: list[Any] = loads(filters)
		for _filter in filter:
			column_name, operator, value = _filter
			column = getattr(model_db, column_name, None)  # Get the column dynamically
			if column is not None:
				if isinstance(value, str) and operator in [
					"=",
					"!=",
					">",
					">=",
					"<",
					"<=",
				]:
					try:
						value = datetime.strptime(value, "%Y-%m-%d")
					except ValueError:
						pass  # It wasn't a datetime, leave it as a string
				filter_ += (
					(operator_map[operator](column, value),)
					if operator != "btw"
					else (operator_map[operator](column, value[0], value[1]),)  # type: ignore
				)
	return filter_  # type: ignore
