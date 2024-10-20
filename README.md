# Konnect - headless kde connect
Konnect is based on the [KDE Connect](https://community.kde.org/KDEConnect) protocol and allows a non-interactive enviroment (headless server) to send notifications to your devices via Rest API or a *simple* CLI

## Prerequisites
- Python 3.10+
- Systemd (optional)

## Installation
```bash
# Create virtualenv
python3 -m venv venv

# Wheels for systemd
venv/bin/pip install "konnect[systemd] @ https://github.com/metallkopf/konnect/releases/download/0.2.0/konnect-0.2.0-py3-none-any.whl"

# Wheels for generic init
venv/bin/pip install https://github.com/metallkopf/konnect/releases/download/0.2.0/konnect-0.2.0-py3-none-any.whl

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
venv/bin/konnect devices
{
  "devices": [
    {
      "identifier": "00112233_4455_6677_8899-aabbccddeeff",
      "name": "server",
      "trusted": true,
      "reachable": true
    },
    {
      "identifier": "abcdef0123456789",
      "name": "phone",
      "trusted": false,
      "reachable": true
    }
  ],
  "success": true
}
```
- Pair with device
```bash
# Rest API
curl -s -X POST http://localhost:8080/pair/@phone

# CLI
venv/bin/konnect pair --device @phone
```
- Accept pairing request on remote host
- Check successful pairing by sending ping
```bash
# Rest API
curl -s -X POST http://localhost:8080/ping/@phone

# CLI
venv/bin/konnect ping --device @phone
```
- Send notification
```bash
# Rest API
curl -s -X POST -d '{"application":"Package Manager","title":"Maintenance","text":"There are updates available!","reference":"update"}' http://localhost:8080/notification/@phone

# CLI
venv/bin/konnect notification --device @phone --title maintenance --text "updates available" --application package_manager --reference update
```
- Unpair device
```bash
# Rest API
curl -s -X DELETE http://localhost:8080/pair/@phone

# CLI
venv/bin/konnect unpair --unpair @phone
```

## Daemon usage
```bash
venv/bin/konnectd --help
```
```
usage: konnectd [--name NAME] [--debug] [--discovery-port PORT] [--service-port PORT] [--transfer-port PORT]
                [--max-transfer-ports NUM] [--admin-port PORT] [--admin-socket SOCK] [--admin-bind BIND]
                [--config-dir DIR] [--receiver] [--service] [--help] [--version]

options:
  --name NAME           Device name (default: computer)
  --debug               Show debug messages (default: False)
  --discovery-port PORT
                        Discovery port (default: 1716)
  --service-port PORT   Service port (default: 1764)
  --transfer-port PORT  Transfer port (top) (default: 1763)
  --max-transfer-ports NUM
                        Total open ports for transfer (default: 3)
  --admin-port PORT     API port (default: 8080)
  --admin-socket SOCK   API unix socket (default: ${XDG_RUNTIME_DIR}/konnectd.sock)
  --admin-bind BIND     API bind type (tcp or socket) (default: tcp)
  --config-dir DIR      Config directory (default: ~/.config/konnect)
  --receiver            Listen for new devices (default: False)
  --service             Send logs to journald (default: False)
  --help                This (default: False)
  --version             Version information (default: False)
```

## Rest API
| Method | Resource | Description | Parameters |
| - | - | - | - |
| GET | / | Application info | |
| PUT | / | Announce identity | |
| GET | /device | List devices | |
| GET | /device/\(@name\|identifier\) | Device info | |
| GET | /command | List all commands | |
| POST | /notification/\(@name\|identifier\) | Send notification | text, title, application, reference \(optional\), icon \(optional\) |
| DELETE | /notification/\(@name\|identifier\)/\(reference\) | Cancel notification | |
| POST | /pair/\(@name\|identifier\) | Pair | |
| DELETE | /pair/\(@name\|identifier\) | Unpair | |
| POST | /ping/\(@name\|identifier\) | Ping device | |
| POST | /ring/\(@name\|identifier\) | Ring device | |
| POST | /custom/\(@name\|identifier\) | Custom packet \(for testing only\) | type, body \(optional\) |

## CLI usage
```bash
venv/bin/konnect help
```
```
usage: konnect [--port PORT] [--debug]
               {announce,custom,device,devices,exec,notification,pair,ping,ring,unpair,version,help}
               ...

options:
  --port PORT           Port running the admin interface
  --debug               Show debug messages

actions:
  {announce,custom,device,devices,exec,notification,pair,ping,ring,unpair,version,help}
    announce            Announce your identity
    custom              Send custom packet...
    device              Show device info
    devices             List devices
    exec                Execute remote command...
    notification        Send or cancel notification...
    pair                Pair with device...
    ping                Send ping...
    ring                Ring my device...
    unpair              Unpair trusted device...
    version             Show server version
    help                This
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
- [KDE Connect\'s wiki](https://community.kde.org/KDEConnect#Troubleshooting)
### Installation errors (required OS packages)
- Debian-based: `sudo apt-get install libsystemd-dev pkg-config python3-venv`
- RedHat-like: `sudo dnf install gcc pkg-config python3-devel systemd-devel`

## To-do (in no particular order)
- Unit testing
- Periodically announce identity
- Connect to devices instead of just listening
- Better documentation
- Type hinting?
- Group notifications?
- MDNS support?
- Share an receive files?

## Contributor(s)
- coxtor

## Code Style
```bash
venv/bin/isort --diff konnect/*.py

venv/bin/flake8 konnect/*.py

venv/bin/pytest -vv
```

## Releasing
```bash
venv/bin/python -m build --wheel

venv/bin/twine check dist/*
```

## License
[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
