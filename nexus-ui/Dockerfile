# ==========================================
# Production Stage
# ==========================================
FROM nginx:alpine-slim

# Create a non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy the locally built assets from the host to Nginx's default public directory
# EDUCATIONAL NOTE: [Why] We bypass the multi-stage build here because the Node 
# process running `tsc` frequently triggers OOM (Out-Of-Memory) kills in 
# resource-constrained Docker environments. The host builds it locally instead.
COPY nexus-ui/dist /usr/share/nginx/html

# Change ownership of the nginx directories to the non-root user
RUN chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    chown -R appuser:appgroup /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid

# Switch to the non-root user
USER appuser

# Expose port 80 (default for Nginx)
EXPOSE 80

# Add a native healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:80/ || exit 1

# Nginx starts automatically
CMD ["nginx", "-g", "daemon off;"]