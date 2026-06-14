# Node/Express microservice that renders D3 family trees server-side (jsdom).
# Internal only (the API proxies to it); no ingress. Listens on 3300.
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY index.js ./
EXPOSE 3300
CMD ["node", "index.js"]
