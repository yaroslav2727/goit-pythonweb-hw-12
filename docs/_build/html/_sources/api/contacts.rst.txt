Contacts Endpoints
==================

The contacts module provides endpoints for managing contact information including creating, reading, updating, and deleting contacts.

Create Contact
--------------

.. http:post:: /api/contacts/

   Create a new contact for the authenticated user.

   Creates a new contact record with the provided contact information. The contact will be associated with the currently authenticated user.

   **Authentication:** Required

   **Request Body:**

   .. code-block:: json

      {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "birth_date": "1990-01-15",
        "additional_data": "Optional additional information"
      }

   **Response:**

   :statuscode 201: Contact successfully created
   :statuscode 422: Validation error

   **Response Example:**

   .. code-block:: json

      {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "birth_date": "1990-01-15",
        "additional_data": "Optional additional information",
        "user_id": 1
      }

Get Contacts
------------

.. http:get:: /api/contacts/

   Get list of contacts for the authenticated user.

   Retrieves contacts belonging to the authenticated user with optional pagination and search functionality.

   **Authentication:** Required

   **Query Parameters:**

   :param skip: Number of records to skip for pagination (default: 0)
   :param limit: Maximum number of records to return (default: 100)
   :param search: Search term to filter contacts by name or email

   **Response:**

   :statuscode 200: Contacts successfully retrieved
   :statuscode 422: Validation error

   **Response Example:**

   .. code-block:: json

      [
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
      ]

Get Contact by ID
-----------------

.. http:get:: /api/contacts/{contact_id}

   Get a specific contact by ID.

   Retrieves a single contact by its ID. The contact must belong to the authenticated user.

   **Authentication:** Required

   **Parameters:**

   :param contact_id: The unique identifier of the contact

   **Response:**

   :statuscode 200: Contact successfully retrieved
   :statuscode 404: Contact not found or doesn't belong to user
   :statuscode 422: Validation error

   **Response Example:**

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

Update Contact
--------------

.. http:patch:: /api/contacts/{contact_id}

   Update an existing contact.

   Updates contact information with the provided data. Only the fields included in the request body will be updated. The contact must belong to the authenticated user.

   **Authentication:** Required

   **Parameters:**

   :param contact_id: The unique identifier of the contact to update

   **Request Body (all fields optional):**

   .. code-block:: json

      {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "+0987654321",
        "birth_date": "1985-05-20",
        "additional_data": "Updated information"
      }

   **Response:**

   :statuscode 200: Contact successfully updated
   :statuscode 404: Contact not found or doesn't belong to user
   :statuscode 422: Validation error

Delete Contact
--------------

.. http:delete:: /api/contacts/{contact_id}

   Delete a specific contact.

   Permanently deletes a contact from the database. The contact must belong to the authenticated user.

   **Authentication:** Required

   **Parameters:**

   :param contact_id: The unique identifier of the contact to delete

   **Response:**

   :statuscode 200: Contact successfully deleted
   :statuscode 404: Contact not found or doesn't belong to user
   :statuscode 422: Validation error

   **Response Example:**

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

Get Upcoming Birthdays
----------------------

.. http:get:: /api/contacts/upcoming-birthdays

   Get contacts with upcoming birthdays within 7 days.

   Retrieves all contacts belonging to the authenticated user whose birthdays occur within the next 7 days from today.

   **Authentication:** Required

   **Response:**

   :statuscode 200: Upcoming birthdays successfully retrieved

   **Response Example:**

   .. code-block:: json

      [
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
      ]
