# IMPC Energy

[简体中文](https://github.com/NiaoBlush/impc_energy/README.md) | English

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/manifest-json/v/NiaoBlush/impc_energy?filename=custom_components%2Fimpc_energy%2Fmanifest.json)](https://github.com/NiaoBlush/impc_energy/releases/latest)

Query electricity balance, historical electricity usage/bills, tiered tariff details, and daily consumption for residential users in Inner Mongolia.

## Data Source

The current version fetches data from the `MDEJ` app APIs.

The repository still keeps the old `energy_api.py` implementation for historical reference, but the WeChat public account related APIs are deprecated and no longer used for actual data fetching.

According to the wording from the original public account:

> The queried balance is the settlement balance, which equals last month's carried-over electricity fee plus this month's paid electricity fee. The actual balance is shown on the meter.

So the balance is ***not real-time*** and is for reference only.

## Installation

### HACS (recommended)

Search for `IMPC Energy` in HACS and install it.

### Manual Installation

Download the latest version from [here](https://github.com/NiaoBlush/impc_energy/releases/latest)

Extract the archive contents into `custom_components/impc_energy`.

**Home Assistant must be restarted after installation.**

## Configuration

The current version uses your `MDEJ` account for setup and no longer requires you to manually enter the electricity account number.

+ Go to Settings -> Devices & Services -> Add Integration.

+ Search for `IMPC Energy` and click it.

  ![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/select_integration.png?raw=true)

+ Enter your `MDEJ` username and password in the setup flow.

+ The integration will call the `getUser` API, discover all electricity accounts linked to the MDEJ account, and create one config entry for each account.

+ Each config entry title uses the address/account name returned by the API (`yhmc`).

+ Wait for setup to finish.

+ Entity IDs will be generated automatically and can be customized later if needed.

> If the `token` expires later, Home Assistant will ask for re-authentication. Enter the password again once to refresh the login token for all entries under the same MDEJ account.

<details>
<summary>Migration Guide for Older Versions</summary>

If you are upgrading from `v0.X.X` to `v1.X.X` or later, please note:

+ YAML configuration is no longer supported. Please add the integration from the UI.

+ Because of `entity_id` and `unique_id` changes, old entities are not compatible with the new version and may need to be removed.

+ Remove the old `impc_energy` YAML configuration if it still exists.

+ If old entities cannot be removed, try removing the old `IMPC Energy` integration, restarting Home Assistant, and then installing it again.

</details>

## Sensors

The integration creates 4 sensors for each electricity account:

+ `electricity balance`
+ `history`
+ `tiered bill`
+ `daily consumption`

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/entities_created.png?raw=true)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/entities_detail.png?raw=true)

The balance is the settlement balance, so in theory it normally changes monthly (and may also change after a payment; not fully verified).

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221605.png?raw=true)

The `history` sensor stores electricity usage and electricity bill data for the past 12 months in its attributes.

The state of the `history` entity is the bill of the current period.

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/history_bill.png?raw=true)

The `tiered bill` sensor queries **the previous month** by default.

![Tiered bill example](https://github.com/NiaoBlush/impc_energy/blob/master/img/tiered_bill.png?raw=true)

Its entity state is the total bill of that month. Extra attributes include:

+ `query_month`: query month in `YYYYMM`
+ `current_tier`: current tier level
+ `current_price`: current tier price
+ `total_consumption`: total consumption
+ `total_bill`: total bill
+ `tier_spread_bill`: tier price difference amount
+ `price_name`: tariff name
+ `price_code`: tariff code
+ `tiers`: tier detail array, convenient for Lovelace cards

The `daily consumption` sensor shows daily usage for the most recent 30 days.

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/sensor_daily_consumption.png)

> Negative daily values may occasionally appear because the upstream API itself sometimes returns negative numbers.

## Card Examples

Using [apexcharts-card](https://github.com/RomRider/apexcharts-card), you can build cards like these:

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20240409174425.png?raw=true)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/chart_daily_consumption.png?raw=true)

(If the x-axis step size does not work, it may be a limitation of the chart library.)

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_01xxxxxxx70_balance %}
          ### {{home.state}}
          Current balance (CNY)
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_0110xxxxxx970_history %}
          ### {{home.attributes['current']['bill']}}
          Current bill (CNY)
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_011xxxxxxx970_history %}
          ### {{home.attributes['current']['consumption']}}
          Current consumption (kWh)
  - type: custom:apexcharts-card
    header:
      show: true
      title: Usage history
      show_states: false
      colorize_states: true
    graph_span: 1y
    span:
      offset: '-1month'
    apex_config:
      legend:
        position: top
      xaxis:
        stepSize: 1
        tooltip:
          enabled: false
        labels:
          datetimeFormatter:
            year: ''
            month: M
      tooltip:
        x:
          format: yyyy-MM
    series:
      - name: Historical consumption
        entity: sensor.impc_energy_01xxxxxxxxx70_history
        type: column
        color: 3498DB
        unit: kWh
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item.length==6&&item.startsWith("20")){
              const timeStr=`${item.slice(0, 4)}-${item.slice(-2)}-01T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]["consumption"]]);
            }
          }
          return data;
      - name: Historical bill
        entity: sensor.impc_energy_011xxxxxx970_history
        color: FF9F0b
        unit: CNY
        extend_to: false
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item.length==6&&item.startsWith("20")){
              const timeStr=`${item.slice(0, 4)}-${item.slice(-2)}-01T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]["bill"]]);
            }
          }
          return data;

  - type: custom:apexcharts-card
    header:
      show: true
      title: Daily consumption
      show_states: false
      colorize_states: true
    graph_span: 30d
    apex_config:
      legend:
        position: top
      xaxis:
        stepSize: 1
        tooltip:
          enabled: false
        labels:
          datetimeFormatter:
            year: ''
            month: ''
            day: d
      tooltip:
        x:
          format: yyyy-MM-dd
    series:
      - name: Daily usage
        entity: sensor.impc_energy_011xxxxxx970_daily_consumption
        color: 4D55CC
        unit: kWh
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item&&item.startsWith("20")){
              const timeStr=`${item}T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]]);
            }
          }
          return data;
```

### Tiered Bill Card Example

Assuming the tiered bill entity is `sensor.impc_energy_0110072xxxxx_tiered_bill`

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |-
      {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
      ## Tiered bill overview
      Query month: **{{ e.attributes.query_month[:4] }}/{{ e.attributes.query_month[4:6] }}**

  - type: grid
    columns: 2
    square: false
    cards:
      - type: markdown
        content: |-
          {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
          ### Current tier
          **{{ e.attributes.current_tier }}**
      - type: markdown
        content: |-
          {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
          ### Current tier price
          **{{ e.attributes.current_price }} CNY/kWh**
      - type: markdown
        content: |-
          {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
          ### Total consumption
          **{{ e.attributes.total_consumption }} kWh**
      - type: markdown
        content: |-
          {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
          ### Total bill
          **{{ e.state }} CNY**
      - type: markdown
        content: |-
          {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
          ### Tier spread bill
          **{{ e.attributes.tier_spread_bill }} CNY**

  - type: markdown
    content: |-
      {% set e = states.sensor.impc_energy_0110072xxxxx_tiered_bill %}
      {% set tiers = e.attributes.tiers if e and e.attributes.tiers is defined else [] %}

      ### Tier details

      {% for item in tiers %}
      - **{{ item.tier_name }}**: {{ item.consumption }} kWh / {{ item.price }} CNY/kWh / {{ item.bill }} CNY
      {% endfor %}
```

Because `apexcharts-card` is much better at time-series charts, the current tiered bill example uses a more stable summary-card + detail-list layout instead of forcing a category-based bar chart.

## Other Information

Thanks to @involute for the code in his [post](https://bbs.hassbian.com/thread-13820-1-1.html)

Thanks to @Aaron Godfrey for his [custom component development guide](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)
