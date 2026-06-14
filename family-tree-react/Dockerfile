# Multistage build for the React (Vite) SPA -> static files served by nginx.
# Runtime config is injected at container start (see 40-env.sh) so ONE image
# works across environments without a rebuild.

# ---- build ----
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- runtime ----
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# nginx:alpine runs /docker-entrypoint.d/*.sh before starting; this writes env.js
COPY docker-entrypoint.sh /docker-entrypoint.d/40-env.sh
RUN chmod +x /docker-entrypoint.d/40-env.sh
EXPOSE 80
