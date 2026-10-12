FROM node:20-alpine AS runner

WORKDIR /app

COPY dist/index.js ./index.js
COPY package.json ./package.json

ENV NODE_ENV=production

ENTRYPOINT ["node", "index.js"]
