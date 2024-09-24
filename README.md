# t4k3r - TelegramForker

## Docker Install 

```
curl -sSL https://get.docker.com/ | CHANNEL=stable sh
```
```
systemctl enable --now docker
```

#### Compose

```
apt update
apt install docker-compose-plugin
```

## Installation 

_In writing process..._

Delete ".exapmle" in ".env.exapmle" and fill empty fields by comments.

```
docker-compose up -d --remove-orphans
```
- add sudo please if you run witout root user
- add --build flag if you want rebuild image

thats all =)

__If you have standalone installation of Compose use "docker compose" with "- between__

## For updates

```
git pull
docker-compose up -d --build
```

## About structure

_In writing process..._