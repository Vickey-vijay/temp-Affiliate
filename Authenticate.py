# Authenticate.py

class LoginManager:
    """
    Handles user authentication by verifying credentials against the MongoDB collection.
    """
    def __init__(self, collection):
        """
        Initialize with a MongoDB collection that stores user login details.
        :param collection: MongoDB collection with user credentials.
        """
        self.collection = collection

    def authenticate(self, username: str, password: str) -> bool:
        """
        Checks if a user exists with the provided username and password.
        :param username: The user's username.
        :param password: The user's password.
        :return: True if authentication is successful, False otherwise.
        """
        user = self.collection.find_one({"username": username, "password": password})
        return user is not None
