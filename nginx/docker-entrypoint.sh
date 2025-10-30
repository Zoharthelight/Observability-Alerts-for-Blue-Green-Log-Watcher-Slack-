#!/bin/sh
set -e

TEMPLATE=/etc/nginx/nginx.conf.template
FINAL=/etc/nginx/nginx.conf

render_config() {
  if [ "${ACTIVE_POOL}" = "green" ]; then
    export APP_UPSTREAM="backend_backup"
  else
    export APP_UPSTREAM="backend_primary"
  fi

  # Expand the template; include service host and port vars as well
  envsubst '\$APP_UPSTREAM \$BLUE_SERVICE_HOST \$GREEN_SERVICE_HOST \$APP_PORT' < ${TEMPLATE} > ${FINAL}
  echo "Rendered nginx config with ACTIVE_POOL=${ACTIVE_POOL} APP_UPSTREAM=${APP_UPSTREAM}"
}

if [ "$1" = "reload" ]; then
  render_config
  nginx -s reload
  echo "Reloaded nginx with ACTIVE_POOL=${ACTIVE_POOL}"
  exit 0
fi

render_config
exec nginx -g "daemon off;"
