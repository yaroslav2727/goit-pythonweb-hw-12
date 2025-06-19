Utility Endpoints
=================

The utils module provides utility endpoints for monitoring and health checking the application.

Health Check
------------

.. http:get:: /api/healthchecker

   Check the health status of the application and its dependencies.

   Verifies connectivity to the database and Redis cache to ensure the application is functioning properly.

   **Response:**

   :statuscode 200: Application is healthy
   :statuscode 500: Internal Server Error if connections fail

   **Response Example:**

   .. code-block:: json

      {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "timestamp": "2025-06-18T10:30:00Z"
      }

   **Use Cases:**

   - Monitoring application health in production
   - Load balancer health checks
   - Container orchestration health probes
   - Debugging connectivity issues

   **Dependencies Checked:**

   - **Database Connection**: Verifies that the application can connect to the PostgreSQL database
   - **Redis Cache**: Verifies that the application can connect to the Redis cache server

   **Error Responses:**

   If any dependency check fails, the endpoint will return a 500 status code with details about which service is unavailable.
