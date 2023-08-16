from typing import List


class QueryValidation:
    """Helper object for validating subgraph queries."""

    @classmethod
    def validate_offer_query(
        cls,
        order_by: str,
        order_direction: str,
        first: int,
    ):
        """Validate the offer query."""
        error_messages = []

        error_messages.extend(
            cls.general_validations(
                order_by=order_by,
                allowed_order_by=["timestamp", "price"],
                order_direction=order_direction,
                first=first,
            )
        )

        if error_messages:
            raise ValueError("\n".join(error_messages))

    @classmethod
    def validate_trade_query(
        cls,
        order_by: str,
        order_direction: str,
        first: int,
    ):
        """Validate the trade query."""
        error_messages = []

        error_messages.extend(
            cls.general_validations(
                order_by=order_by,
                allowed_order_by=["timestamp"],
                order_direction=order_direction,
                first=first,
            )
        )

        if error_messages:
            raise ValueError("\n".join(error_messages))

    @staticmethod
    def general_validations(
        order_by: str,
        allowed_order_by: List[str],
        order_direction: str,
        first: int,
    ) -> List[str]:
        """General validations helper."""
        error_messages = []

        # check the order_by parameter
        if order_by.lower() not in allowed_order_by:
            error_messages.append(
                f"Invalid order_by, must be on of '{allowed_order_by}' (default: timestamp)"
            )

        # check the order_direction parameter
        if order_direction.lower() not in ("asc", "desc"):
            error_messages.append(
                "Invalid order_direction, must be 'asc' or 'desc' (default: desc)"
            )

        # check the first parameter
        if first < 1:
            error_messages.append(
                "Invalid first, must be greater than 0 (default: 1000)"
            )
        if not isinstance(first, int):
            error_messages.append("Invalid first, must be an integer (default: 1000)")

        return error_messages
