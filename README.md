# BEC Atlas

## Prerequisites
* Install redis
* Install docker
* Python environment >= 3.10
* tmux
* nginx (optional)

## Installation
* `pip install -e './backend[dev]'`
* `docker run --name scylla -p 9042:9042 -p 9160:9160 -p 9180:9180 -d scylladb/scylla`
* Optional: `nginx -c $(pwd)/utils/nginx.conf`
* `bec-atlas start` to start the backend. This will start two instances of the fastapi server plus the redis server.

Once the backend is running, you can access the API at `http://localhost/docs` through your browser. 

```{note}
The fastapi server will be running on port 8000 and 8001. The redis server will be running on port 6379. However, nginx will expose it directly to port 80. Therefore, you can access the API at `http://localhost/docs` through your browser. If you want to access the API directly, you can use `http://localhost:8000/docs` or `http://localhost:8001/docs`.
```

