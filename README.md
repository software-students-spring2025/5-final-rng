[![CI](https://github.com/software-students-spring2025/5-final-rng/actions/workflows/CI.yml/badge.svg)](https://github.com/software-students-spring2025/5-final-rng/actions/workflows/CI.yml)

# DropIt

## Description

This project is a lightweight, secure file-sharing platform that allows users to upload files, optionally protect them with a password, and share download links. It is built with Flask, MongoDB, and supports file metadata handling (e.g., expiration dates, download limits). The system is containerized with Docker for easy deployment.

## Docker Images

All services are containerized and available on DockerHub:

- **Backend API**: [dropit](https://hub.docker.com/r/cyan04/dropit)
- **MongoDB (official image)**: [mongo](https://hub.docker.com/_/mongo)
- **MinIO (official image)**: [minio/minio](https://hub.docker.com/r/minio/minio)

## Team Members

- [Bill Feng](https://github.com/BillBBle)
- [Chenxin Yan](https://github.com/chenxin-yan)
- [Leo Wu](https://github.com/leowu777)
- [Felix Guo](https://github.com/Fel1xgte)

## Setup and Run Instructions

### 1. Clone the repository

```bash
git https://github.com/software-students-spring2025/5-final-rng.git
cd 5-final-rng
```

### 2. Set up environment variables

You must create a `.env` file at the root of the project. See `.env.example` for an example.

Example `.env`:

```bash
# Flask application settings
SECRET_KEY=your_secret_key_here
FLASK_ENV=development
FLASK_DEBUG=1

# MongoDB connection settings
MONGO_URI=mongodb://admin:password@mongodb:27017/
MONGO_USERNAME=admin
MONGO_PASSWORD=password

# MinIO settings (object storage)
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=pass1234
MINIO_URL=http://minio:9000
MINIO_BUCKET_NAME=dropit-storage
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key
```

### 3. Run locally with Docker Compose

```bash
docker-compose up --build
```

Login Minio dashboard at [http://localhost:9000](http://localhost:9000) and login with root username and password. Generate access key and secret key in dashboard and put then in `.env`

Restart the services, and access the web app at [http://localhost:3000](http://localhost:3000).

---

## Live Demo

You can access the deployed version of the application here:

👉 [http://104.131.162.152:3000/](http://104.131.162.152:3000/)

Feel free to upload, download, and test the functionality!
