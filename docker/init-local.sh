#!/bin/bash
# Bootstraps a Frappe bench that runs the LMS source mounted from this repo
# (instead of cloning frappe/lms from GitHub, like docker/init.sh does).
#
# Safe to re-run: an existing bench is reused, and the frontend is rebuilt only
# if its assets are missing (so a crashed build resumes rather than starting over).
set -euo pipefail

BENCH_DIR=/home/frappe/frappe-bench
SRC_MOUNT=/workspace/lms-src
SRC_STAGE=/home/frappe/lms-src
SITE=lms.localhost
# frappe 16.x pins Python >=3.14,<3.15
PYTHON_BIN=/home/frappe/.pyenv/versions/3.14.2/bin/python
# vite needs well over node's ~2GB default heap to build this SPA
export NODE_OPTIONS="--max-old-space-size=5120"

build_frontend() {
	echo ">>> Building the LMS frontend (vite)"
	cd "${BENCH_DIR}/apps/lms/frontend"
	yarn install --frozen-lockfile
	yarn build
	cd "${BENCH_DIR}"
	bench build --app lms || true
	bench --site "${SITE}" clear-cache
}

if [ -d "${BENCH_DIR}/apps/frappe" ]; then
	echo ">>> Bench already exists, reusing it"
	cd "${BENCH_DIR}"
	# node_modules lives in its own volume (see docker-compose.local.yml), so it
	# is empty the first time a bench boots after the bind mount was added.
	# Install before anything can try to build against nothing.
	if [ ! -d "${BENCH_DIR}/apps/lms/frontend/node_modules/vite" ]; then
		echo ">>> Installing frontend dependencies (container-side node_modules)"
		(cd "${BENCH_DIR}/apps/lms/frontend" && yarn install)
	fi
	if [ ! -f "${BENCH_DIR}/apps/lms/lms/www/_lms.html" ]; then
		echo ">>> Frontend assets missing, building them"
		build_frontend
	fi
	echo ">>> Ready: http://localhost:8000/lms  (Administrator / admin)"
	exec bench start
fi

echo ">>> Staging local LMS source as a git repo (bench get-app needs one)"
rm -rf "${SRC_STAGE}"
mkdir -p "${SRC_STAGE}"
tar -C "${SRC_MOUNT}" \
	--exclude=node_modules \
	--exclude=.git \
	--exclude=__pycache__ \
	-cf - . | tar -C "${SRC_STAGE}" -xf -
cd "${SRC_STAGE}"
git init -q -b main
git add -A
git -c user.email=dev@localhost -c user.name=dev commit -qm "local snapshot"

echo ">>> bench init (frappe version-16)"
cd /home/frappe
bench init --skip-redis-config-generation --frappe-branch version-16 \
	--python "${PYTHON_BIN}" frappe-bench
cd "${BENCH_DIR}"

echo ">>> Pointing bench at the mariadb/redis containers"
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

echo ">>> Fetching apps"
bench get-app --skip-assets --branch version-15 payments

# `bench get-app` clones into apps/lms, which fails when the repo is already
# bind-mounted there (the dev-loop setup in docker-compose.local.yml). Detect
# that and register the app in place instead: an editable pip install plus the
# apps.txt entry is exactly what get-app leaves behind.
if [ -f "${BENCH_DIR}/apps/lms/pyproject.toml" ]; then
	echo ">>> apps/lms is bind-mounted; installing it in place"
	"${BENCH_DIR}/env/bin/pip" install --quiet --editable "${BENCH_DIR}/apps/lms"
	grep -qxF lms "${BENCH_DIR}/sites/apps.txt" 2>/dev/null || echo lms >> "${BENCH_DIR}/sites/apps.txt"
else
	bench get-app --skip-assets lms "${SRC_STAGE}"
fi

echo ">>> Creating site ${SITE}"
bench new-site "${SITE}" \
	--force \
	--mariadb-root-password 123 \
	--admin-password admin \
	--no-mariadb-socket

bench --site "${SITE}" install-app payments
bench --site "${SITE}" install-app lms
bench --site "${SITE}" set-config developer_mode 1
bench use "${SITE}"

build_frontend

echo ">>> Ready: http://localhost:8000/lms  (Administrator / admin)"
exec bench start
