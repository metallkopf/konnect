# Konnect - headless kde connect

Konnect is based on the [KDE Connect](https://community.kde.org/KDEConnect) protocol and allows a non-interactive environment (headless server) to send notifications to your devices via Rest API or a *simple* CLI

> There are issues with the current versions of KDE Connect, see Troubleshooting.

> Breaking changes in 0.4.0 `--admin-bind` and `--admin-socket` merged into `--admin-port`, `--receiver` is now `--discovery-port 1716`, `--transfer-port` and `--max-transfer-ports` has been removed as ports are allocated automatically, and `--service` has been deprecated and his systemd dependency removed.

> Breaking changes between konnect versions 0.1.x and 0.2.x on the client tool and rest api.

## Supported functionality (plugins):

* Ping
* Ring my phone
* Send notificacions (icon optional)
* Run commands
* Host remote commands
* ~~Share and~~ Receive (files)

## Installation

```bash
# Create virtualenv
python -m venv venv

# Default install (wheels)
venv/bin/pip install https://github.com/metallkopf/konnect/releases/download/0.4.0/konnect-0.4.0-py3-none-any.whl

# From source
venv/bin/pip install git+https://github.com/metallkopf/konnect.git@master#egg=konnect
```

## Server

### Server options

```bash
venv/bin/konnectd --help
```

```
usage: konnectd [--name NAME] [--debug] [--discovery-port PORT] [--service-port PORT] [--admin-port PORT] [--config-dir DIR] [--timestamps] [--version]

options:
  --name NAME           Device name (default: HOSTNAME)
  --debug               Show debug messages (default: False)
  --discovery-port PORT
                        Discovery port (default: 1764)
  --service-port PORT   Service port (default: 1764)
  --admin-port PORT     API (tcp) port or unix socket (default: 8080)
  --config-dir DIR      Config directory (default: ~/.config/konnect)
  --timestamps          Show timestamps (default: False)
  --version             Version information (default: False)
```

### Test run

```bash
# With KDE Connect installed (admin interface by default on port 8080)
venv/bin/konnectd --name Test

# With KDE Connect installed (bind to socket)
venv/bin/konnectd --name Test --admin-port /run/user/1000/konnectd.sock

# Without KDE Connect installed (listen for announce)
venv/bin/konnectd --name Test --discovery-port 1716
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
ExecStart=/home/user/konnect/venv/bin/konnectd --discovery-port 1716

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
| PATCH | /share/\(@name\|identifier\) | Receive files | path (optional) |

## Client

This utility can be used alone but requires the packages `requests` and `PIL` to work.

### Client usage

```bash
./venv/bin/konnect help
```

```
usage: konnect [--port PORT] [--debug] {announce,command,commands,custom,devices,exec,info,notifications,notification,pair,ping,receive,ring,unpair,version,help} ...

options:
  --port PORT           Port running the admin interface
  --debug               Show debug messages

actions:
  {announce,command,commands,custom,devices,exec,info,notifications,notification,pair,ping,receive,ring,unpair,version,help}
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
    receive             Receive files...
    ring                Ring my device...
    unpair              Unpair trusted device...
    version             Show server version
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
  reachable: True
  trusted: True
  commands:
    00112233-4455-6677-8899-aabbccddeeff:
      name: kernel
      command: uname -a
    550e8400-e29b-41d4-a716-446655440000:
      name: who
      command: whoami
  path: None
- identifier: 9c5b94b1-35ad-49bb-b118-8e8fc24abf80
  name: phone
  type: smartphone
  reachable: False
  trusted: True
  commands: {}
  path: ~/Downloads/phone
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
  --title Maintenance --text "There are updates available!" --reference update \
  --icon /usr/share/icons/oxygen/base/32x32/apps/system-software-update.png
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

### Receive (accept) files

```bash
./venv/bin/konnect receive --device @computer --path ~/Downloads/computer
```

## Troubleshooting

###  KDE Connect doesn't find any device

Starting with desktop versions 25.03.80 and android 1.33.0, the protocol version was increased, which had the side effect that untrusted devices running older versions of the software cannot be found.

- For desktop: if you can't find your device, hit "Refresh" on KDE Connect in System Settings. Konnect will send an identity packet matching that protocol version.
- For android: if installed initially with a version older than 1.24.0 you might need to delete the app data and re-pair your devices. The app device id is too short for the current protocol.

### Read how to open firewall ports on

- [KDE Connect\'s wiki](https://community.kde.org/KDEConnect#Troubleshooting)

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

## License

[GPLv2](https://www.gnu.org/licenses/gpl-2.0.html)
