# Build and validate the browser terminal as part of the deployable image.
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/ ./
RUN npm install --no-package-lock --no-audit --no-fund \
    && npm run check \
    && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-build /frontend/public-build ./frontend/public-build
ENV NEPSE_PUBLIC_FRONTEND=/app/frontend/public-build
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
