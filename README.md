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

## Experiment

- prefix pwifi: -30dbm
- prefix ppoorwifi: -46dbm
- lelzmqf\*: sending the string 'load' as replacement for images, as the data
  rate is really low when sending images.
