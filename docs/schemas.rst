Data Schemas
============

This section describes the data schemas used in the API for request and response bodies.

User Schemas
------------

UserCreate
~~~~~~~~~~

Schema for user registration requests.

.. code-block:: json

   {
     "username": "string",
     "email": "user@example.com",
     "password": "string"
   }

**Fields:**

- ``username`` (string, required): Desired username for the account
- ``email`` (string, required): User's email address (validated email format)
- ``password`` (string, required): User's password (will be hashed before storage)

User
~~~~

Schema for user data in API responses.

.. code-block:: json

   {
     "id": 1,
     "username": "string",
     "email": "user@example.com",
     "avatar": "https://example.com/avatar.jpg",
     "confirmed": false,
     "role": "user"
   }

**Fields:**

- ``id`` (integer): Unique identifier for the user
- ``username`` (string): User's username
- ``email`` (string): User's email address (validated email format)
- ``avatar`` (string, optional): URL to user's avatar image
- ``confirmed`` (boolean): Whether the user's email is confirmed (default: false)
- ``role`` (UserRole): User's role in the system (default: "user")

UserRole
~~~~~~~~

Enumeration for user roles.

**Values:**

- ``user`` - Regular user with basic permissions
- ``admin`` - Administrator with full permissions

UserRoleUpdate
~~~~~~~~~~~~~~

Schema for updating user roles (Admin only).

.. code-block:: json

   {
     "email": "user@example.com",
     "role": "admin"
   }

**Fields:**

- ``email`` (string, required): Email of the user to update
- ``role`` (UserRole, required): New role to assign

Contact Schemas
---------------

ContactCreate
~~~~~~~~~~~~~

Schema for creating a new contact.

.. code-block:: json

   {
     "first_name": "John",
     "last_name": "Doe",
     "email": "john.doe@example.com",
     "phone": "+1234567890",
     "birth_date": "1990-01-15",
     "additional_data": "Optional additional information"
   }

**Fields:**

- ``first_name`` (string, required, max 50 chars): Contact's first name
- ``last_name`` (string, required, max 50 chars): Contact's last name
- ``email`` (string, required, max 100 chars): Contact's email address (validated)
- ``phone`` (string, required, max 50 chars): Contact's phone number
- ``birth_date`` (date, required): Contact's date of birth (YYYY-MM-DD format)
- ``additional_data`` (string, optional): Additional information about the contact

ContactUpdate
~~~~~~~~~~~~~

Schema for updating an existing contact (all fields optional).

.. code-block:: json

   {
     "first_name": "Jane",
     "last_name": "Smith",
     "email": "jane.smith@example.com",
     "phone": "+0987654321",
     "birth_date": "1985-05-20",
     "additional_data": "Updated information"
   }

**Fields:**

- ``first_name`` (string, optional, max 50 chars): Updated first name
- ``last_name`` (string, optional, max 50 chars): Updated last name
- ``email`` (string, optional, max 100 chars): Updated email address
- ``phone`` (string, optional, max 50 chars): Updated phone number
- ``birth_date`` (date, optional): Updated date of birth
- ``additional_data`` (string, optional): Updated additional information

ContactResponse
~~~~~~~~~~~~~~~

Schema for contact API responses.

.. code-block:: json

   {
     "id": 1,
     "first_name": "John",
     "last_name": "Doe",
     "email": "john.doe@example.com",
     "phone": "+1234567890",
     "birth_date": "1990-01-15",
     "additional_data": null,
     "user_id": 1
   }

**Fields:**

- All fields from ContactCreate, plus:
- ``id`` (integer): Unique identifier for the contact
- ``user_id`` (integer): ID of the user who owns this contact

Authentication Schemas
----------------------

Token
~~~~~

Schema for authentication token responses.

.. code-block:: json

   {
     "access_token": "jwt-token-string",
     "token_type": "bearer"
   }

**Fields:**

- ``access_token`` (string): The JWT access token string
- ``token_type`` (string): Type of token (typically "bearer")

RequestEmail
~~~~~~~~~~~~

Schema for email confirmation requests.

.. code-block:: json

   {
     "email": "user@example.com"
   }

**Fields:**

- ``email`` (string, required): Email address to send confirmation to

RequestPasswordReset
~~~~~~~~~~~~~~~~~~~~

Schema for password reset requests.

.. code-block:: json

   {
     "email": "user@example.com"
   }

**Fields:**

- ``email`` (string, required): Email address to send password reset link to

ConfirmPasswordReset
~~~~~~~~~~~~~~~~~~~~

Schema for confirming password reset.

.. code-block:: json

   {
     "email": "user@example.com",
     "new_password": "new-password-string",
     "token": "reset-token-string"
   }

**Fields:**

- ``email`` (string, required): Email address of the user resetting password
- ``new_password`` (string, required): The new password to set
- ``token`` (string, required): Password reset token for verification

Validation Rules
----------------

**Email Validation:**
- Must be a valid email format
- Maximum length: 100 characters (for contacts), no limit for users

**String Length Limits:**
- Contact names: 50 characters maximum
- Contact phone: 50 characters maximum
- Username: No explicit limit defined
- Passwords: No explicit limit defined (will be hashed)

**Date Format:**
- Birth dates must be in ISO 8601 date format (YYYY-MM-DD)

**File Upload:**
- Avatar files: Maximum 5MB
- Supported formats: Common image formats (jpg, png, gif, etc.)
