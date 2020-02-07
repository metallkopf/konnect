# Konnect - server app
Konnect is an application based on [KDE Connect](https://community.kde.org/KDEConnect) protocol that allows a non-interactive enviroment (server) to send notifications to your devices via Rest API or a simple CLI

## Prerequisites
- python 3.7+
- pipenv
- systemd

## Installation
```bash
$ curl https://github.com/metallkopf/konnect/archive/master.tar.gz -o konnect-master.tar.gz
$ tar zxf konnect-master.tar.gz
$ cd konnect-master
$ pipenv install
```

## Test run
```bash
# With KDE Connect installed
$ pipenv run python konnectd.py --name Test --admin-port 8080

# Without KDE Connect installed
$ pipenv run python konnectd.py --name Test --receiver --admin-port 8080
```

## Run as service
Change `User` and `WorkingDirectory` on konnect.service
```bash
$ sudo cp konnect.service /etc/systemd/system
$ sudo systemctl daemon-reload
$ sudo systemctl start konnect
$ sudo systemctl enable konnect
```

## Examples
- List available devices
```bash
# CLI
$ pipenv run python konnect.py --devices
# Rest API
$ curl -s -X GET http://localhost:8080/device

- user@remotehost: 00112233_4455_6677_8899-aabbccddeeff (Trusted:False Reachable:True)
- smartphone: abcdef0123456789 (Trusted:False Reachable:True)
```
- Pair with device
```bash
# CLI
$ pipenv run python konnect.py --name user@remotehost --command pair
# Rest API
$ curl -s -X PUT -d '{"pair":true}' http://localhost:8080/device/name/user@remotehost
```
- Accept pairing request on remote host
- Check connectivity by sending ping
```bash
# CLI
$ pipenv run python konnect.py --name user@remotehost --command ping
# Rest API
$ curl -s -X POST http://localhost:8080/ping/name/user@remotehost
```
- Send notification
```bash
# CLI
$ pipenv run python konnect.py --name user@remotehost --command notification --title maintenance --text updates_available --application package_manager --reference update
# Rest API
$ curl -s -X POST -d '{"application":"Package Manager","title":"Maintenance","text":"There are updates available!","reference":"update"}' http://localhost:8080/notification/name/user@remotehost
```
- Unpair device
```bash
# CLI
$ pipenv run python konnect.py --name user@remotehost --command unpair
# Rest API
$ curl -s -X PUT -d '{"pair":false}' http://localhost:8080/device/name/user@remotehost
```

## Daemon usage
```bash
$ pipenv run python konnectd.py --help
```
```
usage: konnectd.py [--name NAME] [--verbose] [--discovery-port DISCOVERY_PORT]
                   [--service-port SERVICE_PORT] [--admin-port ADMIN_PORT]
                   [--config-dir CONFIG_DIR] [--receiver] [--service] [--help]

optional arguments:
  --name NAME           Device name
  --verbose             Show debug messages
  --discovery-port DISCOVERY_PORT
                        Protocol discovery port
  --service-port SERVICE_PORT
                        Protocol service port
  --admin-port ADMIN_PORT
                        Admin Rest API port
  --config-dir CONFIG_DIR
                        Config directory
  --receiver            Listen for new devices
  --service             Send logs to journald
  --help                This help
```

## CLI usage
```bash
$ pipenv run python konnect.py --help
```
```
usage: konnect.py [--port PORT]
                  (--devices | --announce | --command {info,pair,unpair,ping,notification} | --help)
                  [--identifier ID | --name NAME] [--text TEXT] [--title TITLE]
                  [--application APP] [--reference REF]

optional arguments:
  --port PORT           Port running the admin interface

arguments:
  --devices             List all devices
  --announce            Search for devices in the network
  --command {info,pair,unpair,ping,notification}
  --help                This help

command arguments:
  --identifier ID       Device Identifier
  --name NAME           Device Name

notification arguments:
  --text TEXT           The text of the notification
  --title TITLE         The title of the notification
  --application APP     The app that generated the notification
  --reference REF       An (optional) unique notification id
```

## Rest API
| Method | Resource | Description | Parameters |
| - | - | - | - |
| GET | /device | List devices | |
| GET | /device/(name\|identifier)/:value | Device info | |
| PUT | /device/(name\|identifier)/:value | Pair/Unpair | pair (boolean) |
| POST | /identity | Discover devices | |
| POST | /ping | Ping devices | |
| POST | /ping/(name\|identifier)/:value | Ping device | |
| POST | /notification/(name\|identifier)/:value | Send notification | text, title, application, reference (optional) |
| DELETE | /notification/(name\|identifier)/:value/:reference | Cancel notification | |

## Compatibility
Tested on [kdeconnect](https://invent.kde.org/kde/kdeconnect-kde) 1.3.3-1.4.0 and [kdeconnect-android](https://f-droid.org/en/packages/org.kde.kdeconnect_tp/) 1.13.0+ with protocol version 7

## Limitations
Konnect is only capable of sending notifications and anything other than ping will be ignored, this is by design

## Troubleshooting
- Read how to open firewall ports on [KDE Connect's wiki](https://community.kde.org/KDEConnect#Troubleshooting)

## To-do
- Icon support
- PyPI repository
- Unit testing
- Improve command line
- Periodically broadcast identity
- Connect to devices (instead of just listening)
- Type hinting
- Improve logging
- Better documentation
- Group notifications?

## License
[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
