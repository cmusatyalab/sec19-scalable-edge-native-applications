# Edge Resource Management Research Study

## Infrastructure

### cadvisor, prometheus, and Grafana Setup

cadvisor is metric collection tool.
prometheus is a time-series database.
grafana is a visualization tool.

## To Use

```bash
python src/exp_lego.py 'data/traces/lego_196/%010d.jpg'
```

## Development setup

```bash
cd src
vim .envrc
alembic upgrade
```
