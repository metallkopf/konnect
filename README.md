# Konnect - headless kde connect

Konnect is based on the [KDE Connect](https://community.kde.org/KDEConnect) protocol and allows a non-interactive enviroment (headless server) to send notifications to your devices via Rest API or a *simple* CLI

> Warning: Breaking chanches between versions 0.1.x and 0.2.x on the client tool and rest api.

## Prerequisites

- Python 3.10+
- Systemd (optional)

## Installation

```bash
# Create virtualenv
python3 -m venv venv

# Wheels for systemd
venv/bin/pip install "konnect[systemd] @ https://github.com/metallkopf/konnect/releases/download/0.2.1/konnect-0.2.1-py3-none-any.whl"

# Wheels for generic init
venv/bin/pip install https://github.com/metallkopf/konnect/releases/download/0.2.1/konnect-0.2.1-py3-none-any.whl

# From source
venv/bin/pip install git+https://github.com/metallkopf/konnect.git@master#egg=konnect
```

## Server

### Server options

```bash
venv/bin/konnectd --help
```

```
usage: konnectd [--name NAME] [--debug] [--discovery-port PORT] [--service-port PORT] [--transfer-port PORT] [--max-transfer-ports NUM] [--admin-port PORT] [--admin-socket SOCK] [--admin-bind BIND] [--config-dir DIR]
                [--receiver] [--service] [--help] [--version]

options:
  --name NAME           Device name (default: HOSTNAME)
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

### Test run

```bash
# With KDE Connect installed (admin interface by default on port 8080)
venv/bin/konnectd --name Test

# With KDE Connect installed (socket by default on ${XDG_RUNTIME_DIR}/konnectd.sock)
venv/bin/konnectd --name Test --admin-bind socket

# Without KDE Connect installed (listen for announce)
venv/bin/konnectd --name Test --receiver
```

### Run as service

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

### Rest API

| Method | Resource | Description | Parameters |
| - | - | - | - |
| GET | / | Application info | |
| PUT | / | Announce identity | |
| GET | /command | List all \(local\) commands | |
| GET | /command/\(@name\|identifier\) | List device commands | |
| POST | /command/\(@name\|identifier\) | Add device command | name, command |
| DELETE | /command/\(@name\|identifier\) | Remove all device commands | |
| PUT | /command/\(@name\|identifier\)/\(=name\|key\) | Update device command | name, command |
| DELETE | /command/\(@name\|identifier\)/\(=name\|key\) | Remove device command | |
| PATCH | /command/\(@name\|identifier\)/\(=name\|key\) | Execute \(remote\) device command | |
| POST | /custom/\(@name\|identifier\) | Custom packet \(for testing only\) | type, body \(optional\) |
| GET | /device | List all devices | |
| GET | /device/\(@name\|identifier\) | Device info | |
| GET | /notification | List all notifications | |
| POST | /notification/\(@name\|identifier\) | Send notification | text, title, application, reference \(optional\), icon \(optional\) |
| DELETE | /notification/\(@name\|identifier\)/\(reference\) | Cancel notification | |
| POST | /pair/\(@name\|identifier\) | Pair | |
| DELETE | /pair/\(@name\|identifier\) | Unpair | |
| POST | /ping/\(@name\|identifier\) | Ping device | |
| POST | /ring/\(@name\|identifier\) | Ring device | |

## Client

This utility can be used alone but requires the packages `requests` and `PIL` to work.

### Client usage

```bash
./venv/bin/konnect help
```

```
usage: konnect [--port PORT] [--debug] {announce,command,commands,custom,devices,exec,info,notifications,notification,pair,ping,ring,unpair,version,help} ...

options:
  --port PORT           Port running the admin interface
  --debug               Show debug messages

actions:
  {announce,command,commands,custom,devices,exec,info,notifications,notification,pair,ping,ring,unpair,version,help}
    announce            Announce your identity
    command             Configure local commands...
    commands            List all commands...
    custom              Send custom packet...
    devices             List all devices...
    exec                Execute remote command...
    info                Show server info
    notifications       List all notifications...
    notification        Send or cancel notification...
    pair                Pair with device...
    ping                Send ping...
    ring                Ring my device...
    unpair              Unpair trusted device...
    version             Show server version
    help                This
```

### List devices

```bash
./venv/bin/konnect devices
```

```yaml
devices:
- identifier: f81d4fae-7dec-11d0-a765-00a0c91e6bf6
  name: computer
  type: desktop
  reachable: true
  trusted: true
  commands:
    00112233-4455-6677-8899-aabbccddeeff:
      name: kernel
      command: uname -a
    550e8400-e29b-41d4-a716-446655440000:
      name: who
      command: whoami
- identifier: 9c5b94b1-35ad-49bb-b118-8e8fc24abf80
  name: phone
  type: smartphone
  reachable: false
  trusted: true
  commands: {}
```

### Pair device

```bash
./venv/bin/konnect pair --device @computer
# or
./venv/bin/konnect pair --device f81d4fae-7dec-11d0-a765-00a0c91e6bf6
```

### Ping device

```bash
./venv/bin/konnect ping --device @computer
# or
./venv/bin/konnect pair --device f81d4fae-7dec-11d0-a765-00a0c91e6bf6
```

### Send notification

```bash
./venv/bin/konnect notification --device @computer --application "Package Manager" \
  --title Maintenance --text "There are updates available!" --reference update
```

```yaml
key: update
```

### Dismiss notification

```bash
./venv/bin/konnect notification --device @computer --reference update --delete
```

### Execute (remote) command

```bash
./venv/bin/konnect exec --device @computer --key =kernel
# or
./venv/bin/konnect exec --device @computer --key 00112233-4455-6677-8899-aabbccddeeff
```

### Add (local) command

```bash
./venv/bin/konnect command --device @computer --name reboot --command "sudo reboot"
```

```yaml
key: 03000200-0400-0500-0006-000700080009
```

### List (local) commands

```bash
./venv/bin/konnect commands
```

```yaml
- identifier: f81d4fae-7dec-11d0-a765-00a0c91e6bf6
  device: computer
  key: 03000200-0400-0500-0006-000700080009
  name: reboot
  command: sudo reboot
```

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

## Development

### Code Style

```bash
venv/bin/isort --diff konnect/*.py

venv/bin/flake8 konnect/*.py

venv/bin/pytest -vv
```

### Releasing

```bash
venv/bin/python -m build --wheel

venv/bin/twine check dist/*
```

## Contributor(s)

- coxtor

## License

[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
