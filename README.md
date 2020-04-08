# Konnect - headless kde connect
Konnect is based on the [KDE Connect](https://community.kde.org/KDEConnect) protocol and allows a non-interactive enviroment (headless server) to send notifications to your devices via Rest API or a *simple* CLI

## Prerequisites
- Python 3.7+
- Systemd
- Pipenv (or similar)

## Installation
```bash
# From source
pipenv install git+https://github.com/metallkopf/konnect.git@master#egg=konnect

# Wheels
pipenv install https://github.com/metallkopf/konnect/releases/download/0.1.0/konnect-0.1.0-py3-none-any.whl
```

## Test run
```bash
pipenv shell
```
```bash
# With KDE Connect installed
konnectd --name Test --admin-port 8080

# Without KDE Connect installed
konnectd --name Test --receiver --admin-port 8080
```

## Examples
- List available devices
```bash
# Rest API
curl -s -X GET http://localhost:8080/device

# CLI
konnect --devices

- user@remotehost: 00112233_4455_6677_8899-aabbccddeeff (Trusted:False Reachable:True)
- smartphone: abcdef0123456789 (Trusted:False Reachable:True)
```
- Pair with device
```bash
# Rest API
curl -s -X POST http://localhost:8080/device/name/user@remotehost

# CLI
konnect --name user@remotehost --command pair
```
- Accept pairing request on remote host
- Check successful pairing by sending ping
```bash
# Rest API
curl -s -X POST http://localhost:8080/ping/name/user@remotehost

# CLI
konnect --name user@remotehost --command ping
```
- Send notification
```bash
# Rest API
curl -s -X POST -d '{"application":"Package Manager","title":"Maintenance","text":"There are updates available!","reference":"update"}' http://localhost:8080/notification/name/user@remotehost

# CLI
konnect --name user@remotehost --command notification --title maintenance --text updates_available --application package_manager --reference update
```
- Unpair device
```bash
# Rest API
curl -s -X DELETE http://localhost:8080/device/name/user@remotehost

# CLI
konnect --name user@remotehost --command unpair
```

## Daemon usage
```bash
konnectd --help
```
```
usage: konnectd [--name NAME] [--verbose] [--discovery-port DISCOVERY_PORT]
                [--service-port SERVICE_PORT] [--admin-port ADMIN_PORT]
                [--config-dir CONFIG_DIR] [--receiver] [--service] [--help]
                [--version]

optional arguments:
  --name NAME           Device name (default: localhost)
  --verbose             Show debug messages (default: False)
  --discovery-port DISCOVERY_PORT Protocol discovery port (default: 1716)
  --service-port SERVICE_PORT     Protocol service port (default: 1764)
  --admin-port ADMIN_PORT         Admin Rest API port (default: 8080)
  --config-dir CONFIG_DIR         Config directory (default: ~/.config/konnect)
  --receiver                      Listen for new devices (default: False)
  --service                       Send logs to journald (default: False)
  --help                          This help (default: False)
  --version                       Version information (default: False)
```

## Rest API
| Method | Resource | Description | Parameters |
| - | - | - | - |
| GET | / | Application info | |
| GET | /device | List devices | |
| GET | /device/(id\|name)/:value | Device info | |
| POST | /device/(id\|name)/:value | Pair | |
| DELETE | /device/(id\|name)/:value | Unpair | |
| PUT | /announce | Announce identity | |
| POST | /ping/(id\|name)/:value | Ping device | |
| POST | /notification/(id\|name)/:value | Send notification | text, title, application, reference (optional) |
| DELETE | /notification/(id\|name)/:value/:reference | Cancel notification | |

## CLI usage
```bash
konnect --help
```
```
usage: konnect.py [--port PORT]
                  (--devices | --announce | --command {info,pair,unpair,ping,notification,cancel} | --help)
                  [--identifier ID | --name NAME] [--text TEXT] [--title TITLE]
                  [--application APP] [--reference REF] [--reference2 REF2]

optional arguments:
  --port PORT           Port running the admin interface

arguments:
  --devices             List all devices
  --announce            Search for devices in the network
  --command {info,pair,unpair,ping,notification,cancel}
  --help                This help

command arguments:
  --identifier ID       Device Identifier
  --name NAME           Device Name

notification arguments:
  --text TEXT           The text of the notification
  --title TITLE         The title of the notification
  --application APP     The app that generated the notification
  --reference REF       An (optional) unique notification id

cancel arguments:
  --reference2 REF       Notification id
```

## Run as service
Create a file named `konnect.service` in `/etc/systemd/system`, change the value `User` and `WorkingDirectory` accordingly and the execute the following commands
```ini
[Unit]
Description=Konnect
After=network.target
Requires=network.target

[Service]
User=user
Restart=always
Type=simple
WorkingDirectory=/home/user/konnect
ExecStart=/usr/bin/pipenv run konnectd --receiver --service

[Install]
WantedBy=multi-user.target
```
```bash
# Reload configurations
sudo systemctl daemon-reload

# Start service
sudo systemctl start konnect

# Start on boot
sudo systemctl enable konnect
```

## Compatibility
Tested *manually* on [kdeconnect](https://invent.kde.org/kde/kdeconnect-kde) 1.3.3+ and [kdeconnect-android](https://f-droid.org/en/packages/org.kde.kdeconnect_tp/) 1.13.0+

## Troubleshooting
- Read how to open firewall ports on [KDE Connect's wiki](https://community.kde.org/KDEConnect#Troubleshooting)

## To-do (in no particular order)
- Icon support
- PyPI installable
- Unit testing
- Improve command line tool
- Periodically announce identity
- Connect to devices instead of just listening
- Improve logging
- Better documentation
- Type hinting?
- Group notifications?
- Force recommended encryption?
- Run commands?
- Standardize rest resources?

## License
[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
