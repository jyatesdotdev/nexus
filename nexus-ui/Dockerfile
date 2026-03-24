# ==========================================
# Build Stage
# ==========================================
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code and build
COPY . .
# Set the API base URL to a relative path or expect it to be injected
RUN npm run build

# ==========================================
# Production Stage
# ==========================================
FROM nginx:alpine-slim

# Copy the built assets from the builder stage to Nginx's default public directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 (default for Nginx)
EXPOSE 80

# Nginx starts automatically
CMD ["nginx", "-g", "daemon off;"]
