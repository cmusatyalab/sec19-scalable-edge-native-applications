.PHONY: all feed serve image

all: 
	python setup.py install
	cd app
	python setup.py install

run: feed serve

image: Dockerfile-conda-env Dockerfile
	docker build -f Dockerfile-conda-env -t res-env .
	docker build -t res .

serve-container:
	docker run --rm --link feeds-queue:redis res /bin/bash -l -c "conda activate resource-management && source .envrc && python rmexp/serve.py start --num 8 --host redis --port 6379"

feed:
	python rmexp/feed.py start --num 2 --to_host 127.0.0.1 --to_port 6379 --fps 10 --uri 'data/traces/lego_196/%010d.jpg' &

serve:
	python rmexp/serve.py start --num 8 --host 127.0.0.1 --port 6379 &

upgradedb:
	alembic revision --autogenerate -m "Added account table"
	alembic upgrade

dependency:
	conda env export > environment.yml
	sed -i '/app==/d' environment.yml
	sed -i '/rmexp==/d' environment.yml
