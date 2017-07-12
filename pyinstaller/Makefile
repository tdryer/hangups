SCRIPT_PATH=wrapper.py
DIST_PATH=dist
WORK_PATH=build
APP_NAME=hangups
VERSION=$(shell grep -E --only-matching "[0-9.]+" ../hangups/version.py)
DIST_NAME=${APP_NAME}-${VERSION}-linux-x86_64
SUDO_USER?=${USER}

DOCKER_VOLUME=/opt/build
DOCKER_TAG=pyinstaller

pyinstaller:
	pyinstaller \
		--hidden-import=pkg_resources \
		--clean \
		--strip \
		--noconfirm \
		--workpath "${WORK_PATH}" \
		--distpath "${DIST_PATH}" \
		--name "${APP_NAME}" \
		"${SCRIPT_PATH}"
	"${DIST_PATH}/${APP_NAME}/${APP_NAME}" --version
	rm -rf "${DIST_PATH}/${DIST_NAME}"
	mv "${DIST_PATH}/${APP_NAME}" "${DIST_PATH}/${DIST_NAME}"
	tar -zcvf "${DIST_PATH}/${DIST_NAME}.tar.gz" --directory "${DIST_PATH}" "${DIST_NAME}"

docker-pyinstaller:
	docker build -t "${DOCKER_TAG}" .
	docker run --rm --volume "${realpath ..}:${DOCKER_VOLUME}" --workdir "${DOCKER_VOLUME}" \
		"${DOCKER_TAG}" bash -c "pip3 install . && make --directory pyinstaller"
	chown --recursive "${SUDO_USER}:${SUDO_USER}" "${DIST_PATH}"

clean:
	rm -rf "${WORK_PATH}" "${APP_NAME}.spec" "${DIST_PATH}/${DIST_NAME}" "${DIST_PATH}/${APP_NAME}"

.PHONY: pyinstaller docker-pyinstaller clean
