# Final Project
# Project: Secure File Sharing Platform

## Description

This project is a lightweight, secure file-sharing platform that allows users to upload files, optionally protect them with a password, and share download links. It is built with Flask, MongoDB, and supports file metadata handling (e.g., expiration dates, download limits). The system is containerized with Docker for easy deployment.

## Badges



[![CI](https://github.com/software-students-spring2025/5-final-rng/actions/workflows/CI.yml/badge.svg)](https://github.com/software-students-spring2025/5-final-rng/actions/workflows/CI.yml)

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
SECRET_KEY=your_secret_key
FLASK_ENV=development
FLASK_DEBUG=1

MONGO_URI=mongodb://admin:password@localhost:27017/
MONGO_USERNAME=admin
MONGO_PASSWORD=password

MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=pass1234
MINIO_BUCKET_NAME=file-uploads

MAINTENANCE_API_KEY=your_secure_api_key
```

### 3. Run locally with Docker Compose

```bash
docker-compose up --build
```

Access the service at [http://localhost:3000](http://localhost:3000).

---

## Live Demo

You can access the deployed version of the application here:

👉 [http://104.131.162.152:3000/](http://104.131.162.152:3000/)

Feel free to upload, download, and test the functionality!

---
## Additional Notes

- **Environment Variables**: Sensitive variables are loaded through a `.env` file using `python-dotenv`. Example files like `.env.example` are provided for you to set up your environment quickly.
- **Starter Data**: There is no mandatory starter data, but MongoDB collections (`filesharing/uploads`) will be automatically created when you upload the first file.
- **Deployment Tips**: For production, disable Flask debug mode and use services like AWS S3 (instead of MinIO) and Atlas MongoDB.

---

**Feel free to open issues or pull requests for improvements!**

