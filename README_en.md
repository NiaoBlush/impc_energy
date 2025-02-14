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

### HACS (recommended)

You can install the integration by searching for `IMPC Energy` in HACS.

### Manual Installation

Download the latest version from [here](https://github.com/NiaoBlush/impc_energy/releases/latest)

Extract the contents of the archive into the `custom_components/impc_energy` folder.

**A restart of Home Assistant is required after installation.**

## Configuration

You only need to know your account number to start the configuration.

+ Go to Settings -> Devices & Services -> Add Integration (bottom right corner).
+ In the dialog box that appears, search for `IMPC Energy` and click.

  ![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/select_integration.png?raw=true)
+ In the configuration wizard, enter your account number and optionally your home name.
  If the account name is not provided, the integration will attempt to use the retrieved account name (which is usually the address) as the account
  name.

  ![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/config_helper.png?raw=true)
+ Wait for configuration to complete

+ The system will automatically generate entity id, which can be changed as needed.

<details>
<summary>Migration Guide for Older Versions</summary>
If you are upgrading from an older version `v0.X.X` to `v1.X.X` or later, please note the following:

+ The old configuration file method has been removed. Please use the graphical interface to add the integration.
+ Due to changes in entity_id and unique_id, the old entities are not compatible with the new version. You will need to delete the old entities.
+ If you cannot delete the old entities, try removing the old `IMPC Energy` integration, restarting Home Assistant, and then reinstalling the
  integration.

</details>

## Sensors

The integration will add two sensors for each home, electricity account balance and history
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/entities_created.png?raw=true)

The balance is settlement balance, which will be changed every month and every time you pay your electricity fee(
theoretically)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221605.png?raw=true)

Historical data of power consumption and electricity fees for the past 12 months are put in one sensor.

The data displayed as the state of the "History" entity is the bill of the current period.
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/history_bill.png?raw=true)

## Other Information

Thanks to @involute for the code in his [post](https://bbs.hassbian.com/thread-13820-1-1.html)

Thanks to @Aaron Godfrey for
his [custom component development guide](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)
