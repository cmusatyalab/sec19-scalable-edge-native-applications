# src = $(wildcard *.c)
# obj = $(src:.c=.o)

# LDFLAGS = -lGL -lglut -lpng -lz -lm

# myprog: $(obj)
#     $(CC) -o $@ $^ $(LDFLAGS)

.PHONY: all feed serve

all: feed serve

feed:
	python rmexp/feed.py start --num 2 --to_host 127.0.0.1 --to_port 6379 --fps 10 --uri 'data/traces/lego_196/%010d.jpg' &

serve:
	python rmexp/serve.py start --num 8 --host 127.0.0.1 --port 6379 &

upgradedb:
	alembic revision --autogenerate -m "Added account table"
	alembic upgrade