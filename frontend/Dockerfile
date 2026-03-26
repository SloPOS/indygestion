# Build stage
FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000/api/v1
ARG VITE_TUSD_ENDPOINT=http://localhost:1080/files
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_TUSD_ENDPOINT=${VITE_TUSD_ENDPOINT}

COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npm run build

# Runtime stage
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html

RUN printf 'server {\n  listen 80;\n  server_name _;\n  root /usr/share/nginx/html;\n  index index.html;\n\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
