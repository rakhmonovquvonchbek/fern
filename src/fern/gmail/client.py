from fern.gmail.auth import get_gmail_service


def create_client():
    return get_gmail_service()
