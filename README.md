
# 内蒙古电费查询

简体中文 | [English](https://github.com/NiaoBlush/impc_energy/README_en.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/manifest-json/v/NiaoBlush/impc_energy?filename=custom_components%2Fimpc_energy%2Fmanifest.json)](https://github.com/NiaoBlush/impc_energy/releases/latest)

查询内蒙古住户的电费及历史电量、电费情况


## 数据说明

数据来自内蒙古电力公司公众号

根据公众号中的说法

>查询余额为结算系统余额=上月度结转电费+本月缴纳电费，实际电费余额以表计显示为准。

所以，余额***不是实时余额***，仅供参考。

## 安装

可以通过HACS或手动安装
从HACS中搜索插件名
或者从[这里](https://github.com/NiaoBlush/impc_energy/releases/latest)下载最新版本

安装后需要重启hass


## 配置

只需知道自己的户号，即可开始配置

+ 在`configuration.yaml`中，增加配置：
```yaml
sensor:
  #...

  - platform: impc_energy
    account_number: "01xxxxxxxx70"      #户号 (使用引号括住)
    name: 家庭1                       #家庭名称（可选）

  - platform: impc_energy
    account_number: "01xxxxxxxx71"

  #...
```
其中`name`字段可选，如果不填写就会使用获取到的户名(多数情况下为住址)作为家庭名称

+ 重启hass

## 传感器

插件会为每个家庭添加两个传感器 剩余电费 与 历史
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221439.png?raw=true)

电费余额是结算余额，所以理论上数值一个月才会改变一次(交了电费也可能改变，没有测试)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221605.png?raw=true)

过去12个月的历史数据（用电量与电费）放到了一个传感器里
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221718.png?raw=true)

## 卡片配置

利用图表卡片 `apexcharts-card`
可以实现如下的效果:
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20240409161911.png?raw=true)
(x轴步长没有生效可能是这个图表库的问题)

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_01xxxxxxx70_balance %}
          ### {{home.state}}
          当前余额(元)
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_0110xxxxxx970_history %}
          ### {{home.attributes['current']['bill']}}
          本期总电费(元)
      - type: markdown
        content: |-
          {% set home=states.sensor.impc_energy_011xxxxxxx970_history %}
          ### {{home.attributes['current']['consumption']}}
          本期总电量(kW⋅h)
  - type: custom:apexcharts-card
    header:
      show: true
      title: 用电历史
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
            month: M月
      tooltip:
        x:
          format: yyyy年M月
    series:
      - name: 历史电量
        entity: sensor.impc_energy_01xxxxxxxxx70_history
        type: column
        color: 3498DB
        unit: kW⋅h
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item.length==6&&item.startsWith("20")){
              //202403
              const timeStr=`${item.slice(0, 4)}-${item.slice(-2)}-01T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]["consumption"]]);
            }
          }
          //console.log("data1", data);
          return data;
      - name: 历史电费
        entity: sensor.impc_energy_011xxxxxx970_history
        color: FF9F0b
        unit: 元
        extend_to: false
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item.length==6&&item.startsWith("20")){
              //202403
              const timeStr=`${item.slice(0, 4)}-${item.slice(-2)}-01T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]["bill"]]);
            }
          }
          //console.log("data2", data);
          return data;

```

## 其他

没有找到现成能用的，就自己写一个吧。

我是搞Java的，Python勉强能看懂，但是还是有些蛋疼的 (╯‵□′)╯︵┻━┻

这里鸣谢 @involute 大神，参考了他[帖子](https://bbs.hassbian.com/thread-13820-1-1.html)中的代码

同样感谢大神@Aaron Godfrey
提供的[插件开发教程](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)