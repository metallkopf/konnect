# Konnect - headless kde connect
Konnect is based on the [KDE Connect](https://community.kde.org/KDEConnect) protocol and allows a non-interactive enviroment (headless server) to send notifications to your devices via Rest API or a *simple* CLI

## Prerequisites
- Python 3.7+
- Systemd (optional)

## Installation
```bash
# Create virtualenv
python3 -m venv venv

# Wheels for systemd
venv/bin/pip install "konnect[systemd] @ https://github.com/metallkopf/konnect/releases/download/0.1.6/konnect-0.1.6-py3-none-any.whl"

# Wheels for generic init
venv/bin/pip install https://github.com/metallkopf/konnect/releases/download/0.1.6/konnect-0.1.6-py3-none-any.whl

# From source
venv/bin/pip install git+https://github.com/metallkopf/konnect.git@master#egg=konnect
```

## Test run
```bash
# With KDE Connect installed
venv/bin/konnectd --name Test --admin-port 8080

# Without KDE Connect installed
venv/bin/konnectd --name Test --receiver --admin-port 8080
```

## Examples
- List available devices
```bash
# Rest API
curl -s -X GET http://localhost:8080/device

# CLI
venv/bin/konnect --devices

- user@remotehost: 00112233_4455_6677_8899-aabbccddeeff (Trusted: False, Reachable: True)
- smartphone: abcdef0123456789 (Trusted: False, Reachable: True)
```
- Pair with device
```bash
# Rest API
curl -s -X POST http://localhost:8080/device/name/user@remotehost

# CLI
venv/bin/konnect --name user@remotehost --command pair
```
- Accept pairing request on remote host
- Check successful pairing by sending ping
```bash
# Rest API
curl -s -X POST http://localhost:8080/ping/name/user@remotehost

# CLI
venv/bin/konnect --name user@remotehost --command ping
```
- Send notification
```bash
# Rest API
curl -s -X POST -d '{"application":"Package Manager","title":"Maintenance","text":"There are updates available!","reference":"update"}' http://localhost:8080/notification/name/user@remotehost

# CLI
venv/bin/konnect --name user@remotehost --command notification --title maintenance --text updates_available --application package_manager --reference update
```
- Unpair device
```bash
# Rest API
curl -s -X DELETE http://localhost:8080/device/name/user@remotehost

# CLI
venv/bin/konnect --name user@remotehost --command unpair
```

## Daemon usage
```bash
venv/bin/konnectd --help
```
```
usage: konnectd [--name NAME] [--debug] [--discovery-port PORT] [--service-port PORT] [--transfer-port PORT]
                [--max-transfer-ports NUM] [--admin-port PORT] [--config-dir DIR] [--receiver] [--service]
                [--help] [--version]

options:
  --name NAME           Device name (default: localhost)
  --debug               Show debug messages (default: False)
  --discovery-port PORT
                        Discovery port (default: 1716)
  --service-port PORT   Service port (default: 1764)
  --transfer-port PORT  Transfer port (top) (default: 1763)
  --max-transfer-ports NUM
                        Total open ports for transfer (default: 3)
  --admin-port PORT     API port (default: 8080)
  --config-dir DIR      Config directory (default: ~/.config/konnect)
  --receiver            Listen for new devices (default: False)
  --service             Send logs to journald (default: False)
  --help                This help (default: False)
  --version             Version information (default: False)
```

## Rest API
| Method | Resource | Description | Parameters |
| - | - | - | - |
| GET | / | Application info | |
| GET | /device | List devices | |
| GET | /device/(identifier\|name)/:value | Device info | |
| POST | /device/(identifier\|name)/:value | Pair | |
| DELETE | /device/(identifier\|name)/:value | Unpair | |
| PUT | /announce | Announce identity | |
| POST | /ping/(identifier\|name)/:value | Ping device | |
| POST | /ring/(identifier\|name)/:value | Ring device | |
| POST | /notification/(identifier\|name)/:value | Send notification | text, title, application, reference (optional), icon (optional) |
| DELETE | /notification/(identifier\|name)/:value/:reference | Cancel notification | |

## CLI usage
```bash
venv/bin/konnect --help
```
```
usage: konnect [--port PORT] [--debug]
               (--devices | --announce | --command {info,pair,unpair,ring,ping,notification,cancel} | --help | --version)
               [--identifier ID | --name NAME] [--text TEXT] [--title TITLE] [--application APP] [--reference REF]
               [--icon ICON] [--reference2 REF2]

options:
  --port PORT           Port running the admin interface
  --debug               Show debug messages

arguments:
  --devices             List all devices
  --announce            Search for devices in the network
  --command {info,pair,unpair,ring,ping,notification,cancel}
  --help                This help
  --version             Version information

command arguments:
  --identifier ID       Device Identifier
  --name NAME           Device Name

notification arguments:
  --text TEXT           The text of the notification
  --title TITLE         The title of the notification
  --application APP     The app that generated the notification
  --reference REF       An (optional) unique notification id
  --icon ICON           The icon of the notification (optional)

cancel arguments:
  --reference2 REF2     Notification id
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
ExecStart=/home/user/konnect/venv/bin/konnectd --receiver --service

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
### Read how to open firewall ports on
- [KDE Connect's wiki](https://community.kde.org/KDEConnect#Troubleshooting)
### Installation errors (required OS packages)
- Debian-based: `sudo apt-get install libsystemd-dev pkg-config python3-venv`
- RedHat-like: `sudo dnf install gcc pkg-config python3-devel systemd-devel`

## To-do (in no particular order)
- PyPI installable
- Unit testing
- Improve command line tool
- Periodically announce identity
- Connect to devices instead of just listening
- Better documentation
- Type hinting?
- Group notifications?
- Run commands?
- MDNS support?
- Share an receive files?

## Contributor(s)
- coxtor

## Code Style
```bash
venv/bin/isort --diff konnect/*.py

venv/bin/flake8 konnect/*.py
```

## Releasing
```bash
venv/bin/python -m build --wheel

venv/bin/twine check dist/*
```

## License
[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
