.PHONY: all app feed serve image serve-container test

all: 
	if [ "$(shell uname -m)" = "x86_64" ]; then\
		protoc --proto_path=rmexp/proto --python_out=rmexp rmexp/proto/gabriel.proto;\
	fi
	python setup.py install && rm -rf build dist rmexp.egg-info .eggs
	echo "NOTE: Use make app to install changes to applications"

app:
	cd app && python setup.py install && rm -rf build dist app.egg-info .eggs

run: feed serve

image: Dockerfile-conda-env Dockerfile
	docker build -f Dockerfile-conda-env -t res-env .
	docker build -t res .

serve-container:
	bash scripts/serve-container.sh

kill-container:
	docker stop -t 0 rmexp
	docker stop -t 0 rmexp-monitor

feed:
	bash scripts/feed.sh

serve:
	python rmexp/serve.py start --num 1 --broker-type ${BROKER_TYPE} --broker-uri ${BROKER_URI}

monitor:
	python rmexp/monitor.py start --broker-type ${BROKER_TYPE} --broker-uri ${BROKER_URI}

upgradedb:
	alembic revision --autogenerate -m "updated db"
	alembic upgrade head

backupdb:
	docker exec res-db /usr/bin/mysqldump -u root --password=${DB_PASSWORD} --all-databases > data/cloudlet002-mysql-bk/backup-$$(date +%Y%m%d).sql

dependency:
	echo "We should manage enviroment.yml manually from now on"
	false
	# conda env export > environment.yml
	# sed -i '/app==/d' environment.yml
	# sed -i '/rmexp==/d' environment.yml

nexus:
	rsync -avh --exclude='data' --exclude='conda-env-rmexp' --exclude='.git' --exclude='trace-app' . ${MOBILE_USER}@${MOBILE_IP}:~/resource-management --delete
	ssh ${MOBILE_USER}@${MOBILE_IP} "bash -ex ~/resource-management/infra/nexus6/install.sh"
	# adb push app /sdcard/resource-management/
	# adb push infra /sdcard/resource-management/
	# adb push rmexp /sdcard/resource-management/
	# adb push Makefile /sdcard/resource-management/

test:
	pytest

clean:
	rm -rf build dist rmexp.egg-info .eggs
	cd app && rm -rf build dist app.egg-info .eggs