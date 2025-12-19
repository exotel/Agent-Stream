# ═══════════════════════════════════════════════════════════════════════════════
# Exotel Voice Bot - Production Dockerfile
# Multi-stage build for optimized production image
# ═══════════════════════════════════════════════════════════════════════════════

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Install build dependencies for native modules
RUN apk add --no-cache python3 make g++

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci --include=optional

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build TypeScript (if using TypeScript)
# RUN npm run build

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3: Production
FROM node:20-alpine AS production
WORKDIR /app

# Add labels for container metadata
LABEL org.opencontainers.image.title="Exotel Voice Bot"
LABEL org.opencontainers.image.description="AI voice bot framework for Exotel"
LABEL org.opencontainers.image.version="1.0.0"

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Install production dependencies only
COPY package*.json ./
RUN npm ci --only=production --include=optional && \
    npm cache clean --force

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/examples ./examples
COPY --from=builder /app/config ./config

# Create logs directory
RUN mkdir -p logs/events && chown -R nodejs:nodejs logs

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5001
ENV HOST=0.0.0.0

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:5001/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

# Start application
CMD ["node", "examples/simple-conversation-bot.js"]

