# BEC Atlas

BEC Atlas is a web-based management system for BEC (Beamline Experiment Control) deployments at scientific facilities. It provides centralized access control, deployment management, and real-time monitoring capabilities for beamline experiments.

## Features

- **Deployment Management**: Create and manage BEC deployments across multiple beamlines
- **Access Control**: Role-based access control with user, group, and admin permissions
- **Real-time Monitoring**: Live monitoring and control of beamline experiments
- **Authentication**: JWT-based authentication with LDAP integration
- **REST API**: Comprehensive API for programmatic access and integration

## Prerequisites

- Python >= 3.10
- Redis server
- MongoDB
- Docker
- tmux
- nginx (optional, for load balancing)

## Quick Start

1. **Install the package:**
   ```bash
   pip install -e './backend[dev]'
   ```

2. **Start required services:**
   ```bash
   # Start MongoDB (if using Docker)
   docker run --name mongodb -p 27017:27017 -d mongo:latest
   
   # Optional: Start nginx for load balancing
   nginx -c $(pwd)/utils/nginx.conf
   ```

3. **Start BEC Atlas:**
   ```bash
   bec-atlas start
   ```
   This will start two instances of the FastAPI server plus the Redis server.

4. **Update the available deployments:**
   ```bash
   bec-atlas-update deployments
   ```
   This will update the available deployments located in backend/bec_atlas/deployments/realms

6. **Start the data ingestor:**
   ```bash
   bec-atlas-ingestor
   ```
   This will start the data ingestor, needed to populate the database with new scans.

9. **Access the application:**
   - Web interface: `http://localhost:4200`
   - API documentation: `http://localhost/docs`
   - Direct API access: `http://localhost:8000/docs` or `http://localhost:8001/docs`

10. **Connect BEC to BEC Atlas:**
    - Go to `http://localhost/docs` and log in using the admin account.
       - On the local demo instance, the username and password is `admin@bec_atlas.ch` / `admin`.
    - Fetch a new deployment file, save it as `.atlas.env` in your root BEC directory
    - Restart the BEC server.
    - Your server should now be connected to Atlas. 

## Commands

- `bec-atlas start` - Start all services in tmux session
- `bec-atlas stop` - Stop all services
- `bec-atlas restart` - Restart all services  
- `bec-atlas attach` - Attach to running tmux session
- `bec-atlas-get-key` - Retrieve deployment environment files

## Development

The application consists of:
- **Backend**: FastAPI application with MongoDB and Redis
- **Frontend**: Angular web application
- **Services**: Two FastAPI instances (ports 8000/8001) with Redis (port 6379)

For development setup, see the individual README files in `backend/` and `frontend/` directories.

