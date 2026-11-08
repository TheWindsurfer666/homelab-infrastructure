# Power Monitor – Ubuntu + Portainer

This repository deploys Prometheus and Grafana and reads PowerJoular's host CSV through a small host-side exporter.

## What it measures

PowerJoular's CSV fields are assumed to be:
`timestamp, cpu_usage_ratio, total_watts, cpu_watts, gpu_watts`.

**Important:** these are estimated/reported CPU and GPU component values, not whole-server wall power. The kWh and cost panels are estimates based on the sampled CPU+GPU watts. For true whole-server consumption, add a metering smart plug (for example Shelly Plug) and integrate its readings.

## 1. Check Docker host gateway

On Ubuntu:
```bash
ip -4 addr show docker0
```
The default is usually `172.17.0.1`. If yours differs, edit `POWERJOULAR_EXPORTER_HOST` in `exporter/powerjoular-exporter.service` to that address.

## 2. Install the host exporter

First ensure PowerJoular is running and the CSV exists:
```bash
sudo systemctl enable --now powerjoular.service
sudo test -r /run/powerjoular/powerjoular-service.csv && echo "PowerJoular CSV found"
```

Copy the exporter and service:
```bash
sudo mkdir -p /opt/power-monitor/exporter
sudo cp exporter/powerjoular_exporter.py /opt/power-monitor/exporter/
sudo cp exporter/powerjoular-exporter.service /etc/systemd/system/
sudo chmod 755 /opt/power-monitor/exporter/powerjoular_exporter.py
sudo systemctl daemon-reload
sudo systemctl enable --now powerjoular-exporter.service
sudo systemctl status powerjoular-exporter.service
```

Test locally on the Docker host:
```bash
curl http://172.17.0.1:9108/metrics
```
If you changed the docker0 address, use that address instead. You should see `powerjoular_total_watts`, `powerjoular_cpu_watts`, and `powerjoular_gpu_watts`.

The exporter binds to the Docker bridge gateway address rather than all network interfaces, so it is not intentionally exposed on the LAN.

## 3. Deploy in Portainer from Git

1. Push this repository to your GitHub account.
2. In Portainer, choose **Stacks → Add stack → Repository**.
3. Enter the repository URL and branch.
4. Set **Compose path** to `docker-compose.yml`.
5. Add a stack environment variable named `GRAFANA_ADMIN_PASSWORD` with a long unique password.
6. Deploy the stack.

The stack publishes Grafana on host port `3001`. Prometheus is internal to the Docker network and is not published.

Open `http://SERVER-IP:3001`, sign in with username `admin` and the password you supplied. Open **Dashboards → Server → Server Power Monitor**.

## 4. Cost setting

The monthly cost panel currently assumes **1.50 SEK/kWh**. To change it, edit the query in the panel titled `Estimated monthly cost (SEK, 1.50 kr/kWh)` and replace `1.5` with your electricity price.

This is a simple energy estimate; a real electricity bill can also include grid fees, taxes, VAT, and variable hourly prices.

## Troubleshooting

```bash
sudo journalctl -u powerjoular-exporter.service -n 50 --no-pager
sudo systemctl status powerjoular.service
curl http://172.17.0.1:9108/metrics
```

If the exporter cannot bind to `172.17.0.1`, check the actual `docker0` address and update the service file before restarting:
```bash
sudo systemctl daemon-reload
sudo systemctl restart powerjoular-exporter.service
```
