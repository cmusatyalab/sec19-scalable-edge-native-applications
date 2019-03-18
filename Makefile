.PHONY: all feed serve image serve-container

all: 
	protoc --proto_path=rmexp/proto --python_out=rmexp rmexp/proto/gabriel.proto
	pip uninstall -y rmexp
	python setup.py install && rm -rf build dist rmexp.egg-info .eggs
	pip uninstall -y app
	cd app && python setup.py install && rm -rf build dist app.egg-info .eggs

run: feed serve

image: Dockerfile-conda-env Dockerfile
	docker build -f Dockerfile-conda-env -t res-env .
	docker build -t res .

serve-container:
	bash serve-container.sh

feed:
	bash feed.sh

serve:
	python rmexp/serve.py start --num 2 --host 127.0.0.1 --port 6379 &

upgradedb:
	alembic revision --autogenerate -m "Added account table"
	alembic upgrade

dependency:
	conda env export > environment.yml
	sed -i '/app==/d' environment.yml
	sed -i '/rmexp==/d' environment.yml

clean:
	rm -rf build dist rmexp.egg-info .eggs
	cd app && rm -rf build dist app.egg-info .eggs