# Ai-Link A.O. Smith 热水器集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

这是一个 Home Assistant 自定义集成，用于控制和监控 Ai家智控（A.O. Smith）燃气热水器。

## ✨ 主要功能

### 🌡️ Water Heater 实体
- **电源控制**：开启/关闭热水器
- **温度控制**：设置目标水温（35-70°C）
- **实时监控**：显示当前水温、运行状态
- **状态属性**：电源状态、增压状态、巡航状态、节能半管状态

### 🔘 Switch 开关实体
- **增压模式**：独立控制水压增压功能
- **巡航模式**：控制零冷水巡航功能
- **节能半管模式**：控制节能半管加热功能

### 📊 Sensor 传感器实体

#### 温度传感器
- 当前温度
- 进水温度
- 出水温度
- 热水温度

#### 水量传感器
- 瞬时流量（L/分钟）
- 总用水量（升）
- 水硬度

#### 燃烧参数
- 点火次数
- 总用气量
- 巡航总用气量
- 总燃烧时间
- 燃气压力
- CO浓度
- 燃烧比例

#### 设备状态
- 设备状态（运行/关机）
- 供电状态（通电/断电）
- 错误代码
- 固件版本代码

#### 其他传感器
- 风扇转速
- 风扇电流
- 水泵运行频率
- 水泵运行电流
- 循环防冻次数

## 📦 安装

### 通过 HACS 安装（推荐）

1. 在 HACS 中点击右上角的三个点
2. 选择「自定义仓库」
3. 添加仓库地址：`https://github.com/mopocv/Ai-Link_A.O.Smith`
4. 类别选择「Integration」
5. 在 HACS 中搜索「Ai-Link A.O. Smith」并安装
6. 重启 Home Assistant

### 手动安装

1. 下载此仓库
2. 将 `custom_components/ailink_aosmith` 文件夹复制到 Home Assistant 的 `custom_components` 目录
3. 重启 Home Assistant

## ⚙️ 配置

### 获取认证参数

由于 Ai家智控未提供公开的 API，您需要通过抓包获取以下参数：

**必需参数：**
- `access_token`：访问令牌（格式：Bearer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）
- `user_id`：用户ID
- `family_id`：家庭ID

**可选参数：**
- `cookie`：Cookie 信息（格式：cna=xxxxxxx）
- `mobile`：手机号

### 抓包方法

1. 在手机上安装抓包工具（如 Charles、Fiddler、HttpCanary 等）
2. 配置手机网络代理，使流量经过抓包工具
3. 打开「AI家智控」App 并登录
4. 在抓包记录中查找对 `ailink-api.hotwater.com.cn` 的请求
5. 从请求头（Headers）中提取以上参数

### 添加集成

1. 在 Home Assistant 中进入「配置」→「设备与服务」
2. 点击右下角的「+ 添加集成」
3. 搜索「Ai-Link A.O. Smith」
4. 填入获取的认证参数
5. 提交后集成将自动发现您的热水器设备

## 🎯 使用示例

### 自动化示例

#### 定时开启零冷水巡航
```yaml
alias: 早晨开启零冷水
description: 每天早上6点开启零冷水巡航模式
trigger:
  - platform: time
    at: "06:00:00"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.water_heater_cruise
mode: single
```

#### 温度过高告警
```yaml
alias: 热水器温度告警
description: 当水温超过65度时发送通知
trigger:
  - platform: numeric_state
    entity_id: sensor.water_heater_watertemp
    above: 65
action:
  - service: notify.mobile_app
    data:
      message: "热水器温度过高！当前：{{ states('sensor.water_heater_watertemp') }}°C"
mode: single
```

## 🔄 更新日志

### v1.0.2
- 添加开关实体（增压、巡航、节能半管）
- 完善传感器映射
- 优化状态更新逻辑
- 添加翻译配置

### v1.0.0
- 初始版本发布
- 支持基本的热水器控制和监控功能

## ❓ 常见问题

**Q: 为什么需要抓包获取参数？**  
A: Ai家智控未提供公开的开发者 API，因此需要通过抓包获取认证信息。

**Q: 参数会过期吗？**  
A: access_token 可能会过期，如果设备状态无法更新，请重新抓包获取新的参数。

**Q: 支持哪些设备？**  
A: 目前支持 A.O. Smith 燃气热水器（设备类别为 19）。

**Q: 数据更新频率是多少？**  
A: 默认每 60 秒更新一次设备状态。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

此项目为第三方集成，与 A.O. Smith 公司无关。使用本集成产生的任何问题，开发者不承担责任。请谨慎使用。