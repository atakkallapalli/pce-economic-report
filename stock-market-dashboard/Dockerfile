# =============================================================================
# Multi-stage Dockerfile for Stock Market Dashboard (R Shiny)
# =============================================================================

# Stage 1: Install R packages
FROM rocker/shiny:4.4.0 AS builder

RUN install2.r --error --deps TRUE \
    shinydashboard \
    quantmod \
    plotly \
    DT \
    dplyr \
    tidyr \
    forecast \
    scales

# Stage 2: Production image
FROM rocker/shiny:4.4.0 AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/R/site-library /usr/local/lib/R/site-library

# Remove default Shiny examples
RUN rm -rf /srv/shiny-server/*

# Copy application code
COPY app.R /srv/shiny-server/app.R

# Custom Shiny Server config
RUN echo '\
run_as shiny;\n\
preserve_logs true;\n\
server {\n\
  listen 3838;\n\
  location / {\n\
    site_dir /srv/shiny-server;\n\
    log_dir /var/log/shiny-server;\n\
    directory_index on;\n\
    app_idle_timeout 0;\n\
    app_init_timeout 120;\n\
  }\n\
}' > /etc/shiny-server/shiny-server.conf

# Set permissions
RUN chown -R shiny:shiny /srv/shiny-server && \
    chown -R shiny:shiny /var/log/shiny-server

EXPOSE 3838

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:3838/ || exit 1

CMD ["/usr/bin/shiny-server"]
