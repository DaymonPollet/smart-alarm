# Smart Alarm Frontend
# Multi-stage build: Node for building, nginx for serving
# Supports ARM64 (Raspberry Pi) and AMD64

# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies (using npm install for better compatibility)
RUN npm install

# Copy source code
COPY . .

# Build arguments for API URL configuration
# Empty string = use relative paths (nginx proxies /api to backend)
# For local dev without nginx: set to http://localhost:8080
ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Build the application
RUN npm run build

# Production stage - nginx for serving static files
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
