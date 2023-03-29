# IMPC Energy

[简体中文](https://github.com/NiaoBlush/impc_energy/README.md) | English

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration) [![version](https://img.shields.io/github/manifest-json/v/NiaoBlush/impc_energy?filename=custom_components%2Fimpc_energy%2Fmanifest.json)](https://github.com/NiaoBlush/impc_energy/releases/latest)

Query the electricity bill and historical electricity consumption, as well as the electricity bill situation of Inner
Mongolia residents.

## Data Description

The data comes from the Inner Mongolia Power Company WeChat public account.

According to the information on the public account

> The balance queried is the system settlement balance, which equals last month's carried-over electricity fee + this
> month's paid electricity fee. The actual electricity balance is shown on the meter.

Therefore, the balance is ***not real-time*** and is for reference only.

## Installation

可以通过HACS或手动安装

## Configuration

you can start the configuration if you know your account number

+ add configuration in `configuration.yaml`

```yaml
sensor:
  #...

  - platform: impc_energy
    account_number: 01xxxxxxxx70      #account number
    name: home1                       #home name (optional)

  - platform: impc_energy
    account_number: 01xxxxxxxx71

  #...
```

the `name` field is optional
account name will be used as home name (which is address for most cases) if name field is missing.

+ restart hass

# Sensors

The integration will add two sensors for each home, electricity account balance and history
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221439.png?raw=true)

The balance is settlement balance, which will be changed every month and every time you pay your electricity fee(
theoretically)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221605.png?raw=true)

Historical data of power consumption and electricity fees for the past 12 months are put in one sensor.
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221718.png?raw=true)

# Other Information


Thanks to @involute for the code in his [post](https://bbs.hassbian.com/thread-13820-1-1.html)

Thanks to @Aaron Godfrey for his [custom component development guide](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)
