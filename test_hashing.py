import bcrypt


def hash_password(password):
    """
    Hash a password using bcrypt

    Args:
        password (str): The plain text password

    Returns:
        bytes: The hashed password
    """
    if not password:
        return None

    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

    return hashed


def verify_password(stored_hash, provided_password):
    """
    Verify a password against a stored hash

    Args:
        stored_hash (bytes or str): The hashed password from the database
        provided_password (str): The plain text password to check

    Returns:
        bool: True if the password matches, False otherwise
    """
    # If no password was set, and none provided, return True
    if not stored_hash:
        return not provided_password

    # If stored_hash is a string (from MongoDB), convert it to bytes
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    # Check if the provided password matches the stored hash
    return bcrypt.checkpw(provided_password.encode("utf-8"), stored_hash)


def test_password_hash():
    """Test password hashing and verification"""
    print("Starting password hashing tests...")

    # Test case 1: Regular password
    password = "test_password"
    hashed = hash_password(password)
    print(f"Original password: {password}")
    print(f"Hashed password: {hashed}")
    print(f"Hashed password (str): {hashed.decode('utf-8')}")

    # Verify correct password
    assert verify_password(hashed, password) is True
    print("✅ Correct password verification passed!")

    # Verify incorrect password
    assert verify_password(hashed, "wrong_password") is False
    print("✅ Incorrect password verification passed!")

    # Test with string hash (simulating retrieval from MongoDB)
    hashed_str = hashed.decode("utf-8")
    assert verify_password(hashed_str, password) is True
    print("✅ String hash verification passed!")

    # Test empty password
    empty_pwd = ""
    empty_hash = hash_password(empty_pwd)
    if empty_hash is None:
        print("✅ Empty password returns None")
    else:
        assert verify_password(empty_hash, empty_pwd) is True
        print("✅ Empty password verification passed!")

    # Test None password
    none_hash = hash_password(None)
    assert none_hash is None
    print("✅ None password returns None")

    # Test no password set scenario
    assert verify_password(None, "") is True
    print("✅ No password set, none provided - passes!")
    assert verify_password(None, "somepassword") is False
    print("✅ No password set, password provided - fails!")

    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    test_password_hash()
