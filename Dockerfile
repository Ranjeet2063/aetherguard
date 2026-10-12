# Multi-stage Dockerfile for AetherGuard MCP Server
# Designed for Glama, Smithery, and Model Context Protocol stdio runners

FROM node:20-alpine AS runner

WORKDIR /app

# Copy built MCP bundle and metadata
COPY packages/mcp-server/dist/index.js ./index.js
COPY packages/mcp-server/package.json ./package.json

ENV NODE_ENV=production

# Run MCP server on stdio
ENTRYPOINT ["node", "index.js"]
