# 内蒙古电费查询

简体中文 | [English](https://github.com/NiaoBlush/impc_energy/README_en.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/manifest-json/v/NiaoBlush/impc_energy?filename=custom_components%2Fimpc_energy%2Fmanifest.json)](https://github.com/NiaoBlush/impc_energy/releases/latest)

查询内蒙古住户的电费及历史电量、电费情况

## 数据说明

数据来自`内蒙古电力公司`公众号与`蒙电e家`app

根据公众号中的说法

> 查询余额为结算系统余额=上月度结转电费+本月缴纳电费，实际电费余额以表计显示为准。

所以，余额***不是实时余额***，仅供参考。

## 安装

### HACS (推荐)

可以通过在HACS中搜索插件名`IMPC Energy`进行安装

### 手动安装

从[这里](https://github.com/NiaoBlush/impc_energy/releases/latest)下载最新版本

把压缩包内容解压到`custom_components/impc_energy`文件夹下

**安装后需要重启hass**

## 配置

只需知道自己的户号，即可开始配置

+ 进入 设置 -> 设备与服务 -> 添加集成(右下角)

+ 在弹出的对话框中搜索 `IMPC Energy` 并点击

  ![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/select_integration.png?raw=true)

+ 在弹出的配置向导中输入户号及户名

  如果不输入户名, 则集成会尝试使用获取到的户名(多数情况下为住址)作为户名

  ![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/config_helper.png?raw=true)
+ 如果勾选`是否继续配置蒙电e家app`, 则需要输入app的用户名和密码, 配置蒙电e家后可以获取每日用电量

+ 等待配置完成

+ 系统会自动生成实体名称, 如有需要可自行修改

<details>
<summary>旧版本迁移指南</summary>

如果您从 `v0.X.X` 旧版本升级到 `v1.X.X` 及以上版本，可能需要注意以下事项：

- 旧版本配置文件配置方式已被移除，请改用图形界面添加。
- 由于`entity_id`与`unique_id`的问题，旧版实体与新版不兼容，需要删除旧版实体。
- 需要删除配置文件中的`impc_energy`配置
- 如果无法删除旧版实体，请尝试删除旧版`IMPC Energy`集成，重启HomeAssistant，再重新安装。

</details>

## 传感器

插件会为每个家庭添加3个传感器 `电费余额`, `历史电费`与`每日电量`
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/entities_created.png?raw=true)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/entities_detail.png?raw=true)

电费余额是结算余额，所以理论上数值一个月才会改变一次(交了电费也可能改变，没有测试)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20230316221605.png?raw=true)

过去12个月的历史数据（用电量与电费）放到了一个传感器里
"历史"实体中展示的数据是本期电费
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/history_bill.png?raw=true)

每日电量会展示最近30天的每日用电量
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/sensor_daily_consumption.png)

> 有时会有负值是因为接口返回的就是负数, 不知道为什么

## 卡片配置

利用图表卡片 [apexcharts-card](https://github.com/RomRider/apexcharts-card)
可以实现如下的效果:

![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/20240409174425.png?raw=true)
![image](https://github.com/NiaoBlush/impc_energy/blob/master/img/chart_daily_consumption.png?raw=true)

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

  - type: custom:apexcharts-card
    header:
      show: true
      title: 每日用电
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
            day: d日
      tooltip:
        x:
          format: yyyy年MM月dd日
    series:
      - name: 日用电量
        entity: sensor.impc_energy_011xxxxxx970_daily_consumption
        color: 4D55CC
        unit: kW⋅h
        show:
          datalabels: false
          legend_value: false
        data_generator: |
          const data=[];
          const attributes=entity.attributes;
          for(let item in attributes){
            if(item&&item.startsWith("20")){
              //2024-03-01
              const timeStr=`${item}T00:00:00`;
              const dataObj=new Date(timeStr);
              data.push([dataObj.getTime(),attributes[item]]);
              //data.push([item, attributes[item]]);
            }
          }
          console.log("data3", data);
          return data;


```

## 其他

没有找到现成能用的，就自己写一个吧。

我是搞Java的，Python勉强能看懂，但是还是有些蛋疼的 (╯‵□′)╯︵┻━┻

这里鸣谢 @involute 大神，参考了他[帖子](https://bbs.hassbian.com/thread-13820-1-1.html)中的代码

同样感谢大神@Aaron Godfrey
提供的[插件开发教程](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)