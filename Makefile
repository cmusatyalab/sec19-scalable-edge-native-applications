# src = $(wildcard *.c)
# obj = $(src:.c=.o)

# LDFLAGS = -lGL -lglut -lpng -lz -lm

# myprog: $(obj)
#     $(CC) -o $@ $^ $(LDFLAGS)

.PHONY: all feed serve

all: feed serve

feed:
	python src/feed.py start --num 2 --to_host 127.0.0.1 --to_port 6379 --uri 'data/traces/lego_196/%010d.jpg' &

serve:
	python src/serve.py start --num 2 --host 127.0.0.1 --port 6379 &