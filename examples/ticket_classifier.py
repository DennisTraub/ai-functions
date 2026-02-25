from enum import Enum

from ai_functions import ai_function


class TicketCategory(Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    GENERAL = "general"

@ai_function(skill="ticket-classifier")
def classify_ticket(message: str) -> TicketCategory:
    """Invoke the ticket-classifier skill to categorize a support ticket.

    Args:
        message: The support ticket text to classify.

    Returns:
        The matching TicketCategory enum value.
    """


def main():
    message = "I can't log into my account after resetting my password"
    result: TicketCategory = classify_ticket(message)
    print(f"Category: {result}")

if __name__ == "__main__":
    main()
