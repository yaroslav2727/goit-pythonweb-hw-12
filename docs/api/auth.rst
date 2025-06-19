Authentication Endpoints
========================

The authentication module provides endpoints for user registration, login, email verification, and password reset functionality.

Register User
-------------

.. http:post:: /api/auth/register

   Register a new user account.

   Creates a new user account with the provided user data. Sends a verification email to the user's email address for account confirmation.

   **Request Body:**

   .. code-block:: json

      {
        "username": "string",
        "email": "user@example.com",
        "password": "string"
      }

   **Response:**

   :statuscode 201: User successfully created
   :statuscode 409: User with email or username already exists
   :statuscode 422: Validation error

   **Response Example:**

   .. code-block:: json

      {
        "id": 1,
        "username": "string",
        "email": "user@example.com",
        "avatar": null,
        "confirmed": false,
        "role": "user"
      }

Register Admin User
-------------------

.. http:post:: /api/auth/register-admin

   Admin-only endpoint to create admin users.

   Creates a new admin user account. This endpoint requires admin privileges and sends a verification email to the new admin user.

   **Authentication:** Required (Admin only)

   **Request Body:**

   .. code-block:: json

      {
        "username": "string",
        "email": "admin@example.com",
        "password": "string"
      }

   **Response:**

   :statuscode 201: Admin user successfully created
   :statuscode 403: Forbidden if current user is not an admin
   :statuscode 409: User with email or username already exists

Login User
----------

.. http:post:: /api/auth/login

   Authenticate user and return access token.

   Validates user credentials and returns a JWT access token for authenticated requests. The user's email must be confirmed before login is allowed.

   **Request Body (Form Data):**

   .. code-block:: json

      {
        "username": "string",
        "password": "string",
        "grant_type": "password"
      }

   **Response:**

   :statuscode 200: Login successful
   :statuscode 401: Invalid credentials or email not confirmed
   :statuscode 422: Validation error

   **Response Example:**

   .. code-block:: json

      {
        "access_token": "jwt-token-string",
        "token_type": "bearer"
      }

Confirm Email
-------------

.. http:get:: /api/auth/confirmed_email/{token}

   Confirm user's email address using verification token.

   Validates the email verification token and marks the user's email as confirmed. Users must confirm their email before they can log in.

   **Parameters:**

   :param token: Email verification token sent to user's email

   **Response:**

   :statuscode 200: Email successfully confirmed or already confirmed
   :statuscode 400: Invalid token or user not found

Request Email Verification
--------------------------

.. http:post:: /api/auth/request_email

   Request email verification for user account.

   Sends a verification email to the user's email address. Returns a generic success message regardless of whether the email exists for security reasons.

   **Request Body:**

   .. code-block:: json

      {
        "email": "user@example.com"
      }

   **Response:**

   :statuscode 200: Email verification request processed
   :statuscode 500: Email sending failed

Request Password Reset
----------------------

.. http:post:: /api/auth/request-password-reset

   Request password reset for user account.

   Sends a password reset email to the user's email address. Always returns a success message for security reasons, regardless of whether the email exists.

   **Request Body:**

   .. code-block:: json

      {
        "email": "user@example.com"
      }

   **Response:**

   :statuscode 200: Password reset request processed

Confirm Password Reset
----------------------

.. http:post:: /api/auth/confirm-password-reset

   Confirm password reset using token and update user password.

   Validates the password reset token and updates the user's password with the new password provided in the request.

   **Request Body:**

   .. code-block:: json

      {
        "email": "user@example.com",
        "new_password": "new-password-string",
        "token": "reset-token-string"
      }

   **Response:**

   :statuscode 200: Password successfully reset
   :statuscode 400: Invalid or expired token
   :statuscode 404: User not found
