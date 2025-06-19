Users Endpoints
===============

The users module provides endpoints for managing user profiles, avatars, and roles.

Get Current User
----------------

.. http:get:: /api/users/me

   Get current user information.

   Returns the profile information of the currently authenticated user. Rate limited to 3 requests per minute.

   **Authentication:** Required

   **Response:**

   :statuscode 200: User information successfully retrieved

   **Response Example:**

   .. code-block:: json

      {
        "id": 1,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "avatar": "https://example.com/avatar.jpg",
        "confirmed": true,
        "role": "user"
      }

Update User Avatar
------------------

.. http:patch:: /api/users/avatar

   Update user avatar image (Admin only).

   Uploads a new avatar image for the user to cloud storage and updates the user's profile. Requires admin privileges and confirmed email. Rate limited to 5 requests per minute.

   **Authentication:** Required (Admin only)

   **Request Body (Multipart Form Data):**

   :param file: Avatar image file to upload (max 5MB)

   **Response:**

   :statuscode 200: Avatar successfully updated
   :statuscode 403: Forbidden if email not confirmed or not admin
   :statuscode 404: User not found
   :statuscode 500: Upload failed

   **Response Example:**

   .. code-block:: json

      {
        "id": 1,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "avatar": "https://cloudinary.com/new-avatar-url.jpg",
        "confirmed": true,
        "role": "admin"
      }

Delete User Avatar
------------------

.. http:delete:: /api/users/avatar

   Delete user avatar and reset to default Gravatar (Admin only).

   Removes the current avatar and resets it to the default Gravatar image based on the user's email. Requires admin privileges. Rate limited to 3 requests per minute.

   **Authentication:** Required (Admin only)

   **Response:**

   :statuscode 200: Avatar successfully deleted and reset to default
   :statuscode 403: Forbidden if not admin
   :statuscode 404: User not found
   :statuscode 500: Operation failed

   **Response Example:**

   .. code-block:: json

      {
        "id": 1,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "avatar": "https://gravatar.com/avatar/hash",
        "confirmed": true,
        "role": "admin"
      }

Update User Role
----------------

.. http:patch:: /api/users/role

   Update user role (Admin only).

   Updates a user's role in the system. This endpoint is restricted to admin users only. Rate limited to 5 requests per minute.

   **Authentication:** Required (Admin only)

   **Request Body:**

   .. code-block:: json

      {
        "email": "user@example.com",
        "role": "admin"
      }

   **Available Roles:**

   - ``user`` - Regular user with basic permissions
   - ``admin`` - Administrator with full permissions

   **Response:**

   :statuscode 200: User role successfully updated
   :statuscode 403: Forbidden if not admin
   :statuscode 404: User not found
   :statuscode 500: Operation failed

   **Response Example:**

   .. code-block:: json

      {
        "id": 2,
        "username": "janedoe",
        "email": "jane.doe@example.com",
        "avatar": null,
        "confirmed": true,
        "role": "admin"
      }

Rate Limiting
-------------

User endpoints have the following rate limits:

- ``/api/users/me``: 3 requests per minute
- ``/api/users/avatar`` (DELETE): 3 requests per minute  
- ``/api/users/avatar`` (PATCH): 5 requests per minute
- ``/api/users/role``: 5 requests per minute

Admin Privileges
----------------

The following endpoints require admin role:

- Update user avatar
- Delete user avatar
- Update user role
- Register admin user

Users with admin role can perform these operations on any user account, while regular users can only access their own profile information.
