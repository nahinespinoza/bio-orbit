# syntax=docker/dockerfile:1
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --chown=nginx:nginx --chmod=644 nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/healthz || exit 1
