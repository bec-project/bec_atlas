from fastapi import APIRouter, Response
from pydantic import BaseModel

from bec_atlas.router.base_router import BaseRouter


class HealthStatus(BaseModel):
    status: str
    services: dict[str, dict[str, str]]


class HealthRouter(BaseRouter):
    def __init__(self, prefix="/api/v1", datasources=None):
        super().__init__(prefix, datasources)
        self.router = APIRouter(prefix=prefix)
        self.router.add_api_route("/health", self.health_check, methods=["GET"])

    async def health_check(self, response: Response) -> HealthStatus:
        """
        Health check endpoint that verifies connections to Redis and MongoDB.
        Returns 200 if both services are healthy, 503 if any service is down.
        """
        services = {}
        all_healthy = True

        # Check Redis connection
        try:
            # Try to ping Redis to verify connection
            if self.datasources and hasattr(self.datasources, "redis") and self.datasources.redis:
                redis_connector = self.datasources.redis.connector
                if hasattr(redis_connector, "_redis_conn") and redis_connector._redis_conn:  # type: ignore
                    redis_connector._redis_conn.ping()  # type: ignore
                    services["redis"] = {"status": "healthy", "message": "Connection successful"}
                else:
                    raise Exception("Redis connection not established")
            else:
                raise Exception("Redis datasource not available")
        except Exception as e:
            services["redis"] = {"status": "unhealthy", "message": f"Connection failed: {str(e)}"}
            all_healthy = False

        # Check MongoDB connection
        try:
            # Try to list database names to verify connection
            if (
                self.datasources
                and hasattr(self.datasources, "mongodb")
                and self.datasources.mongodb
            ):
                mongodb_client = self.datasources.mongodb.client
                if mongodb_client:
                    # This will raise an exception if the connection is not available
                    mongodb_client.list_database_names()
                    services["mongodb"] = {"status": "healthy", "message": "Connection successful"}
                else:
                    raise Exception("MongoDB client not connected")
            else:
                raise Exception("MongoDB datasource not available")
        except Exception as e:
            services["mongodb"] = {"status": "unhealthy", "message": f"Connection failed: {str(e)}"}
            all_healthy = False

        overall_status = "healthy" if all_healthy else "unhealthy"

        # Set appropriate HTTP status code
        if not all_healthy:
            response.status_code = 503
        else:
            response.status_code = 200

        return HealthStatus(status=overall_status, services=services)
