# Domoticz-XAir-Plugin

正和清源（356）检测仪 接入 Domoticz 插件


## 使用

1. 安装[CH341SER驱动](http://www.wch.cn/download/CH341SER_EXE.html)，将检测仪通过USB连接到domoticz设备，获取其串口名称，Windows串口一般为 `COM` 开头，Linux串口为 `/dev/ttyUSB` 开头

2. 复制插件至plugins目录，重启domoticz

    或使用 install.sh 脚本，在树莓派终端上运行
    >curl -L https://github.com/xiaoyao9184/Domoticz-XAir-Plugin/raw/master/install.sh | bash

3. 配置插件

    在`USB`中填写串口名称。

    在`Repeat Time(s)`中填写心跳时间。

    注意：*这个时间仅作检测间隔，当检测到上次数据事件超过**60秒**时，将重启串口连接，一般设备会因为串口重连自动重启。*