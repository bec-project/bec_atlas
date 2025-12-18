def test_openapi_generation(backend):
    """
    Test that the OpenAPI schema can be generated without errors.
    """
    client, backend_instance = backend
    response = client.get(f"{backend_instance.prefix}/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/v1/user/login" in schema["paths"]
