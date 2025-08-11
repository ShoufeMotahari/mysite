# utils/password_utils.py
import hashlib
import secrets
import hmac
import base64
from typing import Tuple, Optional


class CustomPasswordHasher:
    """
    Custom password hasher that replaces Django's make_password and check_password
    """

    # Constants
    UNUSABLE_PASSWORD_PREFIX = '!'
    UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40
    DEFAULT_ITERATIONS = 600000
    SALT_LENGTH = 32
    HASH_LENGTH = 64

    @staticmethod
    def get_random_string(length: int = UNUSABLE_PASSWORD_SUFFIX_LENGTH) -> str:
        """Generate a random string for unusable passwords"""
        alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_salt(length: int = SALT_LENGTH) -> str:
        """Generate a cryptographically secure random salt"""
        return base64.b64encode(secrets.token_bytes(length)).decode('utf-8')[:length]

    @staticmethod
    def pbkdf2_hash(password: str, salt: str, iterations: int = DEFAULT_ITERATIONS) -> str:
        """
        Generate PBKDF2 hash using SHA-256
        """
        return base64.b64encode(
            hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                iterations,
                CustomPasswordHasher.HASH_LENGTH
            )
        ).decode('utf-8')

    @classmethod
    def make_password(cls, password: Optional[str], salt: Optional[str] = None,
                      hasher: str = "pbkdf2_sha256", iterations: int = None) -> str:
        """
        Turn a plain-text password into a hash for database storage

        Args:
            password: The plain text password
            salt: Optional salt (will be generated if not provided)
            hasher: Hasher algorithm name
            iterations: Number of iterations (uses default if not provided)

        Returns:
            Encoded password in format: algorithm$iterations$salt$hash
        """
        # Handle None password (unusable password)
        if password is None:
            return cls.UNUSABLE_PASSWORD_PREFIX + cls.get_random_string(
                cls.UNUSABLE_PASSWORD_SUFFIX_LENGTH
            )

        # Validate password type
        if not isinstance(password, (str, bytes)):
            raise TypeError(
                f"Password must be a string or bytes, got {type(password).__qualname__}."
            )

        # Convert bytes to string if needed
        if isinstance(password, bytes):
            password = password.decode('utf-8')

        # Generate salt if not provided
        if salt is None:
            salt = cls.generate_salt()

        # Use default iterations if not specified
        if iterations is None:
            iterations = cls.DEFAULT_ITERATIONS

        # Generate hash based on hasher type
        if hasher == "pbkdf2_sha256":
            hash_value = cls.pbkdf2_hash(password, salt, iterations)
            return f"pbkdf2_sha256${iterations}${salt}${hash_value}"
        elif hasher == "sha256":
            # Simple SHA256 with salt (less secure, for compatibility)
            hash_value = hashlib.sha256(f"{salt}{password}".encode('utf-8')).hexdigest()
            return f"sha256${salt}${hash_value}"
        elif hasher == "bcrypt":
            # BCrypt implementation (requires bcrypt library)
            try:
                import bcrypt
                salt_bytes = salt.encode('utf-8')[:22]  # bcrypt uses 22 char salt
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(prefix=salt_bytes))
                return f"bcrypt${hashed.decode('utf-8')}"
            except ImportError:
                raise ImportError("bcrypt library is required for bcrypt hasher")
        else:
            raise ValueError(f"Unknown hasher: {hasher}")

    @classmethod
    def verify_password(cls, password: str, encoded: str, preferred: str = "pbkdf2_sha256") -> Tuple[bool, bool]:
        """
        Verify a password against an encoded hash

        Args:
            password: Plain text password to verify
            encoded: Encoded password hash from database
            preferred: Preferred hasher for determining if update is needed

        Returns:
            Tuple of (is_correct, must_update)
        """
        if not encoded or not password:
            return False, False

        # Check for unusable password
        if encoded.startswith(cls.UNUSABLE_PASSWORD_PREFIX):
            return False, False

        try:
            parts = encoded.split('$')
            algorithm = parts[0]

            if algorithm == "pbkdf2_sha256":
                if len(parts) != 4:
                    return False, False

                _, iterations_str, salt, stored_hash = parts
                iterations = int(iterations_str)

                # Generate hash with same parameters
                computed_hash = cls.pbkdf2_hash(password, salt, iterations)
                is_correct = hmac.compare_digest(computed_hash, stored_hash)

                # Check if we need to update (using newer iteration count or different preferred algorithm)
                must_update = iterations < cls.DEFAULT_ITERATIONS or preferred != "pbkdf2_sha256"

                return is_correct, must_update

            elif algorithm == "sha256":
                if len(parts) != 3:
                    return False, False

                _, salt, stored_hash = parts
                computed_hash = hashlib.sha256(f"{salt}{password}".encode('utf-8')).hexdigest()
                is_correct = hmac.compare_digest(computed_hash, stored_hash)

                # SHA256 should be upgraded to PBKDF2
                must_update = preferred != "sha256"

                return is_correct, must_update

            elif algorithm == "bcrypt":
                try:
                    import bcrypt
                    if len(parts) != 2:
                        return False, False

                    _, hashed = parts
                    is_correct = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

                    # BCrypt is secure, but check if preferred is different
                    must_update = preferred != "bcrypt"

                    return is_correct, must_update
                except ImportError:
                    return False, False

            else:
                return False, False

        except (ValueError, IndexError):
            return False, False

    @classmethod
    def check_password(cls, password: str, encoded: str, setter=None, preferred: str = "pbkdf2_sha256") -> bool:
        """
        Return a boolean of whether the raw password matches the encoded digest.

        If setter is specified, it'll be called when you need to regenerate the password.
        """
        is_correct, must_update = cls.verify_password(password, encoded, preferred)

        if setter and is_correct and must_update:
            # Call setter to update the password hash
            setter(password)

        return is_correct

    @classmethod
    async def acheck_password(cls, password: str, encoded: str, setter=None, preferred: str = "pbkdf2_sha256") -> bool:
        """Async version of check_password"""
        is_correct, must_update = cls.verify_password(password, encoded, preferred)

        if setter and is_correct and must_update:
            # Call async setter to update the password hash
            await setter(password)

        return is_correct


# Convenience functions that match Django's API
def make_password(password: Optional[str], salt: Optional[str] = None, hasher: str = "pbkdf2_sha256") -> str:
    """
    Custom implementation of Django's make_password
    """
    return CustomPasswordHasher.make_password(password, salt, hasher)


def check_password(password: str, encoded: str, setter=None, preferred: str = "pbkdf2_sha256") -> bool:
    """
    Custom implementation of Django's check_password
    """
    return CustomPasswordHasher.check_password(password, encoded, setter, preferred)


async def acheck_password(password: str, encoded: str, setter=None, preferred: str = "pbkdf2_sha256") -> bool:
    """
    Custom async implementation of Django's acheck_password
    """
    return await CustomPasswordHasher.acheck_password(password, encoded, setter, preferred)


# Additional utility functions
def is_password_usable(encoded: str) -> bool:
    """Check if the password is usable (not marked as unusable)"""
    return not encoded.startswith(CustomPasswordHasher.UNUSABLE_PASSWORD_PREFIX)


def get_password_strength(password: str) -> dict:
    """
    Analyze password strength and return detailed information
    """
    if not password:
        return {'score': 0, 'strength': 'No password', 'suggestions': ['Please enter a password']}

    score = 0
    suggestions = []

    # Check length
    if len(password) >= 8:
        score += 1
    else:
        suggestions.append('Use at least 8 characters')

    if len(password) >= 12:
        score += 1
    else:
        suggestions.append('Use at least 12 characters for better security')

    # Check character types
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*(),.?":{}|<>' for c in password)

    if has_upper:
        score += 1
    else:
        suggestions.append('Include uppercase letters')

    if has_lower:
        score += 1
    else:
        suggestions.append('Include lowercase letters')

    if has_digit:
        score += 1
    else:
        suggestions.append('Include numbers')

    if has_special:
        score += 1
    else:
        suggestions.append('Include special characters')

    # Determine strength
    if score <= 2:
        strength = 'Weak'
    elif score <= 4:
        strength = 'Fair'
    elif score <= 5:
        strength = 'Good'
    else:
        strength = 'Strong'

    return {
        'score': score,
        'strength': strength,
        'suggestions': suggestions if score < 6 else [],
        'has_upper': has_upper,
        'has_lower': has_lower,
        'has_digit': has_digit,
        'has_special': has_special,
        'length': len(password)
    }


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure password"""
    import string

    # Ensure we have at least one character from each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%^&*(),.?":{}|<>')
    ]

    # Fill the rest with random characters
    all_chars = string.ascii_letters + string.digits + '!@#$%^&*(),.?":{}|<>'
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # Shuffle the password
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


# Example usage and testing
if __name__ == "__main__":
    # Test the custom password functions

    print("=== Testing Custom Password Functions ===\n")

    # Test make_password
    test_password = "MySecurePassword123!"
    hashed = make_password(test_password)
    print(f"Original password: {test_password}")
    print(f"Hashed password: {hashed}\n")

    # Test check_password
    is_valid = check_password(test_password, hashed)
    print(f"Password verification: {is_valid}")

    wrong_password = "WrongPassword"
    is_invalid = check_password(wrong_password, hashed)
    print(f"Wrong password verification: {is_invalid}\n")

    # Test unusable password
    unusable = make_password(None)
    print(f"Unusable password: {unusable}")
    print(f"Is usable: {is_password_usable(unusable)}\n")

    # Test password strength
    weak_password = "123"
    strength = get_password_strength(weak_password)
    print(f"Password '{weak_password}' strength: {strength}\n")

    # Generate secure password
    secure_pass = generate_secure_password(16)
    secure_strength = get_password_strength(secure_pass)
    print(f"Generated password: {secure_pass}")
    print(f"Generated password strength: {secure_strength}")