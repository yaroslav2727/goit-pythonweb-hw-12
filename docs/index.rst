FastAPI Contacts API Documentation
=====================================

Welcome to the FastAPI Contacts API documentation. This API provides endpoints for managing contacts, user authentication, and user management.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/auth
   api/contacts
   api/users
   api/utils
   schemas

API Overview
------------

This FastAPI application provides a RESTful API for managing contacts with user authentication and authorization. The API includes the following main features:

- User registration and authentication
- Email verification and password reset
- Contact management (CRUD operations)
- User profile management
- Role-based access control (Admin/User)
- Avatar upload functionality

Base URL
--------

All API endpoints are prefixed with ``/api``

Authentication
--------------

The API uses OAuth2 with JWT tokens for authentication. To access protected endpoints, include the JWT token in the Authorization header:

.. code-block:: http

   Authorization: Bearer <your-jwt-token>

Getting Started
---------------

1. Register a new user account using ``/api/auth/register``
2. Confirm your email address using the link sent to your email
3. Login using ``/api/auth/login`` to get an access token
4. Use the access token to access protected endpoints

Rate Limiting
-------------

Some endpoints have rate limiting applied:

- User profile endpoints: 3-5 requests per minute
- Other endpoints: Standard rate limits apply

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
